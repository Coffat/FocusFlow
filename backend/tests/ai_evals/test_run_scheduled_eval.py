"""Offline unit & smoke tests for `scripts/run_scheduled_eval.py` slot tracking."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_scheduled_eval.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("run_scheduled_eval", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_legacy_csv_migration_and_missed_slot_backfill_delayed_wake(
    tmp_path: Path,
) -> None:
    mod = _load_module()
    out_dir = tmp_path / "scheduled"
    state_file = out_dir / "state.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Seed legacy 12-column CSV matching the two existing real runs
    legacy_header = [
        "timestamp_iso",
        "date",
        "hour",
        "dataset",
        "mode",
        "stage",
        "p50_ms",
        "p95_ms",
        "max_ms",
        "pass_at_1",
        "pass_with_judge_verdict",
        "judge_timeout_rate",
    ]
    legacy_rows = [
        [
            "2026-11-16T23:16:43+07:00",
            "2026-11-16",
            "23",
            "golden_planning_18_goals.jsonl",
            "live",
            "decomposer",
            "9939.792",
            "15860.504",
            "25002.491",
            "0.9444",
            "0.9444",
            "0.0",
        ],
        [
            "2026-11-17T10:07:46+07:00",
            "2026-11-17",
            "10",
            "golden_planning_18_goals.jsonl",
            "live",
            "decomposer",
            "9643.514",
            "13998.974",
            "15000.924",
            "1.0",
            "1.0",
            "0.0",
        ],
    ]
    csv_path = out_dir / "hourly_stage_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow(legacy_header)
        writer.writerows(legacy_rows)

    state_file.write_text(
        json.dumps(
            {
                "start_date": "2026-11-16",
                "window_days": 7,
                "runs_count": 2,
                "last_run_at": "2026-11-16T23:22:43+07:00",
                "last_status": "ok",
            }
        ),
        encoding="utf-8",
    )

    # Simulate waking at 2026-11-17T21:45+07:00 (14:00 was missed; 09:00 was covered by 10:07 row)
    rc = mod.main(
        [
            "--mock",
            "--dataset",
            "golden_planning_18_goals.jsonl",
            "--out-dir",
            str(out_dir),
            "--state-file",
            str(state_file),
            "--now-iso",
            "2026-11-17T21:45:00+07:00",
        ]
    )
    assert rc == 0

    with csv_path.open("r", encoding="utf-8", newline="") as cf:
        reader = csv.DictReader(cf)
        assert reader.fieldnames == list(mod.CSV_COLUMNS)
        all_rows = list(reader)

    # Legacy 2 rows preserved intact at the top with padded blank new cols
    assert all_rows[0]["timestamp_iso"] == "2026-11-16T23:16:43+07:00"
    assert all_rows[0]["scheduled_slot"] == ""
    assert all_rows[1]["timestamp_iso"] == "2026-11-17T10:07:46+07:00"
    assert all_rows[1]["scheduled_slot"] == ""

    missed_rows = [r for r in all_rows if r["status"] == "MISSED_SLEEP"]
    assert [r["scheduled_slot"] for r in missed_rows] == ["2026-11-17T14:00"]
    assert missed_rows[0]["mode"] == "missed"
    assert missed_rows[0]["stage"] == "schedule_slot"
    assert "Missed scheduled slot" in missed_rows[0]["reason"]

    delayed_rows = [r for r in all_rows if r["status"] == "DELAYED_WAKE"]
    assert len(delayed_rows) >= 1
    assert all(r["scheduled_slot"] == "2026-11-17T21:00" for r in delayed_rows)
    assert "Triggered at 21:45 after 21:00 slot" in delayed_rows[0]["reason"]

    saved_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "2026-11-17T14:00" in saved_state["recorded_slots"]
    assert "2026-11-17T21:00" in saved_state["recorded_slots"]
    assert "2026-11-17T09:00" in saved_state["recorded_slots"]

    jsonl_lines = [
        json.loads(line)
        for line in (out_dir / "hourly_stage_metrics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert any(
        row["status"] == "MISSED_SLEEP" and row["scheduled_slot"] == "2026-11-17T14:00"
        for row in jsonl_lines
    )


def test_cobhub_unreachable_logged_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module()
    out_dir = tmp_path / "unreachable"
    state_file = out_dir / "state.json"

    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:59999")
    monkeypatch.setenv("LLM_API_KEY", "test-placeholder-key")

    rc = mod.main(
        [
            "--dataset",
            "golden_planning_18_goals.jsonl",
            "--out-dir",
            str(out_dir),
            "--state-file",
            str(state_file),
            "--now-iso",
            "2026-11-17T14:05:00+07:00",
        ]
    )
    assert rc != 0

    csv_path = out_dir / "hourly_stage_metrics.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as cf:
        rows = list(csv.DictReader(cf))

    assert len(rows) == 1
    assert rows[0]["mode"] == "missed"
    assert rows[0]["stage"] == "schedule_slot"
    assert rows[0]["scheduled_slot"] == "2026-11-17T14:00"
    assert rows[0]["status"] == "COBHUB_UNREACHABLE"
    assert "59999" in rows[0]["reason"]


def test_eval_error_logged_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module()
    out_dir = tmp_path / "eval_err"
    state_file = out_dir / "state.json"

    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=3, stdout=""),
    )

    rc = mod.main(
        [
            "--mock",
            "--dataset",
            "golden_planning_18_goals.jsonl",
            "--out-dir",
            str(out_dir),
            "--state-file",
            str(state_file),
            "--now-iso",
            "2026-11-17T09:05:00+07:00",
        ]
    )
    assert rc == 3

    with (out_dir / "hourly_stage_metrics.csv").open("r", encoding="utf-8", newline="") as cf:
        rows = list(csv.DictReader(cf))

    assert len(rows) == 1
    assert rows[0]["mode"] == "missed"
    assert rows[0]["stage"] == "schedule_slot"
    assert rows[0]["scheduled_slot"] == "2026-11-17T09:00"
    assert rows[0]["status"] == "EVAL_ERROR"
    assert "exited 3" in rows[0]["reason"]
