"""
RegWatch AI — Feed Dashboard

F1 + F2 integrated dashboard.

Tabs:
  1. Feed — All ingested regulatory documents with filters (F1)
  2. Review Queue — Documents needing human review before acting (F2)
  3. Summaries — Documents with AI summaries (F2)

Run with:
  streamlit run dashboard/app.py
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from sqlmodel import select

from src.database import get_session
from src.models import DocStatus, DocType, RegulatoryDocument, SourceAgency
from dashboard.components import (
    DOC_TYPE_LABELS,
    render_document_card,
    render_metric_row,
    render_review_card,
    render_sidebar_filters,
    render_summary_card,
)

# ── Page config — must be first Streamlit call ─────────────────────────────────
st.set_page_config(
    page_title="RegWatch AI",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)  # Cache for 5 minutes — refreshes automatically
def load_documents() -> list[dict]:
    """
    Load all documents from DB and return as plain dicts.

    We convert to dicts before caching because SQLModel objects
    hold a DB session reference that can't be serialised by Streamlit's cache.
    """
    with get_session() as session:
        docs = session.exec(select(RegulatoryDocument)).all()
        return [
            {
                "id": d.id,
                "title": d.title,
                "url": d.url,
                "source_agency": d.source_agency.value,
                "doc_type": d.doc_type.value,
                "published_date": d.published_date,
                "fetched_at": d.fetched_at,
                "raw_content": d.raw_content or "",
                "summary_json": d.summary_json,
                "status": d.status.value,
                "is_anomaly": d.is_anomaly,
                "review_flag": d.review_flag,
                # Cache confidence for queue sorting without re-parsing JSON
                "confidence_score_cached": (
                    json.loads(d.summary_json).get("confidence_score", 0)
                    if d.summary_json else 0
                ),
            }
            for d in docs
        ]


def dict_to_doc(d: dict) -> RegulatoryDocument:
    """Reconstruct a RegulatoryDocument from a cached dict for display."""
    doc = RegulatoryDocument(
        id=d["id"],
        title=d["title"],
        url=d["url"],
        source_agency=SourceAgency(d["source_agency"]),
        doc_type=DocType(d["doc_type"]),
        published_date=d["published_date"],
        fetched_at=d["fetched_at"],
        raw_content=d["raw_content"],
        summary_json=d["summary_json"],
        status=None,  # type: ignore
        is_anomaly=d["is_anomaly"],
        review_flag=d["review_flag"],
        content_hash="",
    )
    # Patch status enum back
    from src.models import DocStatus
    doc.status = DocStatus(d["status"])
    return doc


# ── Main app ──────────────────────────────────────────────────────────────────

def main() -> None:
    all_docs_raw = load_documents()

    # Partition docs by status
    review_docs = [d for d in all_docs_raw if d["review_flag"]]
    summarised_docs = [d for d in all_docs_raw
                       if d["status"] == "summarised" and not d["review_flag"]]

    # ── Header ────────────────────────────────────────────────────────────────
    st.title("RegWatch AI")
    st.caption("Regulatory Change Intelligence for Community Banks & Credit Unions")

    # ── Tab bar ───────────────────────────────────────────────────────────────
    review_badge = f" ({len(review_docs)})" if review_docs else ""
    summary_badge = f" ({len(summarised_docs)})" if summarised_docs else ""

    tab_feed, tab_review, tab_summaries = st.tabs([
        f"Feed ({len(all_docs_raw)})",
        f"Review Queue{review_badge}",
        f"Summaries{summary_badge}",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: FEED
    # ══════════════════════════════════════════════════════════════════════════
    with tab_feed:
        all_agencies = sorted({d["source_agency"] for d in all_docs_raw})
        all_doc_types = sorted({d["doc_type"] for d in all_docs_raw})
        filters = render_sidebar_filters(all_agencies, all_doc_types)

        filtered = all_docs_raw
        if filters["agencies"]:
            filtered = [d for d in filtered if d["source_agency"] in filters["agencies"]]
        if filters["doc_types"]:
            filtered = [d for d in filtered if d["doc_type"] in filters["doc_types"]]
        if filters["anomalies_only"]:
            filtered = [d for d in filtered if d["is_anomaly"]]

        sort = filters["sort_by"]
        if sort == "Newest first":
            filtered = sorted(filtered, key=lambda d: d["published_date"] or datetime.min, reverse=True)
        elif sort == "Oldest first":
            filtered = sorted(filtered, key=lambda d: d["published_date"] or datetime.min)
        elif sort == "Agency":
            filtered = sorted(filtered, key=lambda d: d["source_agency"])
        elif sort == "Doc type":
            filtered = sorted(filtered, key=lambda d: d["doc_type"])

        type_counts = Counter(DocType(d["doc_type"]) for d in filtered)
        anomaly_count = sum(1 for d in filtered if d["is_anomaly"])
        render_metric_row(len(filtered), type_counts, anomaly_count)
        st.markdown("---")

        total_all = len(all_docs_raw)
        header = (f"All {total_all} regulatory documents"
                  if len(filtered) == total_all
                  else f"{len(filtered)} of {total_all} documents (filtered)")
        st.subheader(header)

        if not filtered:
            st.info("No documents match the current filters.")
        else:
            if anomaly_count > 0:
                st.error(f"{anomaly_count} document(s) flagged as anomalous — review first.")
                with st.expander(f"View {anomaly_count} anomalous document(s)", expanded=True):
                    for d in [x for x in filtered if x["is_anomaly"]]:
                        render_document_card(dict_to_doc(d))
                st.markdown("---")
                filtered = [d for d in filtered if not d["is_anomaly"]]

            for d in filtered:
                render_document_card(dict_to_doc(d))

        st.markdown("---")
        st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                   f"Data cached 5 min")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: REVIEW QUEUE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_review:
        st.subheader("Review Queue")
        st.caption(
            "Documents that need a human check before being used for compliance decisions. "
            "Sorted by urgency: Final Rules first, lowest confidence last."
        )

        if not review_docs:
            st.success("Review queue is empty — all summaries are high confidence.")
            st.caption("Documents will appear here when AI confidence is below 80%.")
        else:
            # Sort: routing priority first (1=urgent), then confidence ascending
            review_sorted = sorted(
                review_docs,
                key=lambda d: (
                    _routing_priority(d),
                    -(d.get("confidence_score_cached", 100))
                )
            )

            st.info(f"{len(review_sorted)} document(s) need review. "
                    f"Target: < 20% of summaries in review queue.")

            for d in review_sorted:
                render_review_card(d)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: SUMMARIES + QUALITY METRICS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_summaries:
        st.subheader("AI Summaries")
        st.caption("High-confidence summaries ready to act on.")

        # ── Quality Metrics Panel ─────────────────────────────────────────────
        all_summarised = [d for d in all_docs_raw if d["status"] == "summarised"]
        total_summarised = len(all_summarised)

        if total_summarised > 0:
            in_review = len([d for d in all_summarised if d["review_flag"]])
            approved_count = total_summarised - in_review
            override_rate = in_review / total_summarised * 100
            override_target_met = override_rate < 20.0

            # Avg confidence across all summarised docs
            confidences = [
                d["confidence_score_cached"]
                for d in all_summarised
                if d["confidence_score_cached"] > 0
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Routing breakdown
            dismissed = sum(
                1 for d in all_summarised
                if d.get("summary_json") and
                json.loads(d["summary_json"]).get("_routing_decision") == "dismiss"
            )

            st.markdown("**Quality Metrics**")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Summarised", total_summarised)
            m2.metric("Approved", approved_count)
            m3.metric(
                "Override Rate",
                f"{override_rate:.0f}%",
                delta=f"{'Under' if override_target_met else 'Over'} 20% target",
                delta_color="normal" if override_target_met else "inverse",
            )
            m4.metric("Auto-Dismissed", f"{dismissed}", help="Informational docs, no action required")
            m5.metric("Avg Confidence", f"{avg_confidence:.0f}/100")

            # Override rate progress bar
            bar_color = "green" if override_target_met else "red"
            st.markdown(
                f"Override rate: **{override_rate:.0f}%** "
                f"{'(target met)' if override_target_met else '(above 20% target — improve prompt)'}"
            )
            st.progress(min(override_rate / 100, 1.0))
            st.markdown("---")

        if not summarised_docs:
            st.info("No approved summaries yet. Run: python -m src.f2_summarise.run --limit 10")
        else:
            approved = sorted(
                summarised_docs,
                key=lambda d: d["published_date"] or datetime.min,
                reverse=True,
            )
            st.caption(f"{len(approved)} approved summaries (confidence >= 80, no human review needed)")
            for d in approved:
                render_summary_card(d)


def _routing_priority(doc_dict: dict) -> int:
    """Extract routing priority from summary_json, default to 3."""
    if not doc_dict.get("summary_json"):
        return 3
    try:
        s = json.loads(doc_dict["summary_json"])
        return s.get("_routing_priority", 3)
    except Exception:
        return 3


if __name__ == "__main__" or True:
    main()
