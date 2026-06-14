"""
Named-regulation extraction for F3 — Day 27.

KM concept: #258 Regression CI (this module is the feature-engineering fix
that Day 26's eval identified as the highest-leverage path to closing the
40% accuracy gap against the 80% CI gate)

Extracts the regulations a policy explicitly names (e.g. "Equal Credit
Opportunity Act", "Regulation B") from its fixture text, and checks whether
a candidate regulation's title names one of those same regulations.

Why this matters: Day 26 found the classifier's biggest error pattern was
generic-sounding regulations (e.g. "Equal Credit Opportunity Act (Regulation
B)") scoring similarly via dense_score against ALL THREE policies — high for
the policy it actually governs (correct), but also moderately high for
unrelated policies (false positives), while some true matches in the policy
it DOES govern scored just under the HIGH threshold (false negatives).
Checking whether the regulation's title names a law the POLICY ITSELF
already cites is a cheap, free signal dense_score alone can't see.

Limitations (documented, not fixed today): this only catches regulations
named via "<Word> ... Act", "Regulation <Letter>", or a (ABBREVIATION) in
parentheses. Agency names with mixed case (e.g. "FinCEN") aren't extracted.
Good enough for the 3 current policy fixtures; revisit if real client
policies use different citation styles.
"""

import re
from pathlib import Path

POLICIES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "policies"

_ACT_PATTERN = re.compile(r"\b(?:[A-Z][a-zA-Z]+ ){1,6}Act\b")
_REGULATION_LETTER_PATTERN = re.compile(r"\bRegulation [A-Z]\b")
_ABBREVIATION_PATTERN = re.compile(r"\(([A-Z]{3,6})\)")

_cache: dict[str, set[str]] = {}


def extract_named_regulations(policy_text: str) -> set[str]:
    """Return the set of regulation names/abbreviations a policy text explicitly cites."""
    names: set[str] = set()
    names.update(m.group(0) for m in _ACT_PATTERN.finditer(policy_text))
    names.update(m.group(0) for m in _REGULATION_LETTER_PATTERN.finditer(policy_text))
    names.update(m.group(1) for m in _ABBREVIATION_PATTERN.finditer(policy_text))
    return names


def get_named_regulations(policy_name: str) -> set[str]:
    """Load (and cache) the named regulations cited by a policy fixture, by policy_name."""
    if policy_name not in _cache:
        policy_path = POLICIES_DIR / f"{policy_name}.txt"
        text = policy_path.read_text(encoding="utf-8")
        _cache[policy_name] = extract_named_regulations(text)
    return _cache[policy_name]


def is_named_regulation_match(policy_name: str, regulation_title: str) -> bool:
    """True if regulation_title names a regulation the policy itself cites."""
    named = get_named_regulations(policy_name)
    return any(name in regulation_title for name in named)
