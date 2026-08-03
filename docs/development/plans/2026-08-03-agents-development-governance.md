# AGENTS Development Governance Implementation Plan

> **For agentic workers:** Execute inline in the current user-approved workspace. Do not commit, push, rebase, or rewrite history unless the user separately requests it.

**Goal:** Create the repository-wide `AGENTS.md`, migrate documentation into the approved taxonomy, update all path references, and verify the result.

**Architecture:** `AGENTS.md` is the concise enforcement layer and links to authoritative project documents. Durable project documentation lives below `docs/` by audience and purpose; transient agent state stays below ignored `.planning/` directories.

**Tech Stack:** Markdown, HTML, Git, Python 3.9+, pytest

## Global Constraints

- Preserve all user changes already present in the worktree.
- Do not change production behavior.
- Do not add, remove, or upgrade Python versions or runtime dependencies.
- Do not create a Git commit without a separate explicit user request.

---

### Task 1: Migrate documentation

**Files:**
- Move: `docs/ff-requirements.md` to `docs/requirements/ff.md`
- Move: `docs/ff-user-guide.html` to `docs/user/ff-user-guide.html`
- Move: `docs/ff-verification.md` to `docs/development/verification.md`
- Move: `docs/adr/*` to `docs/development/adr/`
- Move: `docs/research/*` to `docs/development/research/`
- Move: `docs/superpowers/specs/*` to `docs/development/designs/`
- Move: `docs/superpowers/plans/*` to `docs/development/plans/`

- [ ] Create destination directories without overwriting existing files.
- [ ] Move every source file using the approved exact mapping.
- [ ] Confirm no legacy document file remains under the old directories.

### Task 2: Add repository governance

**Files:**
- Create: `AGENTS.md`

- [ ] Write the approved rules for authority, workflow, TDD, documentation, dependencies, Git, safety, and verification.
- [ ] Confirm every referenced path exists after migration.

### Task 3: Repair references and verify

**Files:**
- Modify: repository files containing legacy `docs/` paths

- [ ] Search tracked and untracked project files for every legacy path.
- [ ] Replace only path references affected by the migration.
- [ ] Search again and confirm no stale reference remains outside historical Git metadata and ignored transient state.
- [ ] Run `.venv/bin/python -m pytest` and record the actual result.
- [ ] Review `git status --short` and `git diff --check` to confirm the migration preserved user work and introduced no whitespace errors.
