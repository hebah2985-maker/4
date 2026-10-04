"""Evaluation runner (T5): runs gold_set.csv and writes eval/results/.

Metrics computed: verdict accuracy (MT-02) and — for EXACT-capable cases —
per-verdict recall. MT-03/MT-04 gates are enforced on Q&A cases once the
gold set is populated with them (Needs Clarification: books selection).
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT.parent))  # allow running without install

from naql_core.match import build_joined_source, check_quote  # noqa: E402

_RESULTS_DIR = _ROOT / "results"


@dataclass(frozen=True)
class EvalCaseResult:
    """One gold-set case outcome."""

    case_id: str
    expected_verdict: str
    actual_verdict: str
    passed: bool


def run_eval() -> dict:
    """Execute all gold-set cases and persist a timestamped result file.

    Returns:
        Summary dict with accuracy and per-case details.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[EvalCaseResult] = []
    gold_path = _ROOT / "gold_set.csv"
    with gold_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("id") or row["id"].startswith("#"):
                continue
            results.append(_run_case(row))
    passed = sum(1 for r in results if r.passed)
    summary = {
        "run_at": datetime.now(tz=UTC).isoformat(),
        "total": len(results),
        "passed": passed,
        "accuracy": (passed / len(results)) if results else 0.0,
        "cases": [asdict(r) for r in results],
    }
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    out = _RESULTS_DIR / f"eval_{stamp}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _run_case(row: dict) -> EvalCaseResult:
    """Run one quote-check case against its fixture source text."""
    fixture = _ROOT.parent / "tests" / "fixtures" / row["source"]
    text = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    source = build_joined_source([(1, 1, text)])
    expected_page = int(row["expected_page"]) if row.get("expected_page") else None
    result = check_quote(source, row["input"], claimed_page=expected_page)
    return EvalCaseResult(
        case_id=row["id"],
        expected_verdict=row["expected_verdict"],
        actual_verdict=result.verdict.value,
        passed=result.verdict.value == row["expected_verdict"],
    )


if __name__ == "__main__":
    summary = run_eval()
    print(  # noqa: T201 — CLI entry point reporting
        f"eval: {summary['passed']}/{summary['total']} passed (accuracy={summary['accuracy']:.0%})"
    )
