from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONTENT = DOCS / "content"
ASSETS = DOCS / "assets"
VERSION_CONTENT = CONTENT / "versions"
SRC = ROOT / "src" / "torchlet"

DEFAULT_COMPARE_FILES = {
    "v00_full_recompute": "layer/gqa.py",
    "v01_0_ragged_batch": "layer/gqa.py",
    "v01_1_split_gqa": "layer/gqa.py",
    "v02_kv_cache": "layer/gqa.py",
    "v03_request_states": "scheduler.py",
    "v04_continuous_batching": "scheduler.py",
    "v05_decode_slots": "scheduler.py",
    "v06_static_buffers": "scheduler.py",
    "v07_cuda_graph": "engine.py",
    "v08_paged_gqa_py": "kvcache.py",
    "v09_triton_basics": "layer/gqa.py",
    "v10_triton_paged_gqa": "layer/gqa.py",
    "v11_cuda_graph_triton_paged": "engine.py",
}


def slug_to_title(slug: str) -> str:
    return slug.replace("_", " ")


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(match.group(2), quote=True)}">'
            f"{match.group(1)}</a>"
        ),
        escaped,
    )
    return escaped


def render_markdown(markdown: str) -> str:
    html_parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html_parts.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            html_parts.append("<ul>")
            html_parts.extend(f"<li>{item}</li>" for item in list_items)
            html_parts.append("</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                html_parts.append(
                    "<pre><code>"
                    + html.escape("\n".join(code_lines))
                    + "</code></pre>"
                )
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        if not line:
            flush_paragraph()
            flush_list()
            continue

        if line.startswith("#"):
            flush_paragraph()
            flush_list()
            level = min(len(line) - len(line.lstrip("#")), 4)
            title = line[level:].strip()
            html_parts.append(f"<h{level}>{render_inline(title)}</h{level}>")
            continue

        if line.startswith("- "):
            flush_paragraph()
            list_items.append(render_inline(line[2:].strip()))
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_list()
    return "\n".join(html_parts)


def read_versions() -> list[dict[str, str]]:
    with (CONTENT / "versions.json").open() as file:
        return json.load(file)


