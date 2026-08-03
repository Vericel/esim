import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_IGNORED_DIRECTORIES = {
    ".git",
    ".planning",
    ".pytest_cache",
    ".tools",
    ".venv",
    ".worktrees",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fragments: set[str] = set()
        self.references: list[tuple[int, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del tag
        line, _ = self.getpos()
        for name, value in attrs:
            if value is None:
                continue
            if name in {"id", "name"}:
                self.fragments.add(value)
            elif name in {"href", "src"}:
                self.references.append((line, value))


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _ignored_target(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "data:", "//")) or (
        target.startswith("<") and target.endswith(">")
    )


def _markdown_fragments(document: Path) -> set[str]:
    content = document.read_text(encoding="utf-8")
    fragments = set()
    for match in _MARKDOWN_HEADING.finditer(content):
        heading = match.group(1).strip().lower()
        slug = re.sub(r"[^\w\s-]", "", heading)
        fragments.add(re.sub(r"[\s]+", "-", slug))
    return fragments


def _html_parser(document: Path) -> _DocumentParser:
    parser = _DocumentParser()
    parser.feed(document.read_text(encoding="utf-8"))
    return parser


def _documents(root: Path, suffix: str) -> list[Path]:
    documents = []
    for directory, directory_names, file_names in os.walk(root):
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in _IGNORED_DIRECTORIES and not name.startswith(".tmp-")
        )
        documents.extend(
            Path(directory) / name
            for name in sorted(file_names)
            if Path(name).suffix.lower() == suffix
        )
    return documents


def main() -> int:
    root = Path.cwd()
    diagnostics: list[tuple[str, int, str, str]] = []
    for document in _documents(root, ".md"):
        content = document.read_text(encoding="utf-8")
        for match in _MARKDOWN_LINK.finditer(content):
            target = match.group(1)
            if _ignored_target(target):
                continue
            path_text, separator, fragment = target.partition("#")
            target_document = document.parent / path_text if path_text else document
            if path_text and not target_document.exists():
                relative_document = document.relative_to(root)
                line = _line_number(content, match.start())
                diagnostics.append(
                    (str(relative_document), line, target, "file does not exist")
                )
                continue
            if (
                separator
                and fragment
                and target_document.suffix.lower() == ".md"
                and fragment not in _markdown_fragments(target_document)
            ):
                relative_document = document.relative_to(root)
                line = _line_number(content, match.start())
                diagnostics.append(
                    (str(relative_document), line, target, "fragment does not exist")
                )
    for document in _documents(root, ".html"):
        parser = _html_parser(document)
        for line, target in parser.references:
            if _ignored_target(target):
                continue
            path_text, separator, fragment = target.partition("#")
            target_document = document.parent / path_text if path_text else document
            if path_text and not target_document.exists():
                relative_document = document.relative_to(root)
                diagnostics.append(
                    (str(relative_document), line, target, "file does not exist")
                )
                continue
            if (
                separator
                and fragment
                and target_document.suffix.lower() == ".html"
                and fragment not in _html_parser(target_document).fragments
            ):
                relative_document = document.relative_to(root)
                diagnostics.append(
                    (str(relative_document), line, target, "fragment does not exist")
                )
    for document, line, target, reason in sorted(diagnostics):
        print(f"{document}:{line}: {target}: {reason}", file=sys.stderr)
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
