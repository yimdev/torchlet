# Documentation and Code Compare Redesign

## Objective

Redesign the static documentation site so readers can examine the directed code
changes from an earlier implementation Version to a later Version. Use neutral
technical language: the site explains implementation stages and design
pressures; it is not presented as a course or tutorial.

## Site-wide layout

- Apply a GitHub-inspired light visual system across the whole site: gray page
  canvas, white surfaces, gray borders, blue links and primary actions, and
  light red/green diff colors.
- Keep the site in English and optimize it for desktop. Mobile-specific layouts
  and controls are out of scope.
- Use a compact shared top bar.
- Make the home page a single-column README-style overview with prominent links
  to the version notes and code comparison, followed by the version route.
- Give Version pages a left Version navigation, main explanatory article, and a
  right in-page table of contents.
- Give the Compare page a file navigation sidebar and the diff workspace. It
  must not also show the site-wide Version sidebar or article table of contents.

## Version comparison

- A comparison is directed from a Base Version to a later Target Version. Do not
  allow same-Version or reverse comparisons.
- Only implemented Versions with code snapshots can be comparison endpoints.
- Direct entry to Compare defaults to the first adjacent pair, `v00` to `v01`.
  Links from Version pages select that Version's adjacent comparison.
- Version controls display both the Version ID and short title. Target choices
  contain only Versions later than the selected Base Version.
- Provide previous and next adjacent-comparison actions.
- Show a compact evolution summary. For adjacent Versions, show the Target
  Version theme and rationale; for non-adjacent Versions, show the intervening
  Version stages in a collapsed list with links to their notes.

## File navigation

- Replace the Compare page's Version sidebar with a file navigation sidebar.
- Default to changed files and offer an All files toggle.
- Group paths by directory. Mark added, modified, and deleted files and show
  per-file added/deleted line counts. De-emphasize unchanged files.
- Prefer the Target Version's configured important comparison file. Otherwise
  select the changed file with the most changed lines. An explicit URL file wins.
- Do not infer renames: a missing old path plus a new path is a deletion and an
  addition unless an explicit mapping is added in the future.
- If a pair has no changes, show an explicit empty state.

## Diff workspace

- Default to a side-by-side view and provide a unified-view toggle. Remember the
  last selected mode.
- Render Python syntax highlighting. Changed line pairs also receive word-level
  red/green highlighting; pure additions and deletions use whole-line color.
- Collapse long unchanged regions by default with three context lines on either
  side. A collapse row states how many lines are hidden and can expand just that
  region; also provide Expand all.
- Show the current change index and total, with previous/next change controls and
  `[` / `]` keyboard shortcuts. Keep the controls visible while the diff scrolls.
- Do not wrap code lines. Allow horizontal scrolling and keep line numbers fixed.
- Do not provide an Ignore whitespace option.
- Encode Base Version, Target Version, file, view mode, and current change in the
  URL. Do not encode transient expansion state.

## Technical constraints

- Keep the production build dependency-free: Python standard library plus native
  HTML, CSS, and JavaScript. Do not require Node, a frontend framework, or a CDN
  to build or browse the site.
- Keep GitHub Pages and offline static-file browsing working.
- The current source scale does not require virtualization or background work.

## Verification seams

- `tools/build_docs.py --out DIR` is the public static-build seam.
- A DOM-free native JavaScript comparison module is the comparison-model seam.
  Node's built-in test runner may test it, but Node is not a production build
  dependency.
- The generated site is manually verified in a real browser for Version and file
  selection, diff modes, context expansion, change navigation, and URL restore.