def read_version_rationale(version_id: str) -> str:
    markdown = (VERSION_CONTENT / f"{version_id}.md").read_text()
    match = re.search(
        r"^## Why Introduce It\s*$\n(.*?)(?=^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ""
    paragraphs = [part.strip() for part in match.group(1).split("\n\n") if part.strip()]
    if not paragraphs:
        return ""
    rationale = " ".join(paragraphs[0].splitlines())
    rationale = re.sub(r"`([^`]+)`", r"\1", rationale)
    rationale = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", rationale)
    return rationale


def build_asset_version(code_payload: dict[str, object]) -> str:
    digest = hashlib.sha256()
    digest.update((ASSETS / "site.css").read_bytes())
    digest.update((ASSETS / "compare-core.js").read_bytes())
    digest.update((ASSETS / "compare.js").read_bytes())
    digest.update(json.dumps(code_payload, sort_keys=True).encode())
    return digest.hexdigest()[:12]


def versioned(path: str, asset_version: str) -> str:
    return f"{path}?v={asset_version}" if asset_version else path


def compare_href(prefix: str, base: str, target: str, file_path: str) -> str:
    return (
        f"{prefix}/compare/?base={quote(base)}&target={quote(target)}"
        f"&file={quote(file_path, safe='')}"
    )


def action_link(href: str, label: str, class_name: str = "action-link") -> str:
    return (
        f'<a class="{class_name}" href="{html.escape(href, quote=True)}">'
        f"{html.escape(label)}</a>"
    )


def version_actions(
    version: dict[str, str],
    versions: list[dict[str, str]],
) -> str:
    links = []
    prefix = "../.."
    implemented = [item for item in versions if item["status"] == "implemented"]

    if version["status"] == "implemented" and version in implemented:
        implemented_index = implemented.index(version)
        if implemented_index > 0:
            base = implemented[implemented_index - 1]
            target = version
        elif len(implemented) > 1:
            base = version
            target = implemented[1]
        else:
            base = None
            target = None
        if base and target:
            file_path = DEFAULT_COMPARE_FILES.get(target["id"], "layer/gqa.py")
            links.append(
                action_link(
                    compare_href(prefix, base["id"], target["id"], file_path),
                    f"Compare {base['id']} -> {target['id']}",
                )
            )
    elif len(implemented) >= 2:
        base = implemented[-2]
        target = implemented[-1]
        file_path = DEFAULT_COMPARE_FILES.get(target["id"], "layer/gqa.py")
        links.append(
            action_link(
                compare_href(prefix, base["id"], target["id"], file_path),
                "Compare latest implemented Versions",
            )
        )

    links.append(
        action_link(f"{prefix}/compare/", "Open compare tool", "secondary-link")
    )
    return '<div class="doc-actions">' + "".join(links) + "</div>"


def page_shell(
    *,
    title: str,
    body: str,
    versions: list[dict[str, str]],
    current: str | None = None,
    extra_class: str = "",
    extra_head: str = "",
    extra_body: str = "",
    asset_version: str = "",
    table_of_contents: str = "",
) -> str:
    nav_items = []
    for version in versions:
        href = f"versions/{version['id']}/"
        if current and current != "index":
            href = f"../{version['id']}/"
        if current == "compare":
            href = f"../versions/{version['id']}/"
        aria = ' aria-current="page"' if current == version["id"] else ""
        version_label = f'{version["id"]} · {version["title"]}'
        nav_items.append(
            f'<a class="version-link" href="{href}" '
            f'title="{html.escape(version_label, quote=True)}"{aria}>'
            f'<span class="version-link-id">{version["id"]}</span>'
            f'<span class="version-link-title">{html.escape(version["title"])}</span>'
            f'<span class="status {version["status"]}">{version["status"]}</span>'
            "</a>"
        )

    root_prefix = "../.." if current and current not in {"index", "compare"} else ".."
    if current == "index":
        root_prefix = "."

    version_navigation = f"""
    <aside class="version-sidebar">
      <p class="sidebar-title">Versions</p>
      <nav class="version-nav" aria-label="Version navigation">
        {''.join(nav_items)}
      </nav>
    </aside>"""

    if current == "index":
        page_class = "page-home"
        page_layout = f"""
  <div class="readme-layout">
    <main class="content">
      <article class="doc home-doc">{body}</article>
    </main>
  </div>"""
    elif current == "compare":
        page_class = "page-compare"
        page_layout = f"""
  <div class="compare-layout">
    <aside class="file-sidebar">
      <div class="file-sidebar-header">
        <div>
          <p class="sidebar-title">Files</p>
          <span id="fileSummary" class="file-summary"></span>
        </div>
        <div class="file-filter" aria-label="File filter">
          <button id="changedFilesOnly" type="button" aria-pressed="true">Changed</button>
          <button id="allFiles" type="button" aria-pressed="false">All</button>
        </div>
      </div>
      <nav id="fileNav" aria-label="File navigation"></nav>
    </aside>
    <main class="compare-main">
      <article class="doc {extra_class}">{body}</article>
    </main>
  </div>"""
    else:
        page_class = "page-version"
        page_layout = f"""
  <div class="docs-layout">
    {version_navigation}
    <main class="content">
      <article class="doc {extra_class}">{body}</article>
    </main>
    <aside class="toc-sidebar">
      <p class="sidebar-title">On this page</p>
      <nav class="toc-nav" aria-label="On this page">{table_of_contents}</nav>
    </aside>
  </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - Torchlet Docs</title>
  <link rel="stylesheet"
        href="{versioned(f'{root_prefix}/assets/site.css', asset_version)}">
  {extra_head}
</head>
<body class="{page_class}">
  <header class="site-header">
    <a class="brand" href="{root_prefix}/">
      <span class="brand-mark">Torchlet</span>
      <span class="brand-subtitle">LLM inference implementation notes</span>
    </a>
    <nav class="top-nav" aria-label="Top navigation">
      <a href="{root_prefix}/">Overview</a>
      <a href="{root_prefix}/compare/">Compare code</a>
    </nav>
  </header>
  {page_layout}
  {extra_body}
</body>
</html>
"""


def add_heading_anchors(body: str) -> tuple[str, str]:
    headings: list[tuple[str, str]] = []
    used_ids: dict[str, int] = {}

    def replace_heading(match: re.Match[str]) -> str:
        rendered_title = match.group(1)
        plain_title = html.unescape(re.sub(r"<[^>]+>", "", rendered_title))
        base_id = re.sub(r"[^a-z0-9]+", "-", plain_title.lower()).strip("-")
        base_id = base_id or "section"
        occurrence = used_ids.get(base_id, 0)
        used_ids[base_id] = occurrence + 1
        heading_id = base_id if occurrence == 0 else f"{base_id}-{occurrence + 1}"
        headings.append((heading_id, plain_title))
        return f'<h2 id="{heading_id}">{rendered_title}</h2>'

    anchored = re.sub(r"<h2>(.*?)</h2>", replace_heading, body)
    links = "".join(
        f'<a href="#{heading_id}">{html.escape(title)}</a>'
        for heading_id, title in headings
    )
    return anchored, links


def build_index(
    out_dir: Path, versions: list[dict[str, str]], asset_version: str
) -> None:
    content = render_markdown((CONTENT / "index.md").read_text())
    cards = []
    for version in versions:
        cards.append(
            f'<a class="version-card" href="versions/{version["id"]}/">'
            f'<span class="badge {version["status"]}">{version["status"]}</span>'
            f"<h3>{version['id']}</h3>"
            f"<p>{html.escape(version['theme'])}</p>"
            "</a>"
        )
    intro_actions = (
        '<div class="doc-actions">'
        + action_link("versions/v00_full_recompute/", "Open version notes")
        + action_link("compare/", "Open code compare", "secondary-link")
        + "</div>"
    )
    first_paragraph_end = content.find("</p>") + len("</p>")
    intro = content[:first_paragraph_end]
    details = content[first_paragraph_end:]
    body = (
        intro
        + intro_actions
        + '<section class="version-route"><h2>Implementation Versions</h2>'
        + '<p class="lede">Each Version keeps the preceding implementation visible, '
        + "so design pressures and structural changes can be examined directly.</p>"
        + '<section class="version-grid">'
        + "".join(cards)
        + "</section>"
        + "</section>"
        + details
    )
    (out_dir / "index.html").write_text(
        page_shell(
            title="Guide",
            body=body,
            versions=versions,
            current="index",
            asset_version=asset_version,
        )
    )


def build_version_pages(
    out_dir: Path, versions: list[dict[str, str]], asset_version: str
) -> None:
    for version in versions:
        source = VERSION_CONTENT / f"{version['id']}.md"
        body = render_markdown(source.read_text())
        body, table_of_contents = add_heading_anchors(body)
        actions = version_actions(version, versions)
        body = body.replace("</h1>", f"</h1>{actions}", 1)
        body = (
            f'<span class="badge {version["status"]}">{version["status"]}</span>'
            + body
        )
        version_dir = out_dir / "versions" / version["id"]
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "index.html").write_text(
            page_shell(
                title=f"{version['id']} {version['title']}",
                body=body,
                versions=versions,
                current=version["id"],
                asset_version=asset_version,
                table_of_contents=table_of_contents,
            )
        )


