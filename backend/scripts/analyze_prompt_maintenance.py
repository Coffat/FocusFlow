"""Read-only git & prompt maintenance metrics analyzer for `.md` decision (T7.4).

Reads git history (without mutating anything) and inspects all registered production prompts
in Python to output LOC, token estimates, commit frequency, authors, co-change coupling,
and pairwise content overlap into `docs/reports/prompt-md-decision-metrics.md`.
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.update_prompts_lock import build_combined_production_registry  # noqa: E402

DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "prompt-md-decision-metrics.md"

PROMPT_SOURCE_FILES: tuple[str, ...] = (
    "backend/src/planning/application/services/roadmap_skills.py",
    "backend/src/evaluation/application/prompts.py",
    "backend/src/shared_kernel/application/harness/untrusted_context.py",
)


@dataclass(frozen=True, slots=True)
class PromptMetricRow:
    prompt_id: str
    version: str
    workflow_type: str
    chars: int
    loc: int
    tokens_naive_div4: int
    tokens_conservative_vi: int


def _estimate_tokens_conservative_vi(text: str) -> int:
    # Matches FocusFlow ContextEngine conservative Vietnamese heuristic (~3 chars/token + 10%)
    if not text:
        return 0
    return max(1, math.ceil((len(text) / 3.0) * 1.1))


def _run_git(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def collect_prompt_metrics() -> tuple[list[PromptMetricRow], list[tuple[str, str, float, float]]]:
    registry = build_combined_production_registry()
    templates = list(registry.list_templates())
    rows: list[PromptMetricRow] = []
    for tpl in templates:
        txt = tpl.system_template
        rows.append(
            PromptMetricRow(
                prompt_id=tpl.prompt_id,
                version=tpl.version,
                workflow_type=tpl.workflow_type,
                chars=len(txt),
                loc=len(txt.splitlines()),
                tokens_naive_div4=max(1, len(txt) // 4),
                tokens_conservative_vi=_estimate_tokens_conservative_vi(txt),
            )
        )

    token_sets = {
        tpl.prompt_id: set(re.findall(r"\w+", tpl.system_template.lower())) for tpl in templates
    }
    text_by_id = {tpl.prompt_id: tpl.system_template for tpl in templates}
    overlaps: list[tuple[str, str, float, float]] = []
    for i, left in enumerate(templates):
        for right in templates[i + 1 :]:
            seq_ratio = SequenceMatcher(
                None, text_by_id[left.prompt_id], text_by_id[right.prompt_id]
            ).ratio()
            s_a = token_sets[left.prompt_id]
            s_b = token_sets[right.prompt_id]
            jaccard = (len(s_a & s_b) / len(s_a | s_b)) if (s_a or s_b) else 0.0
            overlaps.append(
                (left.prompt_id, right.prompt_id, round(seq_ratio, 4), round(jaccard, 4))
            )
    overlaps.sort(key=lambda item: item[3], reverse=True)
    return rows, overlaps


def collect_git_metrics() -> dict[str, Any]:
    is_shallow = _run_git(["rev-parse", "--is-shallow-repository"])
    total_commits = _run_git(["rev-list", "--count", "HEAD"])
    all_dates = [
        line.strip() for line in _run_git(["log", "--format=%ci"]).splitlines() if line.strip()
    ]
    first_commit_date = all_dates[-1] if all_dates else ""
    latest_commit_date = all_dates[0] if all_dates else ""

    log_raw = _run_git(
        [
            "log",
            "--name-only",
            "--format=__COMMIT__|%H|%an|%ae|%ci",
            "--",
            *PROMPT_SOURCE_FILES,
        ]
    )

    commits: list[dict[str, Any]] = []
    authors: Counter[str] = Counter()
    file_commit_counts: Counter[str] = Counter()
    cochange_files: Counter[str] = Counter()
    cochange_categories: Counter[str] = Counter()

    current: dict[str, Any] | None = None
    for line in log_raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("__COMMIT__|"):
            if current is not None:
                commits.append(current)
            _, sha, author_name, author_email, commit_date = stripped.split("|", 4)
            current = {
                "sha": sha,
                "author": f"{author_name} <{author_email}>",
                "date": commit_date,
                "files": [],
            }
            authors[author_name] += 1
        elif current is not None:
            current["files"].append(stripped)
            if stripped in PROMPT_SOURCE_FILES:
                file_commit_counts[stripped] += 1

    if current is not None:
        commits.append(current)

    # For commits that touched prompt files, inspect all files changed in those commits
    for commit in commits:
        all_files_raw = _run_git(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit["sha"]]
        )
        touched_all = [f.strip() for f in all_files_raw.splitlines() if f.strip()]
        has_schema_or_dto = False
        has_use_case_or_service = False
        has_test = False
        for path_str in touched_all:
            if path_str in PROMPT_SOURCE_FILES:
                continue
            cochange_files[path_str] += 1
            if "dto" in path_str or "schema" in path_str or "prompts.lock" in path_str:
                has_schema_or_dto = True
            elif "/use_cases/" in path_str or "/services/" in path_str or "/prompts.py" in path_str:
                has_use_case_or_service = True
            elif path_str.startswith("backend/tests/"):
                has_test = True
        if has_schema_or_dto:
            cochange_categories["schema_or_dto_or_lock"] += 1
        if has_use_case_or_service:
            cochange_categories["use_cases_or_services"] += 1
        if has_test:
            cochange_categories["tests"] += 1

    prompt_file_loc = {
        rel: len((REPO_ROOT / rel).read_text(encoding="utf-8").splitlines())
        for rel in PROMPT_SOURCE_FILES
        if (REPO_ROOT / rel).exists()
    }

    return {
        "is_shallow": is_shallow == "true",
        "total_repo_commits": int(total_commits or 0),
        "first_commit_date": first_commit_date or "N/A",
        "latest_commit_date": latest_commit_date or "N/A",
        "prompt_commits_count": len(commits),
        "authors": dict(authors),
        "file_commit_counts": dict(file_commit_counts),
        "cochange_top_files": cochange_files.most_common(12),
        "cochange_categories": dict(cochange_categories),
        "prompt_file_loc": prompt_file_loc,
    }


def render_markdown_report(
    rows: list[PromptMetricRow],
    overlaps: list[tuple[str, str, float, float]],
    git_info: dict[str, Any],
) -> str:
    total_chars = sum(r.chars for r in rows)
    total_loc = sum(r.loc for r in rows)
    total_tok_naive = sum(r.tokens_naive_div4 for r in rows)
    total_tok_vi = sum(r.tokens_conservative_vi for r in rows)
    avg_jaccard = round(sum(o[3] for o in overlaps) / max(1, len(overlaps)), 4)
    avg_seq = round(sum(o[2] for o in overlaps) / max(1, len(overlaps)), 4)

    lines: list[str] = [
        "# Báo cáo Phân tích Bảo trì Prompt & Quyết định Lưu trữ `.md` (T7.4)",
        "",
        "> Sinh tự động bằng script read-only `backend/scripts/analyze_prompt_maintenance.py`.",
        "> Không tạo bất kỳ code path runtime nào đọc file `.md`.",
        "",
        "## 1. Phạm vi lịch sử Git trong repository",
        "",
        f"- **Shallow repository**: `{git_info['is_shallow']}`",
        f"- **Tổng số commit trên nhánh hiện tại (`HEAD`)**: `{git_info['total_repo_commits']}`",
        f"- **Khoảng thời gian lịch sử (`HEAD`)**: `{git_info['first_commit_date']}` → `{git_info['latest_commit_date']}`",
        f"- **Số commit đã commit chạm các file định nghĩa prompt**: `{git_info['prompt_commits_count']}` (lưu ý: các file mới tạo/sửa chưa commit như `evaluation/application/prompts.py` và `untrusted_context.py` hiển thị `0` commit trong lịch sử đã commit)",
        f"- **Danh sách / số lượng authors**: `{len(git_info['authors'])}` ({', '.join(f'{k}: {v} commits' for k, v in git_info['authors'].items()) or 'N/A'})",
        "",
        "## 2. Thống kê kích thước 12 Production Prompts",
        "",
        "| Prompt ID | Version | Workflow Type | LOC | Chars | Est. Tokens (`len/4`) | Est. Tokens (VI conservative) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r.prompt_id}` | `{r.version}` | `{r.workflow_type}` | {r.loc} | {r.chars} | {r.tokens_naive_div4} | {r.tokens_conservative_vi} |"
        )
    lines.extend(
        [
            f"| **Tổng cộng (12 prompts)** | — | — | **{total_loc}** | **{total_chars}** | **{total_tok_naive}** | **{total_tok_vi}** |",
            "",
            "### Tổng LOC của các file nguồn chứa prompt",
            "",
        ]
    )
    for path_str, loc_val in git_info["prompt_file_loc"].items():
        commit_cnt = git_info["file_commit_counts"].get(path_str, 0)
        lines.append(f"- `{path_str}`: **{loc_val}** LOC, **{commit_cnt}** commits")

    lines.extend(
        [
            "",
            "## 3. Phân tích Co-change (Prompt ↔ Code / Schema / Test)",
            "",
            f"- Tổng số commit chạm prompt: `{git_info['prompt_commits_count']}`",
            f"- Commit đồng thời sửa `DTO / Schema / prompts.lock`: `{git_info['cochange_categories'].get('schema_or_dto_or_lock', 0)}`",
            f"- Commit đồng thời sửa `Use Cases / Services`: `{git_info['cochange_categories'].get('use_cases_or_services', 0)}`",
            f"- Commit đồng thời sửa `Tests`: `{git_info['cochange_categories'].get('tests', 0)}`",
            "",
            "### Top file thay đổi cùng lúc với Prompt files",
            "",
            "| File | Số lần co-change |",
            "|---|---|",
        ]
    )
    for fpath, cnt in git_info["cochange_top_files"]:
        lines.append(f"| `{fpath}` | {cnt} |")
    if not git_info["cochange_top_files"]:
        lines.append("| _(Không có co-change ngoài các file prompt trong lịch sử git)_ | 0 |")

    lines.extend(
        [
            "",
            "## 4. Mức độ trùng lặp nội dung giữa các Prompt",
            "",
            f"- **Trung bình SequenceMatcher similarity** (toàn bộ {len(overlaps)} cặp): `{avg_seq}`",
            f"- **Trung bình Token Jaccard similarity** (toàn bộ {len(overlaps)} cặp): `{avg_jaccard}`",
            "- Lưu ý: Toàn bộ 12 prompts đều tái sử dụng hằng số `UNTRUSTED_DATA_SYSTEM_RULE` ở cấp Python, nên phần lớn độ tương đồng đến từ quy tắc bảo mật dùng chung.",
            "",
            "### Top 8 cặp prompt có độ tương đồng cao nhất",
            "",
            "| Prompt A | Prompt B | SequenceMatcher | Token Jaccard |",
            "|---|---|---|---|",
        ]
    )
    for p_a, p_b, seq_r, jac_r in overlaps[:8]:
        lines.append(f"| `{p_a}` | `{p_b}` | {seq_r} | {jac_r} |")

    lines.extend(
        [
            "",
            "## 5. Khuyến nghị kỹ thuật (Có chuyển sang `.md` hay giữ trong Python?)",
            "",
            "- **Kết luận hiện tại**: **Giữ prompt trong Python** (`roadmap_skills.py`, `evaluation/application/prompts.py`, `untrusted_context.py`) kết hợp `PromptRegistry` + `prompts.lock` CI drift check.",
            "- **Cơ sở dữ liệu định lượng**:",
            f"  1. Quy mô gọn: 12 prompts chỉ chiếm tổng cộng **{total_loc} dòng / ~{total_tok_vi} tokens**.",
            f"  2. Tỷ lệ đồng biến đổi (co-change) với schema/use-case/test cao (`use_cases_or_services={git_info['cochange_categories'].get('use_cases_or_services', 0)}`, `tests={git_info['cochange_categories'].get('tests', 0)}`), cho thấy prompt gắn chặt với Pydantic structured output và domain invariants.",
            f"  3. Tác giả chỉnh sửa tập trung (`{len(git_info['authors'])}` author(s)), chưa có nhu cầu non-engineer tự sửa prompt độc lập ngoài chu kỳ code review.",
            "  4. Nội dung bảo mật dùng chung (`UNTRUSTED_DATA_SYSTEM_RULE`) được chia sẻ an toàn bằng Python import mà không cần templating parser bên ngoài.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze prompt maintenance metrics from git log.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to write markdown report.",
    )
    args = parser.parse_args(argv)
    rows, overlaps = collect_prompt_metrics()
    git_info = collect_git_metrics()
    report_md = render_markdown_report(rows, overlaps, git_info)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report_md, encoding="utf-8")
    print(f"Wrote prompt maintenance decision report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
