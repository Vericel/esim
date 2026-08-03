import subprocess
import sys
from pathlib import Path


def test_docs_check_accepts_existing_markdown_file_and_fragment(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "guide.md").write_text(
        "See [installation](reference.md#installation).\n",
        encoding="utf-8",
    )
    (tmp_path / "reference.md").write_text(
        "# Installation\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (0, "", "")


def test_docs_check_reports_missing_markdown_target(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "guide.md").write_text(
        "See [missing](missing.md).\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        1,
        "",
        "guide.md:1: missing.md: file does not exist\n",
    )


def test_docs_check_reports_missing_markdown_fragment(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "guide.md").write_text(
        "See [missing section](reference.md#missing-section).\n",
        encoding="utf-8",
    )
    (tmp_path / "reference.md").write_text(
        "# Installation\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        1,
        "",
        "guide.md:1: reference.md#missing-section: fragment does not exist\n",
    )


def test_docs_check_validates_html_href_fragments_and_src_files(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "index.html").write_text(
        '<a href="details.html#usage">Usage</a>\n'
        '<img src="missing.png" alt="missing" />\n',
        encoding="utf-8",
    )
    (tmp_path / "details.html").write_text(
        '<section id="usage">Usage</section>\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        1,
        "",
        "index.html:2: missing.png: file does not exist\n",
    )


def test_docs_check_ignores_external_urls_mail_and_template_targets(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "guide.md").write_text(
        "[web](https://example.com/docs#usage) "
        "[mail](mailto:maintainer@example.com) "
        "[template](<WHEELHOUSE>)\n",
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text(
        '<a href="https://example.com">Web</a>\n'
        '<img src="data:image/png;base64,AAAA" alt="inline" />\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (0, "", "")


def test_docs_check_reports_all_diagnostics_in_stable_path_order(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    (tmp_path / "z-last.md").write_text(
        "[missing z](missing-z.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "a-first.md").write_text(
        "[missing a](missing-a.md)\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        1,
        "",
        "a-first.md:1: missing-a.md: file does not exist\n"
        "z-last.md:1: missing-z.md: file does not exist\n",
    )


def test_docs_check_ignores_generated_and_runtime_directories(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    for directory in (".planning", ".venv", ".tools", "build", "node_modules"):
        generated = tmp_path / directory
        generated.mkdir()
        (generated / "generated.md").write_text(
            "[not a project document](missing.md)\n",
            encoding="utf-8",
        )

    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (0, "", "")
