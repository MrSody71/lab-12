#!/usr/bin/env python3
"""
AI Code Review script for GitHub Actions.

Flow:
  1. Read pr_diff.txt produced by `git diff origin/<base>...HEAD -- '*.py'`
  2. Guard: skip if diff is empty or exceeds MAX_DIFF_LINES
  3. Send diff to Anthropic API for a structured review
  4. Post the result as a PR comment via GitHub REST API
  5. On any error — post a human-readable fallback comment instead of crashing

Required environment variables
--------------------------------
  ANTHROPIC_API_KEY   — Anthropic secret key
  GITHUB_TOKEN        — GitHub Actions token (secrets.GITHUB_TOKEN)
  GITHUB_REPOSITORY   — "owner/repo"  (set automatically by Actions)
  PR_NUMBER           — pull_request.number  (set in workflow env)

Dependencies: anthropic (pip install anthropic)
Everything else uses the Python standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DIFF_FILE = "pr_diff.txt"
MAX_DIFF_LINES = 4000
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = (
    "Ты — senior Python code reviewer. "
    "Анализируй только показанный diff. "
    "Будь конкретен: указывай имена файлов и номера строк там, где это возможно. "
    "Не пересказывай код — объясняй проблему и давай конкретную рекомендацию."
)

USER_PROMPT_TEMPLATE = """\
Проведи code review следующего diff. Найди и опиши проблемы в четырёх категориях:

1. **Security issues** — SQL-инъекции, небезопасные зависимости, открытые секреты, \
некорректная валидация входных данных, небезопасные HTTP-заголовки.
2. **Bugs** — логические ошибки, необработанные исключения, off-by-one, \
неправильные предусловия/постусловия.
3. **Style violations** — нарушения PEP 8, непоследовательное именование, \
излишняя сложность, отсутствие type hints там, где они уместны.
4. **Missing tests** — публичные функции или ветки кода, не покрытые тестами; \
отсутствующие edge-case тесты.

Формат ответа для каждой проблемы:
> **[Категория]** `path/to/file.py` (строка N): краткое описание → рекомендация

Если проблем в какой-либо категории нет — напиши «Проблем не обнаружено».
Завершай ревью кратким итогом (1–3 предложения).

```diff
{diff}
```
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_diff() -> str:
    """Return contents of pr_diff.txt, or empty string if file is missing."""
    try:
        with open(DIFF_FILE, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""


def require_env(name: str) -> str:
    """Return env variable or exit with an error message."""
    value = os.environ.get(name, "")
    if not value:
        print(f"ERROR: required environment variable {name!r} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def post_github_comment(token: str, repo: str, pr_number: str, body: str) -> None:
    """POST a comment to a GitHub PR issue thread."""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    payload = json.dumps({"body": body}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-review-bot/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"Comment posted successfully: HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body_bytes = exc.read()
        print(
            f"GitHub API returned HTTP {exc.code}: {exc.reason}\n"
            f"{body_bytes.decode('utf-8', errors='replace')}",
            file=sys.stderr,
        )
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Network error posting comment: {exc.reason}", file=sys.stderr)
        sys.exit(1)


def call_anthropic_api(api_key: str, diff: str) -> str:
    """Send the diff to Anthropic and return the review text."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("Пакет 'anthropic' не установлен (pip install anthropic)") from exc

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(diff=diff),
            }
        ],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Comment builders
# ---------------------------------------------------------------------------


def comment_empty_diff() -> str:
    return (
        "## 🤖 AI Code Review\n\n"
        "> ℹ️ **Diff пустой** — изменений в Python-файлах не обнаружено.\n\n"
        "Ревью пропущено."
    )


def comment_diff_too_large(lines: int) -> str:
    return (
        f"## 🤖 AI Code Review\n\n"
        f"> ⚠️ **Diff слишком большой**: {lines} строк (лимит {MAX_DIFF_LINES}).\n\n"
        "Автоматическое ревью пропущено. "
        "Рассмотрите возможность разбить PR на меньшие части."
    )


def comment_api_error(reason: str) -> str:
    return (
        "## 🤖 AI Code Review\n\n"
        f"> ❌ **Ревью недоступно**: {reason}\n\n"
        "Пожалуйста, проведите ревью вручную или повторите запуск workflow."
    )


def comment_review(review_text: str, diff_lines: int) -> str:
    return (
        "## 🤖 AI Code Review\n\n"
        f"*Проанализировано строк diff: **{diff_lines}***\n\n"
        "---\n\n"
        f"{review_text}\n\n"
        "---\n"
        f"*Сгенерировано автоматически · модель `{MODEL}`*"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    # GitHub API credentials — no fallback possible without these
    github_token = require_env("GITHUB_TOKEN")
    github_repo = require_env("GITHUB_REPOSITORY")
    pr_number = require_env("PR_NUMBER")

    # Anthropic key — missing → fallback comment (don't hard-crash)
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    diff = read_diff()
    diff_lines = diff.count("\n")

    # ── Guard: empty diff ──────────────────────────────────────────────────
    if not diff.strip():
        post_github_comment(github_token, github_repo, pr_number, comment_empty_diff())
        return

    # ── Guard: diff too large ──────────────────────────────────────────────
    if diff_lines > MAX_DIFF_LINES:
        post_github_comment(
            github_token, github_repo, pr_number, comment_diff_too_large(diff_lines)
        )
        return

    # ── Guard: API key missing ─────────────────────────────────────────────
    if not anthropic_api_key:
        post_github_comment(
            github_token,
            github_repo,
            pr_number,
            comment_api_error("секрет ANTHROPIC_API_KEY не задан в репозитории"),
        )
        return

    # ── AI review ─────────────────────────────────────────────────────────
    try:
        review_text = call_anthropic_api(anthropic_api_key, diff)
        body = comment_review(review_text, diff_lines)
    except Exception as exc:  # network errors, model errors, etc.
        print(f"Anthropic API call failed: {exc}", file=sys.stderr)
        body = comment_api_error(str(exc))

    post_github_comment(github_token, github_repo, pr_number, body)


if __name__ == "__main__":
    main()
