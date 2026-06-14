"""
Policy section extractor for F3 — Policy Impact Mapping.

Parses bank policy documents (currently plain text, structured like real
community bank policies) into numbered sections. The section ID
(e.g. "4.2") is what F3's output points Sarah to: "BSA Policy Section 4.2
needs review."

Input format assumed (matches /fixtures/policies/*.txt):
    SECTION 4: TRANSACTION MONITORING      <- major section header

    4.2 Currency Transaction Reporting     <- subsection header
    The Bank shall file a Currency...      <- body text

Each PolicySection is built from one subsection (the "4.2" level) — this
is the granularity that hybrid search will match against regulation
chunks in Day 23-24.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.f3_impact.pii import redact_text

SECTION_HEADER_RE = re.compile(r"^SECTION\s+(\d+):\s*(.+)$")
SUBSECTION_HEADER_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")


@dataclass
class PolicySection:
    policy_name: str       # "BSA-AML-Policy"
    section_id: str        # "4.2"
    section_title: str     # "Currency Transaction Reporting (CTR)"
    parent_section: str    # "SECTION 4: TRANSACTION MONITORING"
    text: str               # body text of the subsection (PII-redacted)
    # Day 39 (KM #267/268): PII type -> redaction count for this section's
    # text, e.g. {"SSN": 1}. Empty dict means no PII was found.
    pii_findings: dict[str, int] = field(default_factory=dict)


def extract_policy_sections(text: str, policy_name: str) -> list[PolicySection]:
    """Parse policy text into a list of PolicySection objects (one per N.M subsection)."""
    sections: list[PolicySection] = []

    current_major = ""
    current_sub_id: str | None = None
    current_sub_title: str | None = None
    buffer: list[str] = []

    def flush():
        if current_sub_id is not None:
            body = "\n".join(buffer).strip()
            if body:
                redacted_body, pii_findings = redact_text(body)
                sections.append(
                    PolicySection(
                        policy_name=policy_name,
                        section_id=current_sub_id,
                        section_title=current_sub_title or "",
                        parent_section=current_major,
                        text=redacted_body,
                        pii_findings=pii_findings,
                    )
                )

    for line in text.splitlines():
        stripped = line.strip()

        major_match = SECTION_HEADER_RE.match(stripped)
        if major_match:
            flush()
            current_major = stripped
            current_sub_id = None
            current_sub_title = None
            buffer = []
            continue

        sub_match = SUBSECTION_HEADER_RE.match(stripped)
        if sub_match:
            flush()
            current_sub_id = sub_match.group(1)
            current_sub_title = sub_match.group(2)
            buffer = []
            continue

        # Skip separator lines and blank lines outside any subsection
        if current_sub_id is not None:
            buffer.append(line)

    flush()
    return sections


def extract_policy_file(path: str | Path) -> list[PolicySection]:
    """Read a policy text file and extract its sections. policy_name = filename stem."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    policy_name = path.stem
    return extract_policy_sections(text, policy_name)


def extract_policy_library(directory: str | Path) -> list[PolicySection]:
    """Extract sections from every .txt policy file in a directory."""
    directory = Path(directory)
    all_sections: list[PolicySection] = []
    for path in sorted(directory.glob("*.txt")):
        all_sections.extend(extract_policy_file(path))
    return all_sections


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    fixtures_dir = Path(__file__).resolve().parents[2] / "fixtures" / "policies"
    sections = extract_policy_library(fixtures_dir)

    by_policy: dict[str, list[PolicySection]] = {}
    for s in sections:
        by_policy.setdefault(s.policy_name, []).append(s)

    for policy_name, policy_sections in by_policy.items():
        print(f"\n{policy_name}: {len(policy_sections)} sections")
        for s in policy_sections:
            preview = s.text.replace("\n", " ")[:60]
            print(f"  Section {s.section_id} - {s.section_title}: {preview}...")

    print(f"\nTotal: {len(sections)} sections across {len(by_policy)} policies")
