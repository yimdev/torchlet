# Torchlet Docs Architecture

The documentation site contains static implementation notes for Torchlet's
versioned inference implementations. It is designed to work on GitHub Pages
without Node, Ruby, or third-party Python packages.

## Structure

- `docs/content/index.md`: landing page copy.
- `docs/content/versions.json`: ordered version metadata used for navigation.
- `docs/content/versions/*.md`: one implementation note per roadmap Version.
- `docs/content/zh-CN/`: Chinese metadata and translated implementation notes.
- `docs/assets/site.css`: the documentation visual system.
- `docs/assets/compare-core.js`: DOM-free comparison model and diff calculation.
- `docs/assets/compare.js`: browser-side Compare workspace controller.
- `tools/build_docs.py`: static site generator.
- `.github/workflows/docs.yml`: GitHub Pages deployment workflow.

## Version Page Contract

Each version page should answer the same questions:

- What did this version introduce?
- Why was it introduced after the previous version?
- What core principle does it demonstrate?
- Which files should readers compare?
- What tradeoff is intentionally left visible?

This repeated structure helps readers compare
conceptual changes, not just code changes.

## Code Compare Page

The build script scans `src/torchlet/v*/**/*.py`, stores the source in each
locale's `data/code.js`, and creates static compare pages at
`docs/_site/compare/index.html` and `docs/_site/zh/compare/index.html`.

The page compares a Base Version to a later Target Version. It provides a
changed-file navigator, split and unified views, word-level highlights, folded
unchanged context, change navigation, and URL-restorable state. If a file exists
in only one Version, the missing side is shown as pure additions or deletions.

## Build Locally

```bash
python3 tools/build_docs.py
```

Then open `docs/_site/index.html` in a browser. The Chinese site is generated at
`docs/_site/zh/index.html`; language links preserve the current page.

## Deploy On GitHub Pages

The included workflow builds the docs on pushes to `main` and deploys
`docs/_site` through GitHub Pages.

In the repository settings, set Pages to use GitHub Actions as the source.

If the deployed page shows this README instead of the generated documentation
site, the repository is still using the branch-based Pages source. Change
Settings -> Pages -> Source to GitHub Actions, then rerun the docs workflow.
