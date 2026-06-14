"""
F2 summarisation orchestrator.

Runs the full RAG + NER pipeline for a single RegulatoryDocument:
  1. Chunk the document's raw_content (hierarchical strategy)
  2. Retrieve the top-k most relevant chunks
  3. Build the Claude prompt
  4. Call Claude (primary model, fall back to haiku on failure)
  5. Parse the JSON response
  6. Run NER on full raw_content (dates + institution types)
  7. Cross-validate: NER fills null fields, adjusts confidence score
  8. Write summary_json to DB
  9. Update status + review_flag
  10. Write AuditLog entry with prompt_version + chunk_strategy

Day 12 addition: NER layer (Step 6-7) runs independently of LLM retrieval,
finding dates buried in sections the retriever didn't select.
"""

import json
import os
import re
import time
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from langsmith.run_helpers import get_current_run_tree, traceable
from pathlib import Path
from sqlmodel import select

from src.database import get_session

# Explicitly load .env from project root regardless of working directory
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)
from src.f2_summarise.chunker import chunk_document, chunk_stats, chunk_with_strategy
from src.f2_summarise.ner import run_ner, cross_validate
from src.f2_summarise.router import (
    RoutingDecision, build_router_input, route, routing_label
)

# Day 9 benchmark: sentence (0.802) > fixed_size (0.638)
# Day 10: hierarchical adds structure awareness + priority retrieval for date/institution sections
DEFAULT_CHUNK_STRATEGY = "hierarchical"

# Day 16: hybrid retrieval (dense + BM25 via RRF) replaces keyword-only scoring
USE_HYBRID_RETRIEVAL = True

# Day 17: cross-encoder reranker after hybrid retrieval
# Pipeline: BM25(50) → dense(15) → cross-encoder(8) → Claude
# Set to False to use hybrid-only (Day 16 behaviour)
USE_RERANKER = True
from src.f2_summarise.prompts import (
    CONFIDENCE_THRESHOLD,
    FALLBACK_MODEL,
    MAX_TOKENS,
    PRIMARY_MODEL,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    TEMPERATURE,
    build_user_message,
)
from src.f2_summarise.retriever import (
    format_chunks_for_prompt, retrieve_top_chunks,
    hybrid_retrieve, retrieve_for_reranking,
)
from src.f2_summarise.reranker import rerank_chunks
from src.models import AuditAction, AuditLog, DocStatus, RegulatoryDocument



