"""Tests for evals/f3_eval.py."""

import json

from evals import f3_eval


def test_run_eval_against_real_golden_set():
    """Sanity check against the real 30-pair golden set and matches.json."""
    report = f3_eval.run_eval(verbose=False)

    assert report["total"] == 30
    assert 0.0 <= report["accuracy"] <= 1.0
    assert report["correct"] == sum(
        count for (true, pred), count in report["confusion"].items() if true == pred
    )
    assert len(report["mismatches"]) == report["total"] - report["correct"]


def test_run_eval_with_fake_golden_set_and_matches(tmp_path, monkeypatch):
    """Unit test the scoring/confusion logic with controlled inputs."""
    golden = {
        "pairs": [
            {
                "pair_id": 1,
                "policy_name": "BSA-AML-Policy",
                "section_id": "1.1",
                "regulation_doc_id": "regA",
                "regulation_title": "Reg A",
                "dense_score_snapshot": 0.99,
                "true_impact_level": "high",
                "rationale": "should be classified high",
            },
            {
                "pair_id": 2,
                "policy_name": "BSA-AML-Policy",
                "section_id": "1.1",
                "regulation_doc_id": "regB",
                "regulation_title": "Reg B",
                "dense_score_snapshot": 0.99,
                "true_impact_level": "high",
                "rationale": "matches.json says not_applicable -> mismatch expected",
            },
        ]
    }
    # "Reg A" / "Reg B" don't match anything BSA-AML-Policy cites, so both
    # are named_regulation_match=False -> NO_MATCH_PENALTY (-0.20) applies.
    matches = [
        {
            "policy_name": "BSA-AML-Policy",
            "section_id": "1.1",
            "matches": [
                {"regulation_doc_id": "regA", "dense_score": 0.80},  # 0.80-0.20=0.60 -> high, matches golden
                {"regulation_doc_id": "regB", "dense_score": 0.10},  # 0.10-0.20=-0.10 -> not_applicable, mismatch
            ],
        }
    ]

    golden_path = tmp_path / "impact_pairs.json"
    golden_path.write_text(json.dumps(golden), encoding="utf-8")

    index_dir = tmp_path / "f3_indexes"
    index_dir.mkdir()
    (index_dir / "matches.json").write_text(json.dumps(matches), encoding="utf-8")

    monkeypatch.setattr(f3_eval, "GOLDEN_PATH", golden_path)
    monkeypatch.setattr(f3_eval, "INDEX_DIR", index_dir)

    report = f3_eval.run_eval(verbose=False)

    assert report["total"] == 2
    assert report["correct"] == 1
    assert report["accuracy"] == 0.5
    assert len(report["mismatches"]) == 1
    assert report["mismatches"][0]["pair_id"] == 2
    assert report["mismatches"][0]["true"] == "high"
    assert report["mismatches"][0]["predicted"] == "not_applicable"


def test_ci_gate_threshold_is_80_percent():
    assert f3_eval.CI_GATE_THRESHOLD == 0.80


def test_accuracy_does_not_regress_below_baseline():
    """
    Regression CI (KM #258): fails if a future change drops accuracy below
    the Day 30 measured level (23/30 = 76.7%, after multi-query retrieval),
    even though CI_GATE_THRESHOLD (0.80) is a separate, still-unmet
    aspirational target.
    """
    report = f3_eval.run_eval(verbose=False)
    assert report["accuracy"] >= f3_eval.REGRESSION_BASELINE
