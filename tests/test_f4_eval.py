"""Tests for evals/f4_eval.py — structural validation, against fake tasks."""

from evals import f4_eval

CHUNK_LOOKUP = {
    ("Fair-Lending-ECOA-Policy", "1.1", "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3"): (
        "The Bureau finds that there have been significant changes in the "
        "legal landscape and in credit markets since the 1976 Act."
    ),
}

GOOD_TASK = {
    "source_policy_name": "Fair-Lending-ECOA-Policy",
    "source_section_id": "1.1",
    "source_regulation_doc_id": "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    "source_regulation_title": "Equal Credit Opportunity Act (Regulation B)",
    "source_impact_level": "high",
    "title": "Review Fair-Lending-ECOA-Policy Section 1.1 against Equal Credit Opportunity Act (Regulation B)",
    "description": (
        'The Bureau finds that there have been significant changes in the '
        "legal landscape and in credit markets since the 1976 Act. This "
        "policy section should be reviewed for alignment."
    ),
    "owner": "Sarah",
    "due_date": "2026-07-21",
}


def test_validate_task_passes_for_well_formed_task():
    failures = f4_eval.validate_task(GOOD_TASK, CHUNK_LOOKUP)

    assert failures == []


def test_validate_task_fails_missing_section_id_in_title():
    task = {**GOOD_TASK, "title": "Review policy against Equal Credit Opportunity Act (Regulation B)"}

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert "title does not reference source_section_id" in failures


def test_validate_task_fails_missing_regulation_title_in_title():
    task = {**GOOD_TASK, "title": "Review Fair-Lending-ECOA-Policy Section 1.1"}

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert "title does not reference source_regulation_title" in failures


def test_validate_task_fails_invalid_owner():
    task = {**GOOD_TASK, "owner": "Bob"}

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert any(f.startswith("owner 'Bob' not in") for f in failures)


def test_validate_task_fails_invalid_due_date():
    task = {**GOOD_TASK, "due_date": "next month"}

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert "due_date 'next month' is not a valid ISO date" in failures


def test_validate_task_fails_missing_evidence_excerpt():
    task = {
        **GOOD_TASK,
        "title": "Review Fair-Lending-ECOA-Policy Section 1.1 against Equal Credit Opportunity Act (Regulation B)",
        "description": "This section needs review. (default 30-day SLA -- no deadline found in regulation)",
    }

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert "description does not contain evidence excerpt from matched_chunk_text" in failures


def test_validate_task_fails_unknown_source_finding():
    task = {**GOOD_TASK, "source_section_id": "99.9"}

    failures = f4_eval.validate_task(task, CHUNK_LOOKUP)

    assert "source finding not found in impact_results.json" in failures


def test_run_eval_with_fake_tasks_file(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks.json"
    impact_path = tmp_path / "impact_results.json"

    import json

    tasks_path.write_text(json.dumps([GOOD_TASK]), encoding="utf-8")
    impact_path.write_text(
        json.dumps([
            {
                "policy_name": "Fair-Lending-ECOA-Policy",
                "section_id": "1.1",
                "matches": [
                    {
                        "regulation_doc_id": "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
                        "matched_chunk_text": CHUNK_LOOKUP[
                            ("Fair-Lending-ECOA-Policy", "1.1", "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3")
                        ],
                    }
                ],
            }
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(f4_eval, "TASKS_PATH", tasks_path)
    monkeypatch.setattr(f4_eval, "IMPACT_RESULTS_PATH", impact_path)

    report = f4_eval.run_eval(verbose=False)

    assert report["pass_rate"] == 1.0
    assert report["total"] == 1
    assert report["valid"] == 1
