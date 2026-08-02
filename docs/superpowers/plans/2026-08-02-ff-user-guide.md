# ff README and User Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the detailed README with a concise entry point and add a detailed, self-contained Chinese HTML User Guide for ff CLI users.

**Architecture:** `README.md` is the minimal discovery and installation surface. `docs/ff-user-guide.html` is a hand-authored, task-oriented, standalone document whose behavior claims come only from `docs/ff-requirements.md`; a focused pytest module validates document boundaries, internal navigation, offline operation, and coverage anchors.

**Tech Stack:** Markdown, semantic HTML5, embedded CSS, Python 3.9 standard-library `html.parser`, pytest, local browser rendering.

## Global Constraints

- The User Guide is Chinese, one HTML file, and usable without network access.
- CSS is embedded; no external fonts, icons, stylesheets, scripts, images, or other resources.
- JavaScript is not used.
- Wide screens use sticky left navigation and main content; narrow screens use one column.
- Content describes only implemented ff behavior and treats `docs/ff-requirements.md` as authoritative.
- The guide targets ff CLI users and does not document esim TC YAML or expand the Python engine API.
- README contains only introduction, installation, basic usage, and links to detailed documentation.

---

### Task 1: Reduce README to the user entry point

**Files:**
- Modify: `README.md`
- Create: `tests/test_user_guide.py`

**Interfaces:**
- Consumes: the installation command and basic CLI syntax from `docs/ff-requirements.md`
- Produces: a README of at most 45 physical lines linking to `docs/ff-user-guide.html`

- [ ] **Step 1: Write the failing README boundary test**

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_readme_is_a_concise_entry_point() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) <= 45
    assert "## 安装" in readme
    assert "## 基础用法" in readme
    assert "## 详细文档" in readme
    assert "docs/ff-user-guide.html" in readme
    assert "## Python 引擎" not in readme
    assert "## 语法范围" not in readme
```

- [ ] **Step 2: Run the README test and confirm the current README fails**

Run: `.venv/bin/pytest -q tests/test_user_guide.py::test_readme_is_a_concise_entry_point`

Expected: FAIL because the current README has more than 45 lines and lacks the new User Guide link/section layout.

- [ ] **Step 3: Replace README with the minimal user-facing copy**

Use this exact information architecture:

```markdown
# ff

`ff` 是 Verilog/SystemVerilog filelist 展平工具。它处理条件分支、
嵌套 filelist、环境变量和路径，输出全部使用绝对路径的
flat filelist。

## 安装

```bash
python3 -m pip install --no-index --find-links ./wheelhouse esim==0.1.0
```

需要 Python 3.9+。wheelhouse 需包含 ff、`botticelle-onelog`、Rich 及其依赖。

## 基础用法

```bash
ff /aaa/bbb/testbench.f
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

不指定 `-o` 时，默认在当前目录生成 `flattened.f`。

## 详细文档

- [ff User Guide](docs/ff-user-guide.html)
- [ff 需求与行为契约](docs/ff-requirements.md)
```

- [ ] **Step 4: Run the focused test**

Run: `.venv/bin/pytest -q tests/test_user_guide.py::test_readme_is_a_concise_entry_point`

Expected: PASS.

- [ ] **Step 5: Commit the README slice**

```bash
git add README.md tests/test_user_guide.py
git commit -m "docs: simplify ff readme"
```

---

### Task 2: Establish the standalone HTML contract

**Files:**
- Create: `docs/ff-user-guide.html`
- Modify: `tests/test_user_guide.py`

**Interfaces:**
- Consumes: the global constraints and section map from the approved design
- Produces: semantic HTML with stable section IDs, internal navigation, embedded responsive/print CSS, and no resource dependencies

- [ ] **Step 1: Add a failing structural/offline test**

Append this parser and test to `tests/test_user_guide.py`:

```python
from html.parser import HTMLParser


class GuideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.sources: list[str] = []
        self.tags: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if "href" in values:
            self.hrefs.append(values["href"])
        if "src" in values:
            self.sources.append(values["src"])

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def parse_guide() -> tuple[str, GuideParser]:
    html = (PROJECT_ROOT / "docs" / "ff-user-guide.html").read_text(
        encoding="utf-8"
    )
    parser = GuideParser()
    parser.feed(html)
    return html, parser


def test_user_guide_is_standalone_and_has_valid_navigation() -> None:
    html, parser = parse_guide()
    required_ids = {
        "overview", "install", "quick-start", "cli", "conditions",
        "nested-filelists", "environment", "comments-paths",
        "output-safety", "logging-errors", "reference",
    }

    assert required_ids <= set(parser.ids)
    assert len(parser.ids) == len(set(parser.ids))
    assert {href[1:] for href in parser.hrefs if href.startswith("#")} <= set(
        parser.ids
    )
    assert not parser.sources
    assert "script" not in parser.tags
    assert "link" not in parser.tags
    assert not any(
        value.startswith(("http://", "https://", "//"))
        for value in parser.hrefs
    )
    assert '@media (max-width: 860px)' in html
    assert "@media print" in html
```

