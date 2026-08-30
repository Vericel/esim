import argparse
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator
from pygments.util import ClassNotFound

_GUIDE_NAMES = ("ff", "esim")
_EXPLICIT_ID = re.compile(r"\s+\{#([a-z0-9]+(?:-[a-z0-9]+)*)\}\s*$")
_NON_SLUG = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES = re.compile(r"[\s_]+")
_SYNTAX_CLASSES = (
    (Comment, "syntax-comment"),
    (Name.Tag, "syntax-key"),
    (Name.Builtin, "syntax-command"),
    (Keyword, "syntax-command"),
    (Name.Variable, "syntax-variable"),
    (Number, "syntax-number"),
    (Literal, "syntax-string"),
    (Operator, "syntax-operator"),
)


class GuideStructureError(ValueError):
    """Raised when a canonical guide does not declare chapter sections."""


@dataclass(frozen=True)
class Section:
    identifier: str
    title: str
    tokens: list[Token]


@dataclass(frozen=True)
class Chapter:
    identifier: str
    title: str
    heading_tokens: list[Token]
    introduction_tokens: list[Token]
    sections: list[Section]


def _slugify(title: str) -> str:
    normalized = _NON_SLUG.sub("", title.strip().lower())
    slug = _SPACES.sub("-", normalized).strip("-")
    return slug or "section"


def _heading_text(token: Token) -> str:
    return token.content.strip()


def _strip_explicit_id(token: Token) -> tuple[str, str]:
    title = _heading_text(token)
    match = _EXPLICIT_ID.search(title)
    if match is None:
        return title, _slugify(title)
    visible_title = title[: match.start()].rstrip()
    token.content = visible_title
    for child in token.children or []:
        if child.type == "text" and _EXPLICIT_ID.search(child.content):
            child.content = _EXPLICIT_ID.sub("", child.content).rstrip()
    return visible_title, match.group(1)


def _split_chapter(tokens: list[Token]) -> Chapter:
    inline = tokens[1]
    title, identifier = _strip_explicit_id(inline)
    introduction: list[Token] = []
    sections: list[Section] = []
    index = 3
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open" and token.tag == "h3":
            section_inline = tokens[index + 1]
            section_title, section_identifier = _strip_explicit_id(section_inline)
            end = index + 3
            while end < len(tokens):
                candidate = tokens[end]
                if candidate.type == "heading_open" and candidate.tag == "h3":
                    break
                end += 1
            sections.append(
                Section(
                    section_identifier,
                    section_title,
                    tokens[index:end],
                )
            )
            index = end
            continue
        introduction.append(token)
        index += 1
    return Chapter(identifier, title, tokens[:3], introduction, sections)


def _split_document(tokens: list[Token]) -> tuple[str, list[Token], list[Chapter]]:
    title = "User Guide"
    introduction: list[Token] = []
    chapters: list[Chapter] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open" and token.tag == "h1":
            if index + 1 < len(tokens):
                title = _heading_text(tokens[index + 1])
            index += 3
            continue
        if token.type == "heading_open" and token.tag == "h2":
            end = index + 3
            while end < len(tokens):
                candidate = tokens[end]
                if candidate.type == "heading_open" and candidate.tag == "h2":
                    break
                end += 1
            chapters.append(_split_chapter(tokens[index:end]))
            index = end
            continue
        introduction.append(token)
        index += 1
    return title, introduction, chapters


def _highlight_source(source: str, language: str) -> str:
    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        return escape(source)
    fragments = []
    for token_type, value in lex(source, lexer):
        escaped = escape(value)
        syntax_class = next(
            (
                class_name
                for family, class_name in _SYNTAX_CLASSES
                if token_type in family
            ),
            None,
        )
        if syntax_class is None:
            fragments.append(escaped)
        else:
            fragments.append(f'<span class="{syntax_class}">{escaped}</span>')
    return "".join(fragments)


