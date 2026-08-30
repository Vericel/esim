import subprocess
import sys
from pathlib import Path


def test_generator_cli_creates_both_standalone_user_guides(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    (user_docs / "ff-user-guide.md").write_text(
        "# ff User Guide\n\n## 第一章 使用 {#usage-chapter}\n\n"
        "### Quick Start {#quick-start}\n\n```bash\nff top.f\n```\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### CLI Reference {#cli-reference}\n\nReference.\n",
        encoding="utf-8",
    )
    (user_docs / "esim-user-guide.md").write_text(
        "# esim User Guide\n\n## 第一章 使用 {#usage-chapter}\n\n"
        "### Run Flow {#run-flow}\n\n| Phase | Tool |\n"
        "|---|---|\n| Build | vcs |\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### CLI Reference {#cli-reference}\n\nReference.\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    ff_html = (user_docs / "ff-user-guide.html").read_text(encoding="utf-8")
    esim_html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        completed.returncode,
        completed.stdout,
        completed.stderr,
        ff_html.startswith("<!DOCTYPE html>"),
        '<section id="quick-start">' in ff_html,
        "<style>" in ff_html,
        "https://" not in ff_html,
        '<section id="run-flow">' in esim_html,
        "<table>" in esim_html,
        "https://" not in esim_html,
    ) == (0, "", "", True, True, True, True, True, True, True)


def test_generator_check_reports_each_stale_user_guide(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            f"# {name} User Guide\n\n## 第一章 使用 {{#usage-chapter}}\n\n"
            "### Usage {#usage}\n\nInitial content.\n\n"
            "## 第二章 参考 {#reference-chapter}\n\n"
            "### Reference {#reference}\n\nReference.\n",
            encoding="utf-8",
        )
    command = [
        sys.executable,
        str(project_root / "scripts" / "generate_user_guides.py"),
        "--root",
        str(tmp_path),
    ]
    subprocess.run(command, check=True)
    (user_docs / "ff-user-guide.md").write_text(
        "# ff User Guide\n\n## 第一章 使用 {#usage-chapter}\n\n"
        "### Usage {#usage}\n\nUpdated content.\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### Reference {#reference}\n\nReference.\n",
        encoding="utf-8",
    )
    (user_docs / "esim-user-guide.html").unlink()

    completed = subprocess.run(
        [*command, "--check"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr.splitlines()) == (
        1,
        "",
        [
            f"stale generated user guide: {user_docs / 'ff-user-guide.html'}",
            f"stale generated user guide: {user_docs / 'esim-user-guide.html'}",
        ],
    )


def test_generator_separates_intro_and_uses_explicit_section_ids(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            f"# {name} User Guide\n\nIntroduction.\n\n"
            "## 第一章 入门 {#getting-started}\n\n"
            "### 环境与目录 {#environment}\n\nDetails.\n\n"
            "## 第二章 参考 {#reference-chapter}\n\n"
            "### 速查 {#reference}\n\nReference.\n",
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        '<div class="introduction"><p>Introduction.</p>\n</div>\n'
        '<article class="chapter" id="getting-started">'
        in html
        and '<section id="environment">' in html
        and "{#environment}" not in html
        and '<a class="nav-section-link" href="#environment">环境与目录</a>' in html
    )


def test_generator_uses_collapsible_mobile_navigation(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            f"# {name} User Guide\n\n## 第一章 入门 {{#getting-started}}\n\n"
            "### Quick Start {#quick-start}\n\nDetails.\n\n"
            "## 第二章 参考 {#reference-chapter}\n\n"
            "### Reference {#reference}\n\nReference.\n",
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        '<details class="nav-panel">' in html
        and "<summary>章节导航</summary>" in html
        and ".nav-panel:not([open]) > ul" in html
    )


def test_generator_adds_offline_syntax_colours_to_fenced_code(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    source = (
        "# User Guide\n\n## 第一章 配置 {#configuration-chapter}\n\n"
        "### Configuration {#configuration}\n\n"
        "```yaml\nsimulator: vcs\nflow: two-step\n```\n\n"
        "```bash\nexport DV_HOME=/proj/dv\nesim demo:smoke\n```\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### Reference {#reference}\n\nReference.\n"
    )
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            source,
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        'class="highlight language-yaml"' in html
        and '<span class="syntax-key">simulator</span>' in html
        and '<span class="syntax-command">export</span>' in html
        and ".syntax-key" in html
        and ".syntax-command" in html
        and "https://" not in html
    )


def test_generator_uses_multihue_palette_and_code_language_labels(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    source = (
        "# User Guide\n\n## 第一章 示例 {#examples-chapter}\n\n"
        "### Examples {#examples}\n\n"
        "```yaml\nflow: two-step\n```\n\n"
        "```bash\nesim demo:smoke\n```\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### Reference {#reference}\n\nReference.\n"
    )
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            source,
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        '<span class="code-language">YAML</span>' in html
        and '<span class="code-language">Bash</span>' in html
        and "--accent: #2563eb" in html
        and "--accent-alt: #7c3aed" in html
        and "--accent-warm: #f59e0b" in html
        and "--sidebar: #111827" in html
    )


def test_generator_keeps_desktop_navigation_visible_without_javascript(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            f"# {name} User Guide\n\n## 第一章 入门 {{#getting-started}}\n\n"
            "### Quick Start {#quick-start}\n\nDetails.\n\n"
            "## 第二章 参考 {#reference-chapter}\n\n"
            "### Reference {#reference}\n\nReference.\n",
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        '<ul class="desktop-nav">' in html
        and '<ul class="mobile-nav">' in html
        and ".desktop-nav { display: block; }" in html
        and ".nav-panel { display: none; }" in html
    )


def test_generator_renders_chapters_sections_and_two_level_navigation(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    source = (
        "# User Guide\n\nIntroduction.\n\n"
        "## 第一章 入门 {#getting-started}\n\n"
        "### 安装 {#install}\n\nInstall details.\n\n"
        "### 快速开始 {#quick-start}\n\nRun details.\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### CLI 速查 {#cli-reference}\n\nReference details.\n"
    )
    for name in ("ff", "esim"):
        (user_docs / f"{name}-user-guide.md").write_text(
            source,
            encoding="utf-8",
        )

    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=True,
    )

    html = (user_docs / "esim-user-guide.html").read_text(encoding="utf-8")
    assert (
        '<article class="chapter" id="getting-started">' in html
        and '<section id="install">' in html
        and '<section id="quick-start">' in html
        and '<a class="nav-chapter-link" href="#getting-started">第一章 入门</a>'
        in html
        and '<a class="nav-section-link" href="#install">安装</a>' in html
        and html.index('id="getting-started"') < html.index('id="reference-chapter"')
    )


def test_generator_rejects_flat_guides_without_chapter_sections(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    (user_docs / "ff-user-guide.md").write_text(
        "# ff User Guide\n\n## Usage\n\nFlat content.\n\n"
        "## Reference\n\nMore flat content.\n",
        encoding="utf-8",
    )
    (user_docs / "esim-user-guide.md").write_text(
        "# esim User Guide\n\n## 第一章 入门 {#getting-started}\n\n"
        "### Quick Start {#quick-start}\n\nDetails.\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr.strip()) == (
        1,
        "",
        "invalid user guide structure: "
        f"{user_docs / 'ff-user-guide.md'}: chapter 'Usage' must contain "
        "at least one H3 section",
    )
    assert not (user_docs / "ff-user-guide.html").exists()
    assert not (user_docs / "esim-user-guide.html").exists()


def test_generator_rejects_guides_with_fewer_than_two_chapters(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    user_docs = tmp_path / "docs" / "user"
    user_docs.mkdir(parents=True)
    (user_docs / "ff-user-guide.md").write_text(
        "# ff User Guide\n\n## 第一章 入门 {#getting-started}\n\n"
        "### Quick Start {#quick-start}\n\nDetails.\n",
        encoding="utf-8",
    )
    (user_docs / "esim-user-guide.md").write_text(
        "# esim User Guide\n\n## 第一章 入门 {#getting-started}\n\n"
        "### Quick Start {#quick-start}\n\nDetails.\n\n"
        "## 第二章 参考 {#reference-chapter}\n\n"
        "### Reference {#reference}\n\nReference.\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "generate_user_guides.py"),
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr.strip()) == (
        1,
        "",
        "invalid user guide structure: "
        f"{user_docs / 'ff-user-guide.md'}: guide must contain at least two "
        "H2 chapters",
    )
