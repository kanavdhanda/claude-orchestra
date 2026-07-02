# claude-orchestra — Project Instructions

## Start of session
Read the top line of `docs/SESSION_LOG.md`'s index. Open that line's
`docs/sessions/<date>.md` file only if you need more detail.

## Before making a change, don't read every doc — grep frontmatter
- Find decisions/research by topic:
  `rg -l "tags:.*<keyword>" docs/decisions/ docs/research/`
- See a specific file's links:
  `rg -A3 "^related:|^influences:" docs/decisions/<slug>.md`
- Find what elsewhere is influenced by a file:
  `rg "influences:.*<slug>" docs/decisions/ docs/research/ docs/ARCHITECTURE.md`
- Find every prose reference to a file:
  `rg "\[\[<slug>\]\]" docs/`

Each call returns matched lines/filenames only — well under 100 tokens. Never
load the whole decisions/research tree to answer a lookup.

## When finishing meaningful work
1. Create `docs/sessions/YYYY-MM-DD.md` (or append to today's file if one
   already exists) with the full entry, then add one short line to the top
   of `docs/SESSION_LOG.md`'s index. Never write session content directly
   into the index.
2. If the work changed what a decision/paper relates to or affects, update
   *that file's* `related:`/`influences:` frontmatter only — don't backfill
   the whole graph.
3. New decisions: `docs/decisions/NNNN-slug.md`, existing ADR body format plus
   the `tags`/`related`/`influences` frontmatter block; add a line to
   `docs/decisions/README.md`.
4. New papers: `docs/research/<slug>.md` from the template in
   `docs/research.md`; add a line there too.