def _get_client() -> anthropic.Anthropic:
    """Return an Anthropic client. Raises clear error if API key missing."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        raise ValueError(
            "ANTHROPIC_API_KEY not set in .env file.\n"
            "Add your key: ANTHROPIC_API_KEY=sk-ant-..."
        )
    return anthropic.Anthropic(api_key=api_key)


@traceable(name="f2_summarise_call", run_type="llm")
def _call_claude(client: anthropic.Anthropic, user_message: str, use_fallback: bool = False) -> tuple[str, str | None, dict]:
    """
    Call Claude with the summarisation prompt.
    Returns (raw text response, LangSmith trace/run ID or None, token usage dict).
    Falls back to Haiku if primary model fails.

    Day 37 (KM #241 LangSmith): wrapped in @traceable so each call produces
    a LangSmith run. get_current_run_tree() is read AFTER the API call so
    the trace_id reflects this specific invocation. If LangSmith isn't
    configured (no LANGCHAIN_API_KEY), get_current_run_tree() returns None
    and trace_id stays None -- the summarisation pipeline must not fail or
    change behaviour just because observability is unavailable.

    Day 44 (KM #239 cost dashboard): also returns {"input_tokens",
    "output_tokens"} from response.usage, used to compute $/query in
    scripts/cost_dashboard.py. Defaults to 0/0 if the response has no
    usage attribute (e.g. test doubles).
    """
    model = FALLBACK_MODEL if use_fallback else PRIMARY_MODEL

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    trace_id = None
    try:
        run_tree = get_current_run_tree()
        if run_tree is not None:
            trace_id = str(run_tree.id)
    except Exception:
        pass

    usage = getattr(response, "usage", None)
    token_usage = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
    }

    return response.content[0].text, trace_id, token_usage


def _parse_summary_json(raw_text: str) -> dict:
    """
    Parse Claude's JSON response with graceful error handling.

    Claude at temperature 0.2 almost always returns valid JSON.
    But edge cases exist:
      - Markdown code fences: ```json { ... } ```
      - Trailing comma in last field
      - Brief preamble before the JSON

    This parser handles all three.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Find the JSON object (starts with { ends with })
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {text[:200]}")

    json_str = text[start:end]
    return json.loads(json_str)


def _validate_summary(summary: dict) -> list[str]:
    """
    Validate that the summary has required fields and correct types.
    Returns a list of validation warnings (empty = all good).
    """
    warnings = []
    required = [
        "headline", "plain_english_summary", "what_changed",
        "why_it_matters", "confidence_score",
    ]
    for field in required:
        if field not in summary or not summary[field]:
            warnings.append(f"Missing required field: {field}")

    if "confidence_score" in summary:
        score = summary["confidence_score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            warnings.append(f"confidence_score out of range: {score}")

    return warnings


# Day 38 (KM #263 Citations + #269 Guardrails). Chunks are labelled
# "[Chunk N]" 1-indexed by format_chunks_for_prompt -- a citation referencing
# a chunk outside 1..num_chunks did not come from the retrieved excerpts.
_CHUNK_CITATION_RE = re.compile(r"Chunk\s+(\d+)", re.IGNORECASE)


def _apply_guardrails(summary: dict, num_chunks: int) -> list[str]:
    """
    Post-hoc safety checks on Claude's output, independent of confidence_score.

    Closes the gap docs/RCA-Hallucinated-Deadline-v1.md identified: dates
    were extracted with no field-level evidence trail, so a hallucinated
    compliance_deadline could reach a Task undetected. These checks don't
    catch every hallucination, but they make "the model cited evidence for
    this date" a checkable, logged fact rather than an assumption.

    Returns a list of guardrail warnings (empty = all checks passed). Any
    non-empty result forces needs_review=True in summarise_document,
    regardless of the router's decision -- a guardrail failure overrides an
    otherwise-APPROVED/DISMISS routing decision.
    """
    warnings: list[str] = []
    citations = summary.get("source_citations") or []

    # ── Citation forcing: dates must have a field-level citation ──────────────
    for field in ("effective_date", "compliance_deadline"):
        if summary.get(field):
            if not any(field in c for c in citations):
                warnings.append(
                    f"GUARDRAIL: {field}={summary[field]!r} has no matching "
                    f"source_citations entry (no field-level evidence trail)"
                )

    # ── Citation forcing: high confidence requires some citation ─────────────
    score = summary.get("confidence_score", 0)
    if isinstance(score, (int, float)) and score >= CONFIDENCE_THRESHOLD and not citations:
        warnings.append(
            f"GUARDRAIL: confidence_score={score} >= {CONFIDENCE_THRESHOLD} "
            f"but source_citations is empty"
        )

    # ── Citation chunk-range validation ───────────────────────────────────────
    for citation in citations:
        for match in _CHUNK_CITATION_RE.finditer(citation):
            chunk_num = int(match.group(1))
            if not (1 <= chunk_num <= num_chunks):
                warnings.append(
                    f"GUARDRAIL: source_citations references Chunk {chunk_num}, "
                    f"but only {num_chunks} chunks were retrieved"
                )

    return warnings


def summarise_document(doc: RegulatoryDocument, verbose: bool = True) -> dict | None:
    """
    Run the full F2 RAG pipeline for one document.

    Returns the parsed summary dict on success, None on failure.
    Always writes to DB (success → summary_json; failure → logged in AuditLog).
    """
    if verbose:
        print(f"\n[F2] Summarising: {doc.title[:70]}...")
        print(f"     Agency: {doc.source_agency.value} | Status: {doc.status.value}")

    # ── Guard: skip already summarised ────────────────────────────────────────
    if doc.status == DocStatus.SUMMARISED and doc.summary_json:
        if verbose:
            print(f"     [skip] Already summarised")
        return json.loads(doc.summary_json)

    # ── Guard: need raw content ────────────────────────────────────────────────
    if not doc.raw_content or len(doc.raw_content) < 100:
        if verbose:
            print(f"     [skip] raw_content too short ({len(doc.raw_content or '')} chars)")
        return None

    started_at = time.time()

    # ── Step 1: Chunk (Day 9: sentence strategy wins benchmark) ───────────────
    chunks = chunk_with_strategy(doc.raw_content, DEFAULT_CHUNK_STRATEGY)
    stats = chunk_stats(chunks)
    if verbose:
        print(f"     Chunked: {stats['count']} chunks, avg {stats['avg_chars']} chars")

    # ── Step 2: Retrieve + Rerank (Day 17 pipeline) ───────────────────────────
    # Full pipeline: BM25(50) → dense(15) → cross-encoder(8) → Claude
    # Fallback cascade: reranker → hybrid → keyword
    if USE_RERANKER and USE_HYBRID_RETRIEVAL and len(chunks) >= 4:
        retrieval_method = "hybrid+reranker"
        # Get 15 candidates from optimised hybrid pipeline (embeds 50, not 470)
        candidates = retrieve_for_reranking(chunks)
        # Cross-encoder reranks to top-8
        top_chunks = rerank_chunks(candidates)
    elif USE_HYBRID_RETRIEVAL and len(chunks) >= 4:
        retrieval_method = "hybrid"
        top_chunks = hybrid_retrieve(chunks)
    else:
        retrieval_method = "keyword"
        top_chunks = retrieve_top_chunks(chunks)

    chunks_text = format_chunks_for_prompt(top_chunks)
    if verbose:
        print(f"     Retrieved: {len(top_chunks)} chunks [{retrieval_method}] ({len(chunks_text):,} chars)")

    # ── Step 3: Build prompt ───────────────────────────────────────────────────
    user_message = build_user_message(
        title=doc.title,
        agency=doc.source_agency.value,
        url=doc.url,
        chunks_text=chunks_text,
    )

    # ── Step 4: Call Claude ────────────────────────────────────────────────────
    client = _get_client()
    summary = None
    model_used = PRIMARY_MODEL
    error_msg = None

    trace_id = None
    token_usage = {"input_tokens": 0, "output_tokens": 0}
    try:
        raw_response, trace_id, token_usage = _call_claude(client, user_message, use_fallback=False)
        summary = _parse_summary_json(raw_response)
        if verbose:
            conf = summary.get("confidence_score", "?")
            print(f"     [ok] {PRIMARY_MODEL} | confidence: {conf}")
    except Exception as primary_err:
        if verbose:
            print(f"     [warn] Primary model failed: {primary_err}. Trying fallback...")
        try:
            model_used = FALLBACK_MODEL
            raw_response, trace_id, token_usage = _call_claude(client, user_message, use_fallback=True)
            summary = _parse_summary_json(raw_response)
            if verbose:
                conf = summary.get("confidence_score", "?")
                print(f"     [ok] {FALLBACK_MODEL} (fallback) | confidence: {conf}")
        except Exception as fallback_err:
            error_msg = f"Primary: {primary_err} | Fallback: {fallback_err}"
            if verbose:
                print(f"     [error] Both models failed: {error_msg}")

    duration = time.time() - started_at

    # ── Step 5: NER cross-validation ──────────────────────────────────────────
    ner_result = None
    confidence_delta = 0
    if summary and doc.raw_content:
        try:
            ner_result = run_ner(doc.raw_content)
            summary, confidence_delta = cross_validate(summary, ner_result)
            if verbose and (ner_result.best_effective_date or ner_result.best_compliance_deadline):
                print(f"     NER: eff={ner_result.best_effective_date} "
                      f"deadline={ner_result.best_compliance_deadline} "
                      f"institutions={len(ner_result.institution_types)} "
                      f"delta={confidence_delta:+d}")
        except Exception as ner_err:
            if verbose:
                print(f"     [warn] NER failed: {ner_err}")

    # ── Step 6: Route + validate + write to DB ────────────────────────────────
    if summary:
        warnings = _validate_summary(summary)
        guardrail_warnings = _apply_guardrails(summary, len(top_chunks))
        warnings = warnings + guardrail_warnings
        raw_confidence = summary.get("confidence_score", 0)
        confidence = max(0, min(100, raw_confidence + confidence_delta))
        if confidence != raw_confidence:
            summary["confidence_score"] = confidence

        # Multi-signal routing decision (replaces simple threshold check)
        router_inp = build_router_input(
            summary=summary,
            doc_type=doc.doc_type.value,
            ner_delta=confidence_delta,
        )
        routing = route(router_inp)
        needs_review = routing.decision in (
            RoutingDecision.REVIEW, RoutingDecision.ESCALATE
        )
        # Day 38: a guardrail failure (e.g. an undated deadline with no
        # citation) forces human review regardless of the router's decision --
        # routing reasons alone wouldn't surface this safety-layer signal.
        if guardrail_warnings:
            needs_review = True

        # Store routing metadata in summary for dashboard display
        summary["_routing_decision"] = routing.decision.value
        summary["_routing_reasons"] = routing.reasons
        summary["_routing_priority"] = routing.review_priority

        if verbose:
            decision_str = routing_label(routing.decision)
            print(f"     Router: {decision_str} (priority={routing.review_priority}) | "
                  f"adjusted_conf={routing.adjusted_confidence}")

        with get_session() as session:
            db_doc = session.get(RegulatoryDocument, doc.id)
            if db_doc:
                db_doc.summary_json = json.dumps(summary)
                db_doc.status = DocStatus.SUMMARISED
                db_doc.review_flag = needs_review
                session.add(db_doc)

                log = AuditLog(
                    action=AuditAction.SUMMARISE,
                    actor="system:f2",
                    doc_id=doc.id,
                    langsmith_trace_id=trace_id,
                    payload_json=json.dumps({
                        "model": model_used,
                        "prompt_version": PROMPT_VERSION,
                        "chunk_strategy": DEFAULT_CHUNK_STRATEGY,
                        "retrieval_method": retrieval_method,
                        "reranker_used": USE_RERANKER,
                        "confidence_score": confidence,
                        "confidence_delta_from_ner": confidence_delta,
                        "ner_effective_date": ner_result.best_effective_date if ner_result else None,
                        "ner_compliance_deadline": ner_result.best_compliance_deadline if ner_result else None,
                        "ner_institution_count": len(ner_result.institution_types) if ner_result else 0,
                        "routing_decision": routing.decision.value,
                        "routing_priority": routing.review_priority,
                        "routing_reasons": routing.reasons,
                        "review_flag": needs_review,
                        "guardrail_warnings": guardrail_warnings,
                        "chunks_used": len(top_chunks),
                        "total_chunks": len(chunks),
                        "prompt_chars": len(chunks_text),
                        "duration_seconds": round(duration, 2),
                        "input_tokens": token_usage["input_tokens"],
                        "output_tokens": token_usage["output_tokens"],
                        "warnings": warnings,
                    }),
                )
                session.add(log)
                session.commit()

        if verbose:
            flag_str = " [REVIEW QUEUE]" if needs_review else ""
            print(f"     Saved | {duration:.1f}s | confidence={confidence}{flag_str}")
            if warnings:
                for w in warnings:
                    print(f"     Warning: {w}")

        return summary
    else:
        # Log the failure
        with get_session() as session:
            log = AuditLog(
                action=AuditAction.SUMMARISE,
                actor="system:f2",
                doc_id=doc.id,
                payload_json=json.dumps({
                    "error": error_msg,
                    "model_tried": model_used,
                    "duration_seconds": round(duration, 2),
                }),
            )
            session.add(log)
            session.commit()

        return None


def reset_for_resummary(doc_ids: list[str] | None = None) -> int:
    """
    Reset document status to 'new' so they can be re-summarised.
    Used to test a new prompt version against already-summarised docs.
    Returns count of docs reset.
    """
    with get_session() as session:
        if doc_ids:
            query = select(RegulatoryDocument).where(
                RegulatoryDocument.id.in_(doc_ids)  # type: ignore
            )
        else:
            query = select(RegulatoryDocument).where(
                RegulatoryDocument.status == DocStatus.SUMMARISED
            )
        docs = session.exec(query).all()
        for doc in docs:
            doc.status = DocStatus.NEW
            doc.summary_json = None
            doc.review_flag = False
            session.add(doc)
        session.commit()
        return len(docs)


def summarise_batch(
    limit: int = 20,
    agency_filter: str | None = None,
    verbose: bool = True,
) -> dict:
    """
    Summarise up to `limit` documents with status='new'.
    Oldest documents processed first.

    Returns summary stats: {attempted, succeeded, failed, review_queue}.
    """
    with get_session() as session:
        query = (
            select(RegulatoryDocument)
            .where(RegulatoryDocument.status == DocStatus.NEW)
            .where(RegulatoryDocument.raw_content.isnot(None))  # type: ignore
        )
        if agency_filter:
            from src.models import SourceAgency
            try:
                query = query.where(
                    RegulatoryDocument.source_agency == SourceAgency(agency_filter)
                )
            except ValueError:
                pass

        docs = session.exec(query).all()

    # Sort oldest first, apply limit
    docs = sorted(docs, key=lambda d: d.fetched_at or datetime.min)[:limit]

    if verbose:
        print(f"\n{'='*60}")
        print(f"F2 SUMMARISATION — {len(docs)} documents queued")
        print(f"{'='*60}")

    attempted = 0
    succeeded = 0
    failed = 0
    review_queue = 0

    for doc in docs:
        attempted += 1
        result = summarise_document(doc, verbose=verbose)
        if result:
            succeeded += 1
            if result.get("confidence_score", 100) < CONFIDENCE_THRESHOLD:
                review_queue += 1
        else:
            failed += 1

    stats = {
        "attempted": attempted,
        "succeeded": succeeded,
        "failed": failed,
        "review_queue": review_queue,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"SUMMARY: {succeeded}/{attempted} succeeded | {failed} failed | {review_queue} in review queue")
        print(f"{'='*60}")

    return stats
