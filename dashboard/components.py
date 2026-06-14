"""
Reusable display components for the RegWatch AI Streamlit dashboard.

Each function renders one piece of the UI. Keeping them here means
app.py stays focused on data fetching and layout, not HTML strings.
"""

import json
import streamlit as st
from datetime import datetime
from src.models import DocType, RegulatoryDocument


# ── Colour palette ─────────────────────────────────────────────────────────────

DOC_TYPE_COLOURS = {
    DocType.FINAL_RULE:    "#c0392b",   # red   — action required
    DocType.PROPOSED_RULE: "#e67e22",   # orange — comment opportunity
    DocType.ENFORCEMENT:   "#8e44ad",   # purple — enforcement signal
    DocType.GUIDANCE:      "#2980b9",   # blue   — informational
    DocType.FAQ:           "#27ae60",   # green  — low urgency
    DocType.OTHER:         "#7f8c8d",   # grey   — unclassified
}

DOC_TYPE_LABELS = {
    DocType.FINAL_RULE:    "Final Rule",
    DocType.PROPOSED_RULE: "Proposed Rule",
    DocType.ENFORCEMENT:   "Enforcement",
    DocType.GUIDANCE:      "Guidance",
    DocType.FAQ:           "FAQ",
    DocType.OTHER:         "Other",
}

AGENCY_DISPLAY = {
    "fed":              "Federal Reserve",
    "cfpb":             "CFPB",
    "occ":              "OCC",
    "fdic":             "FDIC",
    "fincen":           "FinCEN",
    "federal_register": "Federal Register",
}


def doc_type_badge(doc_type: DocType) -> str:
    """Return an HTML badge string for a doc type."""
    colour = DOC_TYPE_COLOURS.get(doc_type, "#7f8c8d")
    label = DOC_TYPE_LABELS.get(doc_type, "Other")
    return (
        f'<span style="background:{colour};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem;font-weight:600;">{label}</span>'
    )


def anomaly_badge() -> str:
    return (
        '<span style="background:#e74c3c;color:white;padding:2px 8px;'
        'border-radius:4px;font-size:0.75rem;font-weight:700;">⚠ ANOMALY</span>'
    )


def render_metric_row(total: int, by_type: dict, anomaly_count: int) -> None:
    """Top-of-page KPI row."""
    cols = st.columns(5)
    cols[0].metric("Total Documents", total)
    cols[1].metric("Final Rules", by_type.get(DocType.FINAL_RULE, 0))
    cols[2].metric("Proposed Rules", by_type.get(DocType.PROPOSED_RULE, 0))
    cols[3].metric("Enforcement", by_type.get(DocType.ENFORCEMENT, 0))
    cols[4].metric("Anomalies Flagged", anomaly_count, delta=None if anomaly_count == 0 else f"{anomaly_count} need review")


def render_document_card(doc: RegulatoryDocument) -> None:
    """Render one document as an expandable card."""
    pub_date = doc.published_date.strftime("%b %d, %Y") if doc.published_date else "Date unknown"
    agency_label = AGENCY_DISPLAY.get(doc.source_agency.value, doc.source_agency.value.upper())
    content_len = len(doc.raw_content or "")
    has_full_text = content_len >= 500

    # Build header line
    badges = doc_type_badge(doc.doc_type)
    if doc.is_anomaly:
        badges += " " + anomaly_badge()

    header = f"{badges} &nbsp; **{agency_label}** &nbsp; {pub_date}"

    with st.expander(doc.title, expanded=False):
        st.markdown(header, unsafe_allow_html=True)
        st.markdown("---")

        col1, col2 = st.columns([3, 1])
        with col1:
            if doc.summary_json:
                st.markdown("**AI Summary**")
                import json
                try:
                    summary = json.loads(doc.summary_json)
                    if summary.get("plain_english_summary"):
                        st.info(summary["plain_english_summary"])
                    if summary.get("compliance_deadline"):
                        st.warning(f"Compliance deadline: {summary['compliance_deadline']}")
                except Exception:
                    st.write(doc.summary_json[:300])
            elif has_full_text:
                st.markdown("**Document Preview**")
                preview = (doc.raw_content or "")[:600].strip()
                st.caption(preview + ("..." if content_len > 600 else ""))
                st.caption(f"*Full text: {content_len:,} characters — AI summary coming in F2*")
            else:
                st.caption("*No content available yet*")

        with col2:
            st.markdown("**Source**")
            st.markdown(f"[Open original document]({doc.url})")
            st.caption(f"Status: `{doc.status.value}`")
            if doc.is_anomaly:
                st.error("Anomaly flagged")
            if doc.review_flag:
                st.warning("In review queue")


