# Repository history: rewrite & correction log

This file documents every event that altered this repository's git history or
that could otherwise mislead someone reading the raw commit log. It exists so the
record is honest about its own handling. Continuity of commit SHAs is **not**
guaranteed across the rewrite below; integrity of the published change-log
*content* was preserved throughout.

For the authenticity of updates going forward, rely on **GitHub's Activity view**
(Insights → Network / the repository Activity log), which records every push —
including force-pushes — with compare links, outside the control of this
repository's maintainer. Where present, GPG-signed tags on daily state provide
cryptographic attestation (see "Signing", below).

---

## Event 1 — First-run re-seed artifact (content correction, NOT a history rewrite)

- **When:** 2026-08-25, ~16:06–16:07 UTC
- **Commits involved (pre-rewrite SHAs):**
  - `71faa68` — "Daily update 2026-08-25: 96904 change(s)"
  - `6c1e92e` — "Revert spurious first-run baseline; cache now seeded for daily diffs"
- **After the history rewrite in Event 2, these became:** `b2abb8c` and `3c7c616`.
- **What happened:** When the daily job was migrated to GitHub Actions, the first
  run started with an empty state cache and therefore re-emitted the entire
  baseline as if it were a single day's changes — hence a commit labelled
  "96904 change(s)". This is a **re-seed artifact, not 96,904 real changes on
  Aug 25.** The very next commit reverted the doubled content; the current
  `changes.ndjson` contains one baseline (96,879 `initial` rows, all dated
  2026-08-21) plus genuine daily changes only.
- **Why the misleading commit label was left in place:** relabelling a commit is
  itself a history rewrite. To keep rewrites to the minimum, the label stands and
  is explained here instead. **Read "Daily update 2026-08-25: 96904 change(s)" as
  "re-seed (automation cache miss), corrected in the following commit."**
- These were both ordinary commits (a bad commit followed by its revert); **no
  force-push and no history rewrite occurred in Event 1.**

## Event 2 — History rewrite: removed working-state files (one force-push)

- **When:** 2026-08-25, ~16:50 UTC
- **Old head → new head:** `8e1ce4a` → `04f4bc3`
- **Tool:** `git filter-repo --path state.json --path violations_state.json --invert-paths`
- **What was removed:** every historical copy of `state.json` and
  `violations_state.json`. These are the differ's internal working snapshots
  (~25 MB and ~12 MB, rewritten every run); they were never intended as published
  artifacts and carry no archival value. Ten historical copies were removed.
- **What was preserved:** `changes.ndjson` and `violations_changes.ndjson` — the
  append-only public change logs — were left fully intact.
- **Effect:** repository history shrank substantially; all commit SHAs from the
  affected range were rewritten (this is inherent to `filter-repo`). Commit
  messages and author dates were preserved.
- **This required a force-push**, which is why the pre-rewrite SHAs (e.g.
  `8e1ce4a`) are no longer served by GitHub.

## Pre-rewrite chain preservation

The complete pre-rewrite commit chain (SHAs, dates, messages) is recorded in
[`PRE_REWRITE_CHAIN.txt`](PRE_REWRITE_CHAIN.txt). A full mirror of the repository
as it stood immediately before Event 2 is retained privately by the maintainer
(`phl-repo-prerewrite-backup.git`) and is **not** published, since it contains the
same content already public here plus the removed working-state files.

## Signing

Going forward, each daily state may be marked with a **GPG-signed git tag**, giving
a cryptographic attestation of the content at that point in time that does not
depend on commit-chain continuity. Verify with `git tag -v <tag>`.

---

*Maintained as part of an independent, volunteer open-data project. Questions welcome.*