def _render_fence(
    _renderer: RendererHTML,
    tokens: list[Token],
    index: int,
    _options: dict[str, object],
    _environment: dict[str, object],
) -> str:
    token = tokens[index]
    language = token.info.strip().split(maxsplit=1)[0].lower() or "text"
    highlighted = _highlight_source(token.content, language)
    language_label = {"bash": "Bash", "text": "Text", "yaml": "YAML"}.get(
        language,
        language.upper(),
    )
    return (
        f'<div class="highlight language-{escape(language, quote=True)}">\n'
        '<div class="code-toolbar">'
        f'<span class="code-language">{escape(language_label)}</span>'
        "</div>\n"
        f"<pre><code>{highlighted}</code></pre>\n"
        "</div>\n"
    )


def _render_markdown(
    source: str,
) -> tuple[
    str,
    str,
    str,
    list[tuple[str, str, list[tuple[str, str]]]],
]:
    markdown = MarkdownIt("commonmark", {"html": False}).enable("table")
    markdown.add_render_rule("fence", _render_fence)
    title, introduction, chapters = _split_document(markdown.parse(source))
    if len(chapters) < 2:
        raise GuideStructureError("guide must contain at least two H2 chapters")
    for chapter in chapters:
        if not chapter.sections:
            raise GuideStructureError(
                f"chapter '{chapter.title}' must contain at least one H3 section"
            )
    renderer = markdown.renderer
    options = markdown.options
    intro_html = renderer.render(introduction, options, {})
    chapter_fragments = []
    for chapter in chapters:
        if chapter.sections:
            sections_html = "\n".join(
                f'<section id="{section.identifier}">\n'
                f"{renderer.render(section.tokens, options, {})}"
                "</section>"
                for section in chapter.sections
            )
            chapter_fragments.append(
                f'<article class="chapter" id="{chapter.identifier}">\n'
                '<header class="chapter-header">\n'
                f"{renderer.render(chapter.heading_tokens, options, {})}"
                f"{renderer.render(chapter.introduction_tokens, options, {})}"
                "</header>\n"
                f'<div class="chapter-sections">\n{sections_html}\n</div>\n'
                "</article>"
            )
        else:
            chapter_fragments.append(
                f'<section id="{chapter.identifier}">\n'
                f"{renderer.render(chapter.heading_tokens, options, {})}"
                f"{renderer.render(chapter.introduction_tokens, options, {})}"
                "</section>"
            )
    navigation = [
        (
            chapter.identifier,
            chapter.title,
            [(section.identifier, section.title) for section in chapter.sections],
        )
        for chapter in chapters
    ]
    return title, intro_html, "\n".join(chapter_fragments), navigation


def _render_navigation(
    navigation: list[tuple[str, str, list[tuple[str, str]]]],
) -> str:
    fragments = []
    for chapter_id, chapter_title, sections in navigation:
        section_links = "\n".join(
            "            <li>"
            f'<a class="nav-section-link" href="#{section_id}">{section_title}</a>'
            "</li>"
            for section_id, section_title in sections
        )
        nested = (
            f'\n          <ul class="nav-sections">\n{section_links}\n          </ul>'
            if sections
            else ""
        )
        fragments.append(
            '        <li class="nav-chapter">'
            f'<a class="nav-chapter-link" href="#{chapter_id}">{chapter_title}</a>'
            f"{nested}</li>"
        )
    return "\n".join(fragments)