- [ ] **Step 2: Run the structural test and confirm it fails**

Run: `.venv/bin/pytest -q tests/test_user_guide.py::test_user_guide_is_standalone_and_has_valid_navigation`

Expected: FAIL with `FileNotFoundError` because `docs/ff-user-guide.html` does not exist.

- [ ] **Step 3: Create the semantic shell and embedded stylesheet**

Create a valid HTML5 document using this exact outer structure:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ff User Guide</title>
  <style>
    :root { color-scheme: light; --accent: #0f766e; --ink: #17202a; }
    * { box-sizing: border-box; }
    body {
      margin: 0; color: var(--ink); background: #f4f7f7; line-height: 1.7;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    }
    .layout { display: grid; grid-template-columns: 17rem minmax(0, 1fr); }
    nav { position: sticky; top: 0; height: 100vh; overflow: auto; }
    main { width: min(100%, 76rem); padding: 3rem clamp(1.25rem, 4vw, 4rem); }
    pre { overflow-x: auto; }
    a { color: var(--accent); text-underline-offset: .18em; }
    a:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    .card, .note, .warning, .example { border: 1px solid #cbd5d5; padding: 1rem; }
    .badge { display: inline-block; font-weight: 700; }
    .option-table { overflow-x: auto; }
    @media (max-width: 860px) {
      .layout { display: block; }
      nav { position: static; height: auto; }
    }
    @media print {
      nav { display: none; }
      .layout { display: block; }
      main { max-width: none; padding: 0; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <nav aria-label="章节导航">
      <a href="#overview">了解 ff</a>
      <a href="#install">安装</a>
      <a href="#quick-start">快速开始</a>
      <a href="#cli">CLI 参数</a>
      <a href="#conditions">条件指令</a>
      <a href="#nested-filelists">嵌套 filelist</a>
      <a href="#environment">环境变量</a>
      <a href="#comments-paths">注释与路径</a>
      <a href="#output-safety">输出安全</a>
      <a href="#logging-errors">日志与排错</a>
      <a href="#reference">速查</a>
    </nav>
    <main>
      <header><p class="badge">ff 0.1</p><h1>ff User Guide</h1></header>
      <section id="overview"><h2>了解 ff</h2><p>ff 把 filelist 展平为绝对路径文本。</p></section>
      <section id="install"><h2>安装</h2><p>从离线 wheelhouse 安装 ff 及其依赖。</p></section>
      <section id="quick-start"><h2>快速开始</h2><p>使用一个顶层 filelist 生成 flat filelist。</p></section>
      <section id="cli"><h2>CLI 参数</h2><p>了解输入、输出、宏和日志选项。</p></section>
      <section id="conditions"><h2>条件指令</h2><p>根据预定义宏选择活动分支。</p></section>
      <section id="nested-filelists"><h2>嵌套 filelist</h2><p>递归展开 -f 和 -F 引用。</p></section>
      <section id="environment"><h2>环境变量</h2><p>在路径条目中展开环境变量。</p></section>
      <section id="comments-paths"><h2>注释与路径</h2><p>了解可识别条目与透传选项。</p></section>
      <section id="output-safety"><h2>输出安全</h2><p>了解绝对路径、symlink 和原子替换。</p></section>
      <section id="logging-errors"><h2>日志与排错</h2><p>使用日志和 source chain 定位错误。</p></section>
      <section id="reference"><h2>速查</h2><p>集中查看选项、路径基准和退出码。</p></section>
    </main>
  </div>
</body>
</html>
```

Build on these exact IDs and class names in Task 3; do not rename them while expanding the prose and examples.

- [ ] **Step 4: Run the structural test**

Run: `.venv/bin/pytest -q tests/test_user_guide.py::test_user_guide_is_standalone_and_has_valid_navigation`

Expected: PASS.

- [ ] **Step 5: Commit the standalone shell**

```bash
git add docs/ff-user-guide.html tests/test_user_guide.py
git commit -m "docs: add standalone ff user guide shell"
```

---

### Task 3: Fill the guide with the complete user-facing behavior

**Files:**
- Modify: `docs/ff-user-guide.html`
- Modify: `tests/test_user_guide.py`

**Interfaces:**
- Consumes: sections 1 and 3 through 9 of `docs/ff-requirements.md`
- Produces: a task-oriented explanation of every CLI-visible rule, with input/command/output examples and a final quick-reference section

- [ ] **Step 1: Add a failing content-coverage test**

```python
def test_user_guide_covers_the_cli_contract_and_major_rule_groups() -> None:
    _, parser = parse_guide()
    text = " ".join(" ".join(parser.text).split())
    required_phrases = {
        "INPUT 必须是第一个参数",
        "./flattened.f",
        "MACRO_1 MACRO_2",
        "`ifdef",
        "`ifndef",
        "`elsif",
        "-f",
        "-F",
        "$NAME",
        "${NAME}",
        "+incdir+",
        "symlink target",
        "UTF-8",
        "原子替换",
        "source chain",
        "--debug",
        "ff.log",
        "退出码",
        "mixed-language",
        "logical library",
    }

    missing = sorted(phrase for phrase in required_phrases if phrase not in text)
    assert not missing, missing
    assert "TC YAML" not in text
    assert "FlattenRequest" not in text
```

- [ ] **Step 2: Run the coverage test and confirm the concise shell fails**

Run: `.venv/bin/pytest -q tests/test_user_guide.py::test_user_guide_covers_the_cli_contract_and_major_rule_groups`

Expected: FAIL and list the behavior phrases not yet present.

- [ ] **Step 3: Expand every section using the authoritative rules**

Use this content map without adding behavior beyond `docs/ff-requirements.md`:

```text
overview:
  purpose; flat text output; Verilog/SystemVerilog only; no mixed-language/logical library
install:
  Python 3.9+; offline wheelhouse command; ff/onelog/Rich dependency bundle
quick-start:
  top.f input; default flattened.f; explicit -o and -d example; absolute output result
cli:
  INPUT-first grammar; -o; repeatable multi-value -d; -l optional path; --debug; exit 0/1/2/3
conditions:
  ifdef/ifndef/elsif/else/endif; nesting; inactive branch semantics; malformed/unknown directives
nested-filelists:
  top-level filelist-relative default; -f CWD base; -F logical filelist base; cycles vs repeats
environment:
  $NAME and ${NAME}; recursive expansion; missing/empty/cycle errors; unsupported shell forms
comments-paths:
  // and block comments; one logical entry per line; source/-v/-y/+incdir+; passthrough options;
  whitespace/glob/continuation/Windows/UNC restrictions
output-safety:
  normalized absolute logical paths; symlink target annotation; existence/readability checks;
  UTF-8 BOM/CRLF input; UTF-8 LF output; atomic replace; permissions; output/log conflicts;
  output symlink node replacement; same-path concurrency rule
logging-errors:
  four -l/--debug combinations; overwrite and atomic log publish; source chain; suggestions;
  expected vs internal failures
reference:
  option table; path-base table; supported entries; unsupported syntax; exit-code table
```

For conditions, nested filelists, environment variables, and logging, include three-part `.example` blocks labeled `输入`, `命令`, and `结果`. Keep code examples POSIX-only and use `/proj/tb`, `/proj/rtl`, `MACRO_1`, and `MACRO_2` consistently.

- [ ] **Step 4: Run all document tests**

Run: `.venv/bin/pytest -q tests/test_user_guide.py`

Expected: all tests PASS.

- [ ] **Step 5: Commit the complete guide content**

```bash
git add docs/ff-user-guide.html tests/test_user_guide.py
git commit -m "docs: document ff behavior in user guide"
```

---

### Task 4: Render, audit, and finalize the documentation

**Files:**
- Modify if defects are found: `README.md`
- Modify if defects are found: `docs/ff-user-guide.html`
- Modify if validation gaps are found: `tests/test_user_guide.py`

**Interfaces:**
- Consumes: the completed README, guide, tests, and authoritative requirements
- Produces: visually verified desktop/mobile/print-ready documentation and a clean regression result

- [ ] **Step 1: Run the structural and content audit**

```bash
git diff --check
.venv/bin/pytest -q tests/test_user_guide.py
rg -n 'https?://|src=|<script|<link' docs/ff-user-guide.html
```

Expected: diff check and tests PASS; resource scan returns no matches.

- [ ] **Step 2: Render at desktop width**

Open `/mnt/c/Users/majin/Documents/EDA仿真脚本开发/docs/ff-user-guide.html` in Chrome, use a 1440 px-wide viewport, and capture a full-page screenshot. Verify navigation stays readable, content does not exceed its column, tables and code blocks do not overlap, and information labels are distinguishable without relying only on color.

- [ ] **Step 3: Render at narrow width**

Use a 390 px-wide viewport and capture a full-page screenshot. Verify the layout becomes one column, the navigation is no longer sticky/full-height, tables scroll inside their containers, and no page-level horizontal overflow appears.

- [ ] **Step 4: Check print layout**

Use Chrome print preview. Verify navigation is hidden, main content uses the full printable width, code examples remain legible, and headings do not become isolated at page bottoms.

- [ ] **Step 5: Run the complete project regression**

```bash
.venv/bin/python -m compileall -q src
.venv/bin/pytest -q
```

Expected: compileall exits 0 and all tests PASS, including the existing 119 tests and the new document tests.

- [ ] **Step 6: Commit any render-driven corrections**

If rendering required changes:

```bash
git add README.md docs/ff-user-guide.html tests/test_user_guide.py
git commit -m "docs: polish ff user guide rendering"
```

If no rendering changes were required, do not create an empty commit.