def collect_code(version_metadata: list[dict[str, str]]) -> dict[str, object]:
    implemented_versions: list[dict[str, str]] = []
    all_files: set[str] = set()
    code: dict[str, dict[str, str]] = {}

    for version in version_metadata:
        version_dir = SRC / version["id"]
        if version["status"] != "implemented" or not version_dir.is_dir():
            continue
        implemented_versions.append(
            {
                **version,
                "rationale": read_version_rationale(version["id"]),
                "important_file": DEFAULT_COMPARE_FILES.get(
                    version["id"], "layer/gqa.py"
                ),
            }
        )
        code[version["id"]] = {}
        for path in sorted(version_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(version_dir).as_posix()
            all_files.add(rel)
            code[version["id"]][rel] = path.read_text()

    return {
        "versions": implemented_versions,
        "files": sorted(all_files),
        "code": code,
    }


def build_compare(
    out_dir: Path, versions: list[dict[str, str]], asset_version: str
) -> None:
    compare_dir = out_dir / "compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    body = """
<header class="compare-heading">
  <div>
    <p class="eyebrow">Version comparison</p>
    <h1>Compare implementation changes</h1>
    <p class="lede">Inspect the directed code changes from a Base Version to a later Target Version.</p>
  </div>
  <div class="pair-navigation" aria-label="Adjacent comparisons">
    <button id="previousPair" type="button">Previous pair</button>
    <button id="nextPair" type="button">Next pair</button>
  </div>
</header>
<section class="compare-toolbar" aria-label="Comparison controls">
  <label>Base Version<select id="baseVersion"></select></label>
  <span class="direction-arrow" aria-hidden="true">→</span>
  <label>Target Version<select id="targetVersion"></select></label>
  <div class="view-toggle" aria-label="Diff view">
    <button id="splitView" type="button" aria-pressed="true">Split</button>
    <button id="unifiedView" type="button" aria-pressed="false">Unified</button>
  </div>
</section>
<section class="evolution-summary" id="evolutionSummary" aria-label="Evolution summary"></section>
<section class="diff-panel">
  <div class="diff-panel-header diff-toolbar">
    <div class="current-file">
      <span id="fileStatus" class="file-status"></span>
      <h2 id="filePathTitle"></h2>
    </div>
    <div class="diff-summary" id="diffSummary"></div>
    <div class="change-navigation">
      <button id="previousChange" type="button" aria-label="Previous change">↑</button>
      <span id="changePosition">No changes</span>
      <button id="nextChange" type="button" aria-label="Next change">↓</button>
      <button id="expandAll" type="button">Expand all</button>
    </div>
  </div>
  <div class="diff-scroll" id="diffView"></div>
</section>
"""
    (compare_dir / "index.html").write_text(
        page_shell(
            title="Compare Code",
            body=body,
            versions=versions,
            current="compare",
            extra_class="compare-page",
            extra_body=(
                f'<script src="{versioned("../data/code.js", asset_version)}"></script>'
                f'<script src="{versioned("../assets/compare-core.js", asset_version)}">'
                "</script>"
                f'<script src="{versioned("../assets/compare.js", asset_version)}">'
                "</script>"
            ),
            asset_version=asset_version,
        )
    )


def build(out_dir: Path) -> None:
    versions = read_versions()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    shutil.copytree(ASSETS, out_dir / "assets")

    data_dir = out_dir / "data"
    data_dir.mkdir()
    code_payload = collect_code(versions)
    asset_version = build_asset_version(code_payload)
    (data_dir / "code.json").write_text(json.dumps(code_payload))
    (data_dir / "code.js").write_text(
        "window.TORCHLET_CODE = " + json.dumps(code_payload) + ";\n"
    )

    build_index(out_dir, versions, asset_version)
    build_version_pages(out_dir, versions, asset_version)
    build_compare(out_dir, versions, asset_version)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Torchlet docs site.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DOCS / "_site",
        help="Output directory for the generated static site.",
    )
    args = parser.parse_args()
    build(args.out)


if __name__ == "__main__":
    main()
