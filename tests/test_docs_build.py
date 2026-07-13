from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_build_docs_module():
    spec = importlib.util.spec_from_file_location(
        "build_docs", ROOT / "tools" / "build_docs.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocsBuildTest(unittest.TestCase):
    def test_generated_pages_use_page_specific_documentation_layouts(self):
        build_docs = load_build_docs_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "site"
            build_docs.build(out_dir)

            index_html = (out_dir / "index.html").read_text()
            version_html = (
                out_dir / "versions" / "v02_kv_cache" / "index.html"
            ).read_text()
            compare_html = (out_dir / "compare" / "index.html").read_text()
            css = (out_dir / "assets" / "site.css").read_text()

        self.assertIn('class="readme-layout"', index_html)
        self.assertNotIn('aria-label="Version navigation"', index_html)
        self.assertIn('aria-label="Version navigation"', version_html)
        self.assertIn('aria-label="On this page"', version_html)
        self.assertIn('aria-label="File navigation"', compare_html)
        self.assertNotIn('aria-label="Version navigation"', compare_html)
        self.assertIn("--canvas-default: #f6f8fa;", css)
        self.assertIn("--accent-fg: #0969da;", css)

    def test_generated_site_uses_neutral_implementation_language(self):
        build_docs = load_build_docs_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "site"
            build_docs.build(out_dir)
            rendered_pages = "\n".join(
                path.read_text().lower() for path in out_dir.rglob("*.html")
            )

        for tutorial_term in ("walkthrough", "teaching", "teaches", "learns"):
            self.assertNotIn(tutorial_term, rendered_pages)
        self.assertIn("implementation notes", rendered_pages)
        self.assertIn("design pressure", rendered_pages)

    def test_compare_page_exposes_directed_workspace_and_version_metadata(self):
        build_docs = load_build_docs_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "site"
            build_docs.build(out_dir)
            compare_html = (out_dir / "compare" / "index.html").read_text()
            first_version_html = (
                out_dir / "versions" / "v00_full_recompute" / "index.html"
            ).read_text()
            payload = json.loads((out_dir / "data" / "code.json").read_text())

        self.assertIn('id="baseVersion"', compare_html)
        self.assertIn('id="targetVersion"', compare_html)
        self.assertIn('id="evolutionSummary"', compare_html)
        self.assertIn('id="changedFilesOnly"', compare_html)
        self.assertIn('id="splitView"', compare_html)
        self.assertIn('id="unifiedView"', compare_html)
        self.assertLess(
            compare_html.index("compare-core.js"), compare_html.index("compare.js")
        )
        self.assertIn(
            "?base=v00_full_recompute&amp;target=v01_0_ragged_batch",
            first_version_html,
        )
        self.assertEqual(payload["versions"][0]["title"], "Full Recompute")
        self.assertEqual(payload["versions"][0]["status"], "implemented")
        self.assertEqual(
            payload["versions"][1]["important_file"], "layer/gqa.py"
        )
        self.assertIn("padding", payload["versions"][1]["rationale"].lower())
        self.assertNotIn("v09_triton_basics", payload["code"])


if __name__ == "__main__":
    unittest.main()
