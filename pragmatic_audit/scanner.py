from __future__ import annotations

import os
import re
from pathlib import Path

from .config import Config
from .gitinfo import run_git
from .models import Repo, SourceFile

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
}

MAX_FILE_BYTES = 2_000_000
TEST_DIRS = {
    "test",
    "tests",
    "spec",
    "specs",
    "__tests__",
    "e2e",
    "integration",
    "testing",
    "testdata",
}
TEST_FILE_RE = re.compile(
    r"(^test_.*\.py$|.*_test\.py$|^conftest\.py$|.*\.(test|spec)\.(js|jsx|ts|tsx)$|"
    r".*(Test|Tests|Spec)\.(java|kt|cs|scala)$|.*_spec\.rb$)",
    re.IGNORECASE,
)
SUPPRESS_FILE_RE = re.compile(r"pragmatic-audit:\s*ignore-file\s+([^\n]+)", re.IGNORECASE)
SUPPRESS_LINE_RE = re.compile(r"pragmatic-audit:\s*ignore\s+([^\n]+)", re.IGNORECASE)
RULE_TOKEN_RE = re.compile(r"^(?:\*|PP-[A-Z0-9-]+)$")
README_NAMES = {"readme.md", "readme.rst", "readme.txt", "readme.markdown", "readme"}


def scan(root: Path, config: Config) -> Repo:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"path is not a directory: {root}")

    files: list[SourceFile] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        rel_dir = _rel(current, root)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not config.should_exclude(_join(rel_dir, name))
            and not name.startswith(".git")
        )
        for filename in sorted(filenames):
            path = current / filename
            rel = _join(rel_dir, filename)
            if config.should_exclude(rel):
                continue
            language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
            if language is None:
                continue
            if config.languages and language not in config.languages:
                continue
            text = _read_text(path)
            if text is None:
                continue
            suppressions, file_suppressions = _parse_suppressions(text)
            files.append(
                SourceFile(
                    path=path,
                    rel=rel,
                    language=language,
                    text=text,
                    lines=text.splitlines(),
                    is_test=_is_test(rel),
                    suppressions=suppressions,
                    file_suppressions=file_suppressions,
                )
            )

    files.sort(key=lambda item: item.rel)
    readme_path, readme_text = _read_readme(root)
    is_git, git_root, tracked_files = _git_metadata(root)
    return Repo(
        root=root,
        files=files,
        is_git=is_git,
        git_root=git_root,
        tracked_files=tracked_files,
        readme_path=readme_path,
        readme_text=readme_text,
    )


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:2048]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _parse_suppressions(text: str) -> tuple[dict[int, set[str]], set[str]]:
    suppressions: dict[int, set[str]] = {}
    file_suppressions: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        if "pragmatic-audit" not in line.lower():
            continue
        for match in SUPPRESS_FILE_RE.finditer(line):
            file_suppressions.update(_rule_ids(match.group(1)))
        for match in SUPPRESS_LINE_RE.finditer(line):
            ids = _rule_ids(match.group(1))
            if ids:
                suppressions.setdefault(number, set()).update(ids)
    return suppressions, file_suppressions


def _rule_ids(raw: str) -> set[str]:
    raw = raw.split("--", 1)[0]
    return {
        token.upper()
        for token in re.split(r"[,\s]+", raw.strip())
        if RULE_TOKEN_RE.match(token.strip().upper())
    }


def _is_test(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    filename = parts[-1]
    if TEST_FILE_RE.match(filename):
        return True
    return any(part.lower() in TEST_DIRS for part in parts[:-1])


def _read_readme(root: Path) -> tuple[Path | None, str]:
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return None, ""
    for entry in entries:
        if entry.is_file() and entry.name.lower() in README_NAMES:
            try:
                return entry, entry.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return entry, ""
    return None, ""


def _git_metadata(root: Path) -> tuple[bool, Path | None, list[str]]:
    top = run_git(root, "rev-parse", "--show-toplevel", timeout=5)
    if top is None or top.returncode != 0:
        return False, None, []
    git_root = Path(top.stdout.strip()).resolve()
    tracked = run_git(root, "ls-files", "-z")
    if tracked is None:
        return True, git_root, []
    names = [item for item in tracked.stdout.split("\0") if item]
    return True, git_root, names


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _join(parent: str, name: str) -> str:
    return f"{parent}/{name}" if parent else name