def render_sidebar_filters(agencies: list[str], doc_types: list[str]) -> dict:
    """
    Render sidebar filter controls.
    Returns a dict of selected filter values.
    """
    st.sidebar.title("RegWatch AI")
    st.sidebar.caption("Regulatory Feed Monitor")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Filters")

    selected_agencies = st.sidebar.multiselect(
        "Agency",
        options=agencies,
        default=agencies,
        format_func=lambda x: AGENCY_DISPLAY.get(x, x.upper()),
    )

    selected_types = st.sidebar.multiselect(
        "Document Type",
        options=doc_types,
        default=doc_types,
        format_func=lambda x: DOC_TYPE_LABELS.get(DocType(x), x),
    )

    anomalies_only = st.sidebar.checkbox("Anomalies only", value=False)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Sort")
    sort_by = st.sidebar.radio(
        "Sort by",
        options=["Newest first", "Oldest first", "Agency", "Doc type"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("F1 complete · F2 in progress")

    return {
        "agencies": selected_agencies,
        "doc_types": selected_types,
        "anomalies_only": anomalies_only,
        "sort_by": sort_by,
    }


# ── Confidence display helpers ────────────────────────────────────────────────

def _confidence_label(score: int) -> str:
    if score >= 90: return "HIGH"
    if score >= 80: return "GOOD"
    if score >= 70: return "MODERATE"
    if score >= 60: return "LOW"
    return "VERY LOW"


def _confidence_colour(score: int) -> str:
    if score >= 90: return "#27ae60"
    if score >= 80: return "#2980b9"
    if score >= 70: return "#e67e22"
    return "#e74c3c"


def render_review_card(doc_dict: dict) -> None:
    """Render a document in the review queue with routing reasons and actions."""
    summary = {}
    if doc_dict.get("summary_json"):
        try:
            summary = json.loads(doc_dict["summary_json"])
        except Exception:
            pass

    conf = summary.get("confidence_score", 0)
    routing = summary.get("_routing_decision", "review")
    reasons = summary.get("_routing_reasons", [])
    priority = summary.get("_routing_priority", 3)
    agency = AGENCY_DISPLAY.get(doc_dict["source_agency"], doc_dict["source_agency"].upper())
    doc_type = DOC_TYPE_LABELS.get(DocType(doc_dict["doc_type"]), doc_dict["doc_type"])
    pub_date = doc_dict["published_date"]
    date_str = pub_date.strftime("%b %d, %Y") if pub_date else "Unknown date"

    priority_labels = {1: "URGENT", 2: "High", 3: "Medium", 4: "Low", 5: "Informational"}
    priority_str = priority_labels.get(priority, "Medium")

    conf_colour = _confidence_colour(conf)
    conf_label = _confidence_label(conf)

    header_html = (
        f'<span style="background:{DOC_TYPE_COLOURS.get(DocType(doc_dict["doc_type"]), "#7f8c8d")}; '
        f'color:white;padding:2px 7px;border-radius:4px;font-size:0.75rem;font-weight:600;">'
        f'{doc_type}</span> &nbsp;'
        f'<span style="background:{conf_colour};color:white;padding:2px 7px;'
        f'border-radius:4px;font-size:0.75rem;font-weight:600;">'
        f'{conf_label} {conf}/100</span> &nbsp;'
        f'<span style="color:#888;font-size:0.8rem;">{agency} · {date_str} · Priority: {priority_str}</span>'
    )

    with st.expander(doc_dict["title"][:80], expanded=(priority <= 2)):
        st.markdown(header_html, unsafe_allow_html=True)

        if reasons:
            st.markdown("**Why this needs review:**")
            for r in reasons:
                st.caption(f"- {r}")

        if summary.get("plain_english_summary"):
            st.markdown("**Summary:**")
            st.info(summary["plain_english_summary"])

        col1, col2, col3 = st.columns(3)
        col1.caption(f"**Effective date:** {summary.get('effective_date') or 'Not found'}")
        col2.caption(f"**Deadline:** {summary.get('compliance_deadline') or 'None'}")
        col3.caption(f"**Affects:** {', '.join(summary.get('affected_institution_types') or ['Not specified'])[:60]}")

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.button("Approve", key=f"approve_{doc_dict['id'][:8]}", type="primary")
        c2.button("Edit", key=f"edit_{doc_dict['id'][:8]}")
        c3.button("Escalate", key=f"escalate_{doc_dict['id'][:8]}")
        c4.link_button("View Original", doc_dict["url"])


def render_summary_card(doc_dict: dict) -> None:
    """Render an approved summary card."""
    summary = {}
    if doc_dict.get("summary_json"):
        try:
            summary = json.loads(doc_dict["summary_json"])
        except Exception:
            pass

    if not summary:
        return

    conf = summary.get("confidence_score", 0)
    agency = AGENCY_DISPLAY.get(doc_dict["source_agency"], doc_dict["source_agency"].upper())
    doc_type = DOC_TYPE_LABELS.get(DocType(doc_dict["doc_type"]), doc_dict["doc_type"])
    pub_date = doc_dict["published_date"]
    date_str = pub_date.strftime("%b %d, %Y") if pub_date else ""

    conf_colour = _confidence_colour(conf)
    conf_label = _confidence_label(conf)

    header_html = (
        f'<span style="background:{DOC_TYPE_COLOURS.get(DocType(doc_dict["doc_type"]), "#7f8c8d")}; '
        f'color:white;padding:2px 7px;border-radius:4px;font-size:0.75rem;">{doc_type}</span> &nbsp;'
        f'<b>{agency}</b> &nbsp; {date_str} &nbsp;'
        f'<span style="background:{conf_colour};color:white;padding:2px 7px;'
        f'border-radius:4px;font-size:0.75rem;">{conf_label} {conf}/100</span>'
    )

    headline = summary.get("headline", doc_dict["title"][:70])

    with st.expander(headline, expanded=False):
        st.markdown(header_html, unsafe_allow_html=True)
        st.markdown("---")

        if summary.get("plain_english_summary"):
            st.markdown(summary["plain_english_summary"])

        col1, col2 = st.columns(2)
        with col1:
            if summary.get("what_changed"):
                st.markdown("**What changed**")
                st.caption(summary["what_changed"])
        with col2:
            if summary.get("why_it_matters"):
                st.markdown("**Why it matters**")
                st.caption(summary["why_it_matters"])

        st.markdown("---")
        meta_cols = st.columns(3)
        meta_cols[0].caption(f"**Effective:** {summary.get('effective_date') or 'null'}")
        meta_cols[1].caption(f"**Deadline:** {summary.get('compliance_deadline') or 'null'}")
        meta_cols[2].caption(
            f"**Affects:** {', '.join((summary.get('affected_institution_types') or [])[:2])}"
        )

        if summary.get("source_citations"):
            st.caption("Citations: " + " · ".join(summary["source_citations"][:3]))

        st.link_button("View Original", doc_dict["url"])
