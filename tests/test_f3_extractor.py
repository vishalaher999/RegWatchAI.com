from src.f3_impact.extractor import extract_policy_library, extract_policy_sections

SAMPLE_POLICY = """FIRST COMMUNITY BANK
SAMPLE POLICY

Policy Number: SAMPLE-001

━━━━━━━━━━

SECTION 1: PURPOSE AND SCOPE

1.1 Purpose
This policy establishes the sample purpose.

1.2 Scope
This policy applies to all employees.

━━━━━━━━━━

SECTION 2: REQUIREMENTS

2.1 Requirement One
The Bank shall do something.
With a second line of text.
"""


def test_extract_policy_sections_basic():
    sections = extract_policy_sections(SAMPLE_POLICY, "Sample-Policy")

    assert len(sections) == 3
    assert sections[0].section_id == "1.1"
    assert sections[0].section_title == "Purpose"
    assert sections[0].parent_section == "SECTION 1: PURPOSE AND SCOPE"
    assert "sample purpose" in sections[0].text

    assert sections[1].section_id == "1.2"
    assert sections[2].section_id == "2.1"
    assert sections[2].parent_section == "SECTION 2: REQUIREMENTS"
    assert "second line of text" in sections[2].text


def test_extract_policy_sections_multiline_body():
    sections = extract_policy_sections(SAMPLE_POLICY, "Sample-Policy")
    requirement = sections[2]
    assert "The Bank shall do something." in requirement.text
    assert "With a second line of text." in requirement.text


def test_extract_policy_library_fixtures():
    sections = extract_policy_library("fixtures/policies")

    # All 3 fixture policies parsed
    policy_names = {s.policy_name for s in sections}
    assert "BSA-AML-Policy" in policy_names
    assert "Fair-Lending-ECOA-Policy" in policy_names
    assert "TRID-Mortgage-Disclosure-Policy" in policy_names

    # Sanity check: every section has a populated section_id, title, and text
    for s in sections:
        assert s.section_id
        assert s.section_title
        assert s.text.strip()

    # Spot check a known section
    bsa_sections = {s.section_id: s for s in sections if s.policy_name == "BSA-AML-Policy"}
    assert "4.2" in bsa_sections
    assert "Currency Transaction Reporting" in bsa_sections["4.2"].section_title
