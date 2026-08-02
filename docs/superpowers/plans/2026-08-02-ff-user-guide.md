# ff README and User Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the detailed README with a concise entry point and add a detailed, self-contained Chinese HTML User Guide for ff CLI users.

**Architecture:** `README.md` is the minimal discovery and installation surface. `docs/ff-user-guide.html` is a hand-authored, task-oriented, standalone document whose behavior claims come only from `docs/ff-requirements.md`. Because both artifacts are human-facing prose, validation checks HTML/link/resource behavior and rendered layout instead of adding brittle text-assertion tests.

**Tech Stack:** Markdown, semantic HTML5, embedded CSS, `xmllint`, Python 3.9 standard-library `html.parser` for a one-time link audit, and local Chrome rendering.

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

**Interfaces:**
- Consumes: installation and basic CLI syntax from `docs/ff-requirements.md`
- Produces: a short README linking to `docs/ff-user-guide.html`

- [ ] **Step 1: Replace README with the approved minimal content**

Keep exactly these sections and no developer/API detail:

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

- [ ] **Step 2: Check the README boundary**

Run: `wc -l README.md`

Expected: no more than 40 lines.

Inspect the rendered Markdown and confirm it has only the introduction, installation, two basic commands, the default output note, and two documentation links.

- [ ] **Step 3: Commit the README slice**

```bash
git add README.md
git commit -m "docs: simplify ff readme"
```

---

### Task 2: Create the complete standalone HTML guide

**Files:**
- Create: `docs/ff-user-guide.html`

**Interfaces:**
- Consumes: sections 1 and 3 through 9 of `docs/ff-requirements.md`
- Produces: a task-oriented, standalone HTML5 guide with stable internal section IDs

- [ ] **Step 1: Build the embedded visual system and document shell**

Use `<!doctype html>`, `<html lang="zh-CN">`, UTF-8 and viewport metadata. Embed all CSS in one `<style>` element. Define:

```css
:root { color-scheme: light; --accent: #0f766e; --ink: #17202a; }
.layout { display: grid; grid-template-columns: 17rem minmax(0, 1fr); }
.sidebar { position: sticky; top: 0; height: 100vh; overflow: auto; }
.content { width: min(100%, 76rem); padding: 3rem clamp(1.25rem, 4vw, 4rem); }
.table-wrap, pre { overflow-x: auto; }
@media (max-width: 860px) {
  .layout { display: block; }
  .sidebar { position: static; height: auto; }
}
@media print {
  .sidebar { display: none; }
  .layout { display: block; }
  .content { max-width: none; padding: 0; }
}
```

Add visible focus outlines, underlined links, system fonts, readable code blocks, responsive tables, and labeled `.note`, `.warning`, `.example`, and `.badge` components.

- [ ] **Step 2: Add navigation and task-oriented sections**

Use these stable IDs in the sidebar and matching `<section>` elements:

```text
overview
install
quick-start
cli
conditions
nested-filelists
environment
comments-paths
output-safety
logging-errors
reference
```

- [ ] **Step 3: Fill every section from the authoritative contract**

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

For conditions, nested filelists, environment variables, and logging, include examples labeled `输入`, `命令`, and `结果`. Keep examples POSIX-only and consistently use `/proj/tb`, `/proj/rtl`, `MACRO_1`, and `MACRO_2`.

- [ ] **Step 4: Validate HTML syntax and offline boundaries**

```bash
xmllint --html --noout docs/ff-user-guide.html
rg -n 'https?://|src=|<script|<link' docs/ff-user-guide.html
```

Expected: `xmllint` exits 0; resource scan returns no matches.

Run a one-time standard-library `HTMLParser` audit that collects all IDs and fragment links. Confirm IDs are unique, every `href` beginning with `#` resolves to an ID, and all required IDs from Step 2 are present.

- [ ] **Step 5: Commit the guide**

```bash
git add docs/ff-user-guide.html
git commit -m "docs: add detailed ff user guide"
```

---

### Task 3: Render, audit, and finalize the documentation

**Files:**
- Modify if the audits find defects: `README.md`
- Modify if the audits find defects: `docs/ff-user-guide.html`

**Interfaces:**
- Consumes: the completed README, guide, and authoritative requirements
- Produces: visually verified desktop/mobile/print-ready documentation and a clean project regression

- [ ] **Step 1: Audit requirement coverage**

Compare the guide section-by-section with `docs/ff-requirements.md`. Explicitly account for CLI, conditions, comments, recognized paths, nested paths, environment expansion, path normalization/symlinks, output safety, logging, errors, and limitations. Correct any unsupported claim or missing user-visible rule.

- [ ] **Step 2: Render at desktop width**

Open `/mnt/c/Users/majin/Documents/EDA仿真脚本开发/.worktrees/ff-user-guide/docs/ff-user-guide.html` in Chrome at a 1440 px-wide viewport. Capture a full-page screenshot and verify sidebar behavior, readable line lengths, table/code containment, focus visibility, and labeled information blocks.

- [ ] **Step 3: Render at narrow width**

Render at 390 px width. Capture a full-page screenshot and verify one-column layout, non-sticky navigation, horizontally scrollable tables/code blocks, and no page-level horizontal overflow.

- [ ] **Step 4: Check print CSS**

Use Chrome print preview. Confirm the sidebar is hidden, main content uses printable width, code remains legible, and headings avoid isolated page bottoms.

- [ ] **Step 5: Run final verification**

```bash
git diff --check
xmllint --html --noout docs/ff-user-guide.html
/mnt/c/Users/majin/Documents/EDA仿真脚本开发/.venv/bin/python -m compileall -q src
/mnt/c/Users/majin/Documents/EDA仿真脚本开发/.venv/bin/pytest -q
```

Expected: all commands exit 0; the existing 119 tests still pass.

- [ ] **Step 6: Commit corrections if required**

If audits or rendering required changes:

```bash
git add README.md docs/ff-user-guide.html
git commit -m "docs: polish ff user guide"
```

If no correction is needed, do not create an empty commit.
