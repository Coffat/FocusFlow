#!/usr/bin/env python3
"""7-day scheduled AI evaluation runner & hourly stage metrics collector.

Runs `tests.ai_evals.eval_runner` in live (default) or mock mode for up to
`--window-days` (default 7) from `start_date` tracked in `state.json`, saves full
JSON reports under `<out-dir>/runs/`, and appends normalized stage latency and
quality rows to `<out-dir>/hourly_stage_metrics.jsonl` and `.csv`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
DATASETS_DIR = BACKEND_DIR / "tests" / "ai_evals" / "datasets"

DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "experiments" / "scheduled_eval_7d"
DEFAULT_STATE_FILE = DEFAULT_OUT_DIR / "state.json"
DEFAULT_WINDOW_DAYS = 7
SCHEDULED_HOURS: tuple[int, ...] = (9, 14, 21)
DELAYED_WAKE_THRESHOLD_MINUTES = 30

CANONICAL_STAGE_ORDER: tuple[str, ...] = (
    "clarifier",
    "milestone_planner",
    "decomposer",
    "critics_judge_parallel",
    "weekly",
    "e2e_total",
)

CSV_COLUMNS: tuple[str, ...] = (
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
    "scheduled_slot",
    "status",
    "reason",
)


def resolve_backend_python() -> Path:
    """Find the repo Python interpreter with backend dependencies installed."""
    candidates = (
        BACKEND_DIR / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "bin" / "python",
        Path(sys.executable),
    )
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return Path(sys.executable)


def resolve_dataset_specs(
    requested_datasets: list[str] | None,
    *,
    e2e: bool,
) -> list[tuple[Path, bool]]:
    """Resolve dataset paths and per-dataset `--e2e` intent.

    Defaults to `golden_planning_18_goals.jsonl` and, if present on disk,
    optionally includes `hard_planning_6_goals.jsonl` (with `--e2e` intent).
    """
    specs: list[tuple[Path, bool]] = []
    if not requested_datasets:
        primary = DATASETS_DIR / "golden_planning_18_goals.jsonl"
        if not primary.exists():
            raise FileNotFoundError(f"Default dataset not found: {primary}")
        specs.append((primary, e2e))

        optional_hard = DATASETS_DIR / "hard_planning_6_goals.jsonl"
        if optional_hard.exists():
            specs.append((optional_hard, True))
        return specs

    for raw in requested_datasets:
        for item in raw.split(","):
            name = item.strip()
            if not name:
                continue
            candidate = Path(name)
            if not candidate.is_absolute():
                repo_rel = REPO_ROOT / candidate
                dataset_rel = DATASETS_DIR / candidate
                if repo_rel.exists():
                    candidate = repo_rel
                elif dataset_rel.exists():
                    candidate = dataset_rel
                else:
                    raise FileNotFoundError(
                        f"Dataset {name!r} not found at {repo_rel} or {dataset_rel}"
                    )
            elif not candidate.exists():
                raise FileNotFoundError(f"Dataset not found: {candidate}")
            use_e2e = e2e or candidate.name == "hard_planning_6_goals.jsonl"
            specs.append((candidate, use_e2e))

    if not specs:
        raise ValueError("No valid datasets resolved from --dataset arguments.")
    return specs


def _eval_runner_supports_flag(python_bin: Path, flag: str) -> bool:
    proc = subprocess.run(
        [str(python_bin), "-m", "tests.ai_evals.eval_runner", "--help"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    return flag in proc.stdout


def _compute_pass_with_judge_verdict(report: dict[str, Any]) -> float | None:
    explicit = report.get("pass_with_judge_verdict")
    if explicit is not None:
        return float(explicit)

    outcomes = report.get("per_case_outcomes")
    if isinstance(outcomes, list) and outcomes:
        passed_both = sum(
            1
            for item in outcomes
            if isinstance(item, dict)
            and bool(item.get("passed_tier1"))
            and item.get("judge_status") == "PASSED"
        )
        return round(passed_both / len(outcomes), 4)

    judge_rate = report.get("judge_passed_rate")
    return float(judge_rate) if judge_rate is not None else None


def extract_metric_rows(
    report: dict[str, Any],
    *,
    run_ts: datetime,
    dataset_name: str,
    mode_fallback: str,
    scheduled_slot: str = "",
    status: str = "OK",
    reason: str = "",
) -> list[dict[str, Any]]:
    """Normalize `stage_latency_stats` and overall pipeline metrics into flat rows."""
    timestamp_iso = run_ts.isoformat(timespec="seconds")
    date_str = run_ts.strftime("%Y-%m-%d")
    hour_str = run_ts.strftime("%H")
    mode = str(report.get("mode") or mode_fallback)
    pass_at_1 = report.get("pass_at_1")
    pass_with_judge_verdict = _compute_pass_with_judge_verdict(report)
    judge_timeout_rate = report.get("judge_timeout_rate")

    base_fields: dict[str, Any] = {
        "timestamp_iso": timestamp_iso,
        "date": date_str,
        "hour": hour_str,
        "dataset": dataset_name,
        "mode": mode,
        "pass_at_1": pass_at_1,
        "pass_with_judge_verdict": pass_with_judge_verdict,
        "judge_timeout_rate": judge_timeout_rate,
        "scheduled_slot": scheduled_slot,
        "status": status,
        "reason": reason,
    }

    rows: list[dict[str, Any]] = []
    stage_stats = report.get("stage_latency_stats")
    if isinstance(stage_stats, dict):
        ordered_stages = [s for s in CANONICAL_STAGE_ORDER if s in stage_stats]
        extra_stages = sorted(k for k in stage_stats if k not in CANONICAL_STAGE_ORDER)
        for stage in [*ordered_stages, *extra_stages]:
            stats = stage_stats.get(stage)
            if not isinstance(stats, dict):
                continue
            rows.append(
                {
                    **base_fields,
                    "stage": stage,
                    "p50_ms": stats.get("p50_ms"),
                    "p95_ms": stats.get("p95_ms"),
                    "max_ms": stats.get("max_ms"),
                }
            )

    if (
        report.get("latency_p50_ms") is not None
        or report.get("latency_p95_ms") is not None
    ):
        rows.append(
            {
                **base_fields,
                "stage": "overall_pipeline",
                "p50_ms": report.get("latency_p50_ms"),
                "p95_ms": report.get("latency_p95_ms"),
                "max_ms": None,
            }
        )

    return rows


def build_slot_event_row(
    *,
    event_ts: datetime,
    scheduled_slot: str,
    status: str,
    reason: str,
    dataset: str = "all",
    mode: str = "missed",
) -> dict[str, Any]:
    """Build a normalized CSV/JSONL row for missed, unreachable, or errored slots."""
    return {
        "timestamp_iso": event_ts.isoformat(timespec="seconds"),
        "date": event_ts.strftime("%Y-%m-%d"),
        "hour": event_ts.strftime("%H"),
        "dataset": dataset,
        "mode": mode,
        "stage": "schedule_slot",
        "p50_ms": None,
        "p95_ms": None,
        "max_ms": None,
        "pass_at_1": None,
        "pass_with_judge_verdict": None,
        "judge_timeout_rate": None,
        "scheduled_slot": scheduled_slot,
        "status": status,
        "reason": reason,
    }


def migrate_csv_if_needed(csv_path: Path) -> None:
    """Pad older 12-column CSV files cleanly to the current `CSV_COLUMNS` header."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return
    with csv_path.open("r", encoding="utf-8", newline="") as cf:
        reader = csv.reader(cf)
        header = next(reader, None)
    if header == list(CSV_COLUMNS):
        return

    with csv_path.open("r", encoding="utf-8", newline="") as cf:
        dict_reader = csv.DictReader(cf)
        existing_rows = list(dict_reader)

    tmp_path = csv_path.with_suffix(".csv.tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as tf:
        writer = csv.DictWriter(tf, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in existing_rows:
            writer.writerow(
                {
                    col: ("" if row.get(col) is None else row.get(col))
                    for col in CSV_COLUMNS
                }
            )
    tmp_path.replace(csv_path)


def append_metrics(out_dir: Path, rows: Sequence[dict[str, Any]]) -> tuple[Path, Path]:
    """Append metric rows to both JSONL and CSV files inside `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "hourly_stage_metrics.jsonl"
    csv_path = out_dir / "hourly_stage_metrics.csv"

    if not rows:
        return jsonl_path, csv_path

    migrate_csv_if_needed(csv_path)

    with jsonl_path.open("a", encoding="utf-8") as jf:
        for row in rows:
            jf.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=list(CSV_COLUMNS))
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    col: ("" if row.get(col) is None else row.get(col))
                    for col in CSV_COLUMNS
                }
            )

    return jsonl_path, csv_path


def format_slot_label(slot_dt: datetime) -> str:
    return slot_dt.strftime("%Y-%m-%dT%H:%M")


def _parse_iso_datetime(raw: Any, fallback_tz: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=fallback_tz)
    return parsed


def find_current_slot(now_local: datetime) -> datetime:
    """Return the most recent scheduled `(date, hour)` slot `<= now_local`."""
    candidates: list[datetime] = []
    for day_offset in (-1, 0):
        slot_date = now_local.date() + timedelta(days=day_offset)
        for hour in SCHEDULED_HOURS:
            candidates.append(
                datetime.combine(slot_date, time(hour, 0), tzinfo=now_local.tzinfo)
            )
    eligible = [slot for slot in candidates if slot <= now_local]
    return max(eligible)


def resolve_anchor_datetime(
    state: dict[str, Any],
    *,
    now_local: datetime,
    start_date: date,
) -> tuple[datetime, str]:
    """Resolve the anchor timestamp from which scheduled slots are tracked."""
    for key in ("first_slot_after", "installed_at", "last_run_at"):
        parsed = _parse_iso_datetime(state.get(key), now_local.tzinfo)
        if parsed is not None:
            installed = (
                _parse_iso_datetime(state.get("installed_at"), now_local.tzinfo)
                or parsed
            )
            return parsed, installed.isoformat(timespec="seconds")

    if state.get("start_date"):
        anchor = datetime.combine(start_date, time(0, 0), tzinfo=now_local.tzinfo)
        return anchor, anchor.isoformat(timespec="seconds")

    return now_local, now_local.isoformat(timespec="seconds")


def iter_tracked_slots(
    anchor_dt: datetime,
    end_exclusive_dt: datetime,
    *,
    start_date: date,
    window_days: int,
) -> list[datetime]:
    """Enumerate scheduled `(date, hour)` slots in `[anchor_dt, end_exclusive_dt)` within window."""
    end_date = start_date + timedelta(days=window_days)
    slots: list[datetime] = []
    cur_date = min(anchor_dt.date(), start_date)
    limit_date = min(end_exclusive_dt.date(), end_date - timedelta(days=1))
    while cur_date <= limit_date:
        if cur_date >= start_date:
            for hour in SCHEDULED_HOURS:
                slot_dt = datetime.combine(
                    cur_date, time(hour, 0), tzinfo=anchor_dt.tzinfo
                )
                if anchor_dt <= slot_dt < end_exclusive_dt:
                    slots.append(slot_dt)
        cur_date += timedelta(days=1)
    return slots


def load_recorded_slots_from_csv(csv_path: Path, *, fallback_tz: Any) -> set[str]:
    """Collect slot labels already recorded in CSV (including legacy 12-col rows)."""
    recorded: set[str] = set()
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return recorded
    with csv_path.open("r", encoding="utf-8", newline="") as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            explicit_slot = str(row.get("scheduled_slot") or "").strip()
            if explicit_slot:
                recorded.add(explicit_slot)
                continue
            ts = _parse_iso_datetime(row.get("timestamp_iso"), fallback_tz)
            if ts is not None:
                recorded.add(format_slot_label(find_current_slot(ts)))
    return recorded


def check_gateway_reachable(
    env: dict[str, str],
    *,
    timeout_seconds: float = 5.0,
) -> tuple[bool, str]:
    """Check gateway reachability via `GET {LLM_BASE_URL}/v1beta/models`."""
    raw_base = (env.get("LLM_BASE_URL") or "").strip().rstrip("/")
    if not raw_base:
        return False, "LLM_BASE_URL is not configured"
    models_url = (
        f"{raw_base}/models"
        if raw_base.endswith("/v1beta")
        else f"{raw_base}/v1beta/models"
    )
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = (env.get("LLM_API_KEY") or env.get("LLM_KEY") or "").strip()
    if api_key:
        headers["x-goog-api-key"] = api_key
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(models_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status_code = getattr(resp, "status", 200)
            if 200 <= int(status_code) < 300:
                return True, ""
            return False, f"Gateway returned HTTP {status_code} from {models_url}"
    except urllib.error.HTTPError as exc:
        return False, f"Gateway HTTP {exc.code} at {models_url}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return (
            False,
            f"Gateway unreachable at {models_url}: {type(exc).__name__}: {reason}",
        )


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}
    raw = state_file.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object in state file: {state_file}")
    return data


def save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_repo_dotenv(dotenv_path: Path) -> dict[str, str]:
    """Parse key=value pairs from repo `.env` without logging or exposing secrets."""
    parsed: dict[str, str] = {}
    if not dotenv_path.exists():
        return parsed
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and (
            (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")
        ):
            val = val[1:-1]
        if key:
            parsed[key] = val
    return parsed


def build_child_env(*, live_mode: bool) -> dict[str, str]:
    """Build subprocess env inheriting repo `.env` so cron/launchd runs find gateway config."""
    env = dict(os.environ)
    for key, val in load_repo_dotenv(REPO_ROOT / ".env").items():
        env.setdefault(key, val)
    if live_mode:
        env.setdefault("ENVIRONMENT", "development")
    else:
        env.setdefault("ENVIRONMENT", "test")
    return env


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FocusFlow scheduled AI evaluation within a 7-day monitoring window.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help="Number of days from start_date to keep running evals (default: 7).",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        default=None,
        help=(
            "Dataset path or filename under backend/tests/ai_evals/datasets/ "
            "(repeatable; defaults to golden_planning_18_goals.jsonl plus optional hard_planning_6_goals.jsonl)."
        ),
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Include e2e flag when supported by eval_runner.",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Path to state JSON tracking start_date.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for run JSONs and hourly_stage_metrics.{jsonl,csv}.",
    )
    parser.add_argument(
        "--trials-per-goal",
        type=int,
        default=1,
        help="Trials per goal passed to eval_runner (default: 1).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrency passed to eval_runner (default: 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without executing eval_runner or writing files.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run eval_runner in offline --mock mode instead of --live.",
    )
    parser.add_argument(
        "--now-iso",
        type=str,
        default=None,
        help="Optional ISO-8601 local timestamp override for deterministic slot/backfill testing.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.window_days < 1:
        print("--window-days must be >= 1", file=sys.stderr)
        return 2

    system_tz = datetime.now().astimezone().tzinfo
    if args.now_iso:
        parsed_now = _parse_iso_datetime(args.now_iso, system_tz)
        if parsed_now is None:
            print(f"Invalid --now-iso timestamp: {args.now_iso!r}", file=sys.stderr)
            return 2
        now_local = parsed_now
    else:
        now_local = datetime.now().astimezone()
    today = now_local.date()

    state = load_state(args.state_file)
    start_date_str = str(state.get("start_date") or today.isoformat())
    start_date = date.fromisoformat(start_date_str)
    elapsed_days = (today - start_date).days

    if elapsed_days >= args.window_days:
        print(
            f"[scheduled-eval] {args.window_days}-day window completed "
            f"(start_date={start_date_str}, today={today.isoformat()}, elapsed_days={elapsed_days}). "
            "Exiting 0 without running eval calls."
        )
        return 0

    anchor_dt, installed_at_iso = resolve_anchor_datetime(
        state,
        now_local=now_local,
        start_date=start_date,
    )
    current_slot_dt = find_current_slot(now_local)
    current_slot_label = format_slot_label(current_slot_dt)
    delay_delta = now_local - current_slot_dt
    if delay_delta > timedelta(minutes=DELAYED_WAKE_THRESHOLD_MINUTES):
        slot_status = "DELAYED_WAKE"
        slot_reason = (
            f"Triggered at {now_local.strftime('%H:%M')} after "
            f"{current_slot_dt.hour:02d}:00 slot (host wake/delay)"
        )
    else:
        slot_status = "OK"
        slot_reason = ""

    csv_path = args.out_dir / "hourly_stage_metrics.csv"
    recorded_slots: set[str] = {
        str(s).strip() for s in (state.get("recorded_slots") or []) if str(s).strip()
    }
    recorded_slots |= load_recorded_slots_from_csv(
        csv_path, fallback_tz=now_local.tzinfo
    )

    prior_slots = iter_tracked_slots(
        anchor_dt,
        current_slot_dt,
        start_date=start_date,
        window_days=args.window_days,
    )
    missing_prior_slots = [
        slot_dt
        for slot_dt in prior_slots
        if format_slot_label(slot_dt) not in recorded_slots
    ]

    dataset_specs = resolve_dataset_specs(args.datasets, e2e=args.e2e)
    python_bin = resolve_backend_python()
    mode_flag = "--mock" if args.mock else "--live"
    mode_label = "mock" if args.mock else "live"

    supports_e2e_flag = False
    if any(use_e2e for _, use_e2e in dataset_specs):
        supports_e2e_flag = _eval_runner_supports_flag(python_bin, "--e2e")

    runs_dir = args.out_dir / "runs"
    planned_runs: list[tuple[Path, Path, list[str]]] = []
    for dataset_path, use_e2e in dataset_specs:
        ts_slug = now_local.strftime("%Y%m%d_%H%M%S")
        report_path = runs_dir / f"{ts_slug}_{dataset_path.stem}.json"
        cmd = [
            str(python_bin),
            "-m",
            "tests.ai_evals.eval_runner",
            "--dataset",
            str(dataset_path),
            "--trials-per-goal",
            str(max(1, args.trials_per_goal)),
            "--concurrency",
            str(max(1, args.concurrency)),
            "--output",
            str(report_path),
            mode_flag,
        ]
        if use_e2e:
            if supports_e2e_flag:
                cmd.append("--e2e")
            elif not args.dry_run:
                print(
                    f"[scheduled-eval] Note: eval_runner does not support --e2e yet; "
                    f"running {dataset_path.name} with standard CLI flags.",
                    file=sys.stderr,
                )
        planned_runs.append((dataset_path, report_path, cmd))

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "today": today.isoformat(),
                    "start_date": start_date_str,
                    "elapsed_days": elapsed_days,
                    "window_days": args.window_days,
                    "mode": mode_label,
                    "python_bin": str(python_bin),
                    "state_file": str(args.state_file),
                    "out_dir": str(args.out_dir),
                    "slot_plan": {
                        "installed_at": installed_at_iso,
                        "first_slot_after": anchor_dt.isoformat(timespec="seconds"),
                        "current_slot": current_slot_label,
                        "status": slot_status,
                        "reason": slot_reason,
                        "missing_prior_slots": [
                            format_slot_label(s) for s in missing_prior_slots
                        ],
                    },
                    "runs": [
                        {
                            "dataset": str(ds),
                            "report_path": str(rp),
                            "command": cmd,
                        }
                        for ds, rp, cmd in planned_runs
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if missing_prior_slots:
        backfill_rows = [
            build_slot_event_row(
                event_ts=slot_dt,
                scheduled_slot=format_slot_label(slot_dt),
                status="MISSED_SLEEP",
                reason="Missed scheduled slot (host asleep or launchd skipped)",
            )
            for slot_dt in missing_prior_slots
        ]
        append_metrics(args.out_dir, backfill_rows)
        for slot_dt in missing_prior_slots:
            recorded_slots.add(format_slot_label(slot_dt))
        print(
            f"[scheduled-eval] Backfilled {len(backfill_rows)} missed slot(s): "
            f"{[format_slot_label(s) for s in missing_prior_slots]}",
            flush=True,
        )

    runs_dir.mkdir(parents=True, exist_ok=True)
    completed_reports: list[str] = []
    total_rows_written = 0
    child_env = build_child_env(live_mode=not args.mock)

    if not args.mock:
        reachable, reach_err = check_gateway_reachable(child_env, timeout_seconds=5.0)
        if not reachable:
            unreachable_row = build_slot_event_row(
                event_ts=now_local,
                scheduled_slot=current_slot_label,
                status="COBHUB_UNREACHABLE",
                reason=reach_err,
            )
            append_metrics(args.out_dir, [unreachable_row])
            recorded_slots.add(current_slot_label)
            state.update(
                {
                    "start_date": start_date_str,
                    "window_days": args.window_days,
                    "installed_at": installed_at_iso,
                    "first_slot_after": anchor_dt.isoformat(timespec="seconds"),
                    "recorded_slots": sorted(recorded_slots),
                    "runs_count": int(state.get("runs_count", 0)) + 1,
                    "last_run_at": now_local.isoformat(timespec="seconds"),
                    "last_status": "error",
                    "last_error": reach_err,
                }
            )
            save_state(args.state_file, state)
            print(f"[scheduled-eval] ERROR: {reach_err}", file=sys.stderr)
            return 1

    for dataset_path, report_path, cmd in planned_runs:
        run_ts = now_local if args.now_iso else datetime.now().astimezone()
        print(
            f"[scheduled-eval] Running {dataset_path.name} ({mode_label}) -> {report_path}",
            flush=True,
        )
        proc = subprocess.run(cmd, cwd=str(BACKEND_DIR), env=child_env, check=False)
        if proc.returncode != 0:
            err_msg = f"eval_runner exited {proc.returncode} on {dataset_path.name}"
            err_row = build_slot_event_row(
                event_ts=run_ts,
                scheduled_slot=current_slot_label,
                status="EVAL_ERROR",
                reason=err_msg,
                dataset=dataset_path.name,
            )
            append_metrics(args.out_dir, [err_row])
            recorded_slots.add(current_slot_label)
            state.update(
                {
                    "start_date": start_date_str,
                    "window_days": args.window_days,
                    "installed_at": installed_at_iso,
                    "first_slot_after": anchor_dt.isoformat(timespec="seconds"),
                    "recorded_slots": sorted(recorded_slots),
                    "runs_count": int(state.get("runs_count", 0)) + 1,
                    "last_run_at": run_ts.isoformat(timespec="seconds"),
                    "last_status": "error",
                    "last_error": err_msg,
                }
            )
            save_state(args.state_file, state)
            print(
                f"[scheduled-eval] ERROR: eval_runner failed with code {proc.returncode} "
                f"for {dataset_path.name}",
                file=sys.stderr,
            )
            return proc.returncode

        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = extract_metric_rows(
            report,
            run_ts=run_ts,
            dataset_name=dataset_path.name,
            mode_fallback=mode_label,
            scheduled_slot=current_slot_label,
            status=slot_status,
            reason=slot_reason,
        )
        jsonl_path, csv_out_path = append_metrics(args.out_dir, rows)
        total_rows_written += len(rows)
        completed_reports.append(str(report_path))
        print(
            f"[scheduled-eval] Appended {len(rows)} stage rows to {jsonl_path} and {csv_out_path}",
            flush=True,
        )

    recorded_slots.add(current_slot_label)
    last_run_ts = now_local if args.now_iso else datetime.now().astimezone()
    state.update(
        {
            "start_date": start_date_str,
            "window_days": args.window_days,
            "installed_at": installed_at_iso,
            "first_slot_after": anchor_dt.isoformat(timespec="seconds"),
            "recorded_slots": sorted(recorded_slots),
            "runs_count": int(state.get("runs_count", 0)) + 1,
            "last_run_at": last_run_ts.isoformat(timespec="seconds"),
            "last_status": "ok",
            "last_reports": completed_reports,
            "last_rows_appended": total_rows_written,
        }
    )
    state.pop("last_error", None)
    save_state(args.state_file, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