def _render_guide(name: str, source: str) -> str:
    title, introduction, body, navigation = _render_markdown(source)
    nav_html = _render_navigation(navigation)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{name} 中文用户指南" />
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --accent: #2563eb;
      --accent-deep: #1d4ed8;
      --accent-alt: #7c3aed;
      --accent-warm: #f59e0b;
      --ink: #172033;
      --muted: #5d6b82;
      --line: #d9e2f0;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --page: #eef2f7;
      --sidebar: #111827;
      --code: #0b1020;
      --code-ink: #dbeafe;
      --shadow: 0 16px 45px rgba(30, 41, 59, 0.1);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; scroll-padding-top: 1rem; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 95% 0%, rgba(124, 58, 237, 0.11),
          transparent 30rem),
        radial-gradient(circle at 55% 0%, rgba(37, 99, 235, 0.08),
          transparent 34rem),
        var(--page);
      font: 16px/1.72 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
        "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
      overflow-wrap: anywhere;
    }}
    a {{ color: var(--accent-deep); text-underline-offset: 0.18em; }}
    a:focus-visible, button:focus-visible, summary:focus-visible {{
      outline: 3px solid #60a5fa;
      outline-offset: 3px;
      border-radius: 0.2rem;
    }}
    code, pre {{ font-family: "SFMono-Regular", Consolas, monospace; }}
    :not(pre) > code {{
      padding: 0.1em 0.32em;
      border-radius: 0.28rem;
      color: #1e3a8a;
      background: #e8eefc;
      font-size: 0.92em;
    }}
    pre {{
      position: relative;
      margin: 1rem 0;
      padding: 1rem 1.1rem;
      overflow-x: auto;
      color: var(--code-ink);
      background: var(--code);
      border-radius: 0;
      line-height: 1.55;
    }}
    pre code {{ color: inherit; background: transparent; }}
    .highlight {{
      margin: 1rem 0;
      overflow: hidden;
      background: var(--code);
      border: 1px solid #26344f;
      border-radius: 0.72rem;
      box-shadow: 0 12px 28px rgba(2, 6, 23, 0.18);
    }}
    .highlight pre {{ margin: 0; }}
    .code-toolbar {{
      display: flex;
      min-height: 2.35rem;
      align-items: center;
      padding: 0.38rem 0.7rem 0.38rem 1rem;
      color: #9fb0cc;
      background: #121a2c;
      border-bottom: 1px solid #26344f;
    }}
    .code-language {{
      font-size: 0.7rem;
      font-weight: 750;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .syntax-comment {{ color: #7d9b96; font-style: italic; }}
    .syntax-key {{ color: #7dd3fc; }}
    .syntax-command {{ color: #c4b5fd; font-weight: 650; }}
    .syntax-variable {{ color: #fbbf24; }}
    .syntax-number {{ color: #fb7185; }}
    .syntax-string {{ color: #86efac; }}
    .syntax-operator {{ color: #fda4af; }}
    .layout {{
      display: grid;
      grid-template-columns: 18rem minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 2rem 1.4rem;
      overflow-y: auto;
      color: #dbe5f5;
      background:
        linear-gradient(180deg, var(--sidebar), #172554 58%, #1e1b4b);
    }}
    .brand {{
      display: flex;
      gap: 0.7rem;
      align-items: center;
      color: white;
      text-decoration: none;
    }}
    .brand-mark {{
      display: grid;
      width: 2.6rem;
      height: 2.6rem;
      place-items: center;
      color: #111827;
      background: linear-gradient(135deg, #38bdf8, #a78bfa 70%);
      border-radius: 0.65rem;
      font-weight: 800;
    }}
    .sidebar ul {{ margin: 1.5rem 0 0; padding: 0; list-style: none; }}
    .desktop-nav {{ display: block; }}
    .nav-panel {{ display: none; }}
    .sidebar li + li {{ margin-top: 0.18rem; }}
    .sidebar .nav-chapter + .nav-chapter {{ margin-top: 0.8rem; }}
    .sidebar li a {{
      display: block;
      padding: 0.43rem 0.62rem;
      color: #c5d2e7;
      border-radius: 0.4rem;
      text-decoration: none;
      font-size: 0.88rem;
      transition: color 150ms ease, background 150ms ease;
    }}
    .sidebar .nav-chapter-link {{
      color: #eef4ff;
      font-size: 0.84rem;
      font-weight: 760;
    }}
    .sidebar .nav-sections {{
      margin: 0.18rem 0 0.35rem 0.72rem;
      padding-left: 0.52rem;
      border-left: 1px solid rgba(147, 197, 253, 0.22);
    }}
    .sidebar .nav-section-link {{
      padding-top: 0.3rem;
      padding-bottom: 0.3rem;
      color: #adbbd1;
      font-size: 0.78rem;
    }}
    .sidebar li a:hover, .sidebar li a[aria-current="true"] {{
      color: white;
      background: rgba(59, 130, 246, 0.24);
    }}
    .content {{
      width: min(100%, 78rem);
      padding: 3rem clamp(1.25rem, 4vw, 4.5rem) 5rem;
    }}
    .hero {{
      margin-bottom: 2rem;
      padding: clamp(1.5rem, 4vw, 3rem);
      color: white;
      background:
        linear-gradient(120deg, #172554, #2563eb 55%, #7c3aed);
      border-radius: 1rem;
      box-shadow: var(--shadow);
    }}
    .hero .badge {{
      color: #bfdbfe;
      font-size: 0.76rem;
      font-weight: 750;
      letter-spacing: 0.12em;
    }}
    .hero h1 {{
      margin: 0.5rem 0 0;
      font-size: clamp(2.1rem, 6vw, 4.2rem);
      line-height: 1.06;
    }}
    .introduction {{ margin: 0 0 2rem; font-size: 1.08rem; color: var(--muted); }}
    .chapter {{ margin-top: 3.6rem; scroll-margin-top: 1rem; }}
    .chapter:first-of-type {{ margin-top: 2.4rem; }}
    .chapter-header {{
      margin-bottom: 1.25rem;
      padding: 0 0.25rem;
    }}
    .chapter-header h2 {{ margin-bottom: 0; }}
    .chapter-header p {{ max-width: 68rem; color: var(--muted); }}
    .chapter-sections {{ display: grid; gap: 1.35rem; }}
    section {{
      margin-top: 0;
      padding: clamp(1.25rem, 3vw, 2.2rem);
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 0.8rem;
      box-shadow: var(--shadow);
    }}
    h2 {{
      margin-top: 0;
      color: var(--accent-deep);
      font-size: clamp(1.45rem, 3vw, 2rem);
    }}
    h2::after {{
      display: block;
      width: 3.2rem;
      height: 0.22rem;
      margin-top: 0.55rem;
      background: linear-gradient(90deg, var(--accent), var(--accent-warm));
      border-radius: 99rem;
      content: "";
    }}
    h3 {{ margin-top: 1.8rem; }}
    .chapter section > h3:first-child {{
      margin-top: 0;
      color: var(--ink);
      font-size: clamp(1.28rem, 2.4vw, 1.7rem);
    }}
    h4 {{ margin: 1.7rem 0 0.65rem; color: var(--accent-deep); }}
    blockquote {{
      margin: 1.2rem 0;
      padding: 0.7rem 1rem;
      background: #eff6ff;
      border-left: 0.3rem solid #2563eb;
    }}
    table {{
      display: block;
      width: 100%;
      overflow-x: auto;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 0.65rem 0.8rem;
      border: 1px solid var(--line);
      text-align: left;
    }}
    th {{ background: #eef3fb; }}
    .copy-button {{
      margin-left: auto;
      padding: 0.3rem 0.55rem;
      color: #dbeafe;
      background: #23304a;
      border: 1px solid #405271;
      border-radius: 0.35rem;
      cursor: pointer;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --accent-deep: #93c5fd;
        --ink: #e6edf7;
        --muted: #aab6cc;
        --line: #2b3853;
        --surface: #111827;
        --surface-soft: #151f32;
        --page: #080d18;
      }}
      :not(pre) > code {{ color: #bfdbfe; background: #1e293b; }}
      th {{ background: #182338; }}
      blockquote {{ background: #111f39; }}
    }}
    @media (max-width: 860px) {{
      .layout {{ display: block; }}
      .sidebar {{ position: static; height: auto; padding: 1.2rem; }}
      .desktop-nav {{ display: none; }}
      .nav-panel {{ display: block; }}
      .nav-panel > summary {{
        display: block;
        margin-top: 1rem;
        padding: 0.55rem 0.7rem;
        color: white;
        background: rgba(59, 130, 246, 0.3);
        border-radius: 0.4rem;
        cursor: pointer;
        font-weight: 650;
      }}
      .nav-panel:not([open]) > ul {{ display: none; }}
      .nav-panel[open] > ul {{ display: block; columns: 2; }}
      .content {{ padding-top: 1.5rem; }}
    }}
    @media (max-width: 520px) {{ .sidebar ul {{ columns: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      * {{ transition: none !important; }}
    }}
    @media print {{
      :root {{ color-scheme: light; }}
      body {{ color: #000; background: #fff; }}
      .sidebar, .copy-button {{ display: none; }}
      .layout {{ display: block; }}
      .content {{ width: 100%; padding: 0; }}
      .hero, section {{
        color: #000;
        background: #fff;
        box-shadow: none;
        break-inside: avoid;
      }}
      a[href]:not([href^="#"])::after {{ content: " (" attr(href) ")"; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <nav class="sidebar" aria-label="章节导航">
      <a class="brand" href="#top">
        <span class="brand-mark">{name}</span><strong>User Guide</strong>
      </a>
      <ul class="desktop-nav">
{nav_html}
      </ul>
      <details class="nav-panel">
        <summary>章节导航</summary>
        <ul class="mobile-nav">
{nav_html}
        </ul>
      </details>
    </nav>
    <main class="content" id="top">
      <header class="hero">
        <span class="badge">{name.upper()} · 中文用户指南</span>
        <h1>{title}</h1>
      </header>
      <div class="introduction">{introduction}</div>
{body}
    </main>
  </div>
  <script>
    document.querySelectorAll(".highlight").forEach((container) => {{
      const block = container.querySelector("pre");
      const toolbar = container.querySelector(".code-toolbar");
      if (!block || !toolbar) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy-button";
      button.textContent = "复制";
      button.addEventListener("click", async () => {{
        const text = block.querySelector("code")?.textContent || block.textContent;
        try {{
          await navigator.clipboard.writeText(text);
          button.textContent = "已复制";
        }}
        catch {{ button.hidden = true; }}
        window.setTimeout(() => {{ button.textContent = "复制"; }}, 1400);
      }});
      toolbar.append(button);
    }});
    if ("IntersectionObserver" in window) {{
      const links = new Map();
      document.querySelectorAll('.sidebar a[href^="#"]').forEach((link) => {{
        const id = link.getAttribute("href").slice(1);
        links.set(id, [...(links.get(id) || []), link]);
      }});
      const observer = new IntersectionObserver((entries) => {{
        entries.filter((entry) => entry.isIntersecting).forEach((entry) => {{
          links.forEach((group) => group.forEach(
            (link) => link.removeAttribute("aria-current"),
          ));
          const activeIds = [
            entry.target.closest(".chapter")?.id,
            entry.target.id,
          ];
          activeIds.forEach((id) => links.get(id)?.forEach(
            (link) => link.setAttribute("aria-current", "true"),
          ));
        }});
      }}, {{ rootMargin: "0px 0px -70%" }});
      document.querySelectorAll("main section[id]").forEach(
        (section) => observer.observe(section),
      );
    }}
  </script>
</body>
</html>
'''


def _generated_guides(root: Path) -> dict[Path, str]:
    user_docs = root / "docs" / "user"
    generated = {}
    for name in _GUIDE_NAMES:
        source = user_docs / f"{name}-user-guide.md"
        output = user_docs / f"{name}-user-guide.html"
        try:
            generated[output] = _render_guide(
                name,
                source.read_text(encoding="utf-8"),
            )
        except GuideStructureError as error:
            raise GuideStructureError(f"{source}: {error}") from error
    return generated


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate standalone user guides")
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        generated = _generated_guides(args.root.resolve())
    except GuideStructureError as error:
        print(f"invalid user guide structure: {error}", file=sys.stderr)
        return 1
    stale = []
    for output, content in generated.items():
        if args.check:
            if not output.exists() or output.read_text(encoding="utf-8") != content:
                stale.append(output)
        else:
            output.write_text(content, encoding="utf-8", newline="\n")
    for output in stale:
        print(f"stale generated user guide: {output}", file=sys.stderr)
    if stale:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
