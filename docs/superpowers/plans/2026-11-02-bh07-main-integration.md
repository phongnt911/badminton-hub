# BH-07 Bank Tooling Integration Preparation Plan

> **For agentic workers:** Use superpowers:executing-plans for this inline review/packaging preparation. Production adaptations, if later authorized, belong to Antigravity exclusively on Gemini 3.8 Flash (High); Codex reviews. No parallel implementers are needed.

**Goal:** Produce a reviewable integration candidate and an evidence-backed dependency decision without changing main.

**Architecture:** Pin source/main Git revisions, derive the tool/test/fixture closure, export main below ignored `build/`, and apply a generated draft patch only to that export. Validate offline behavior and separately inventory missing live app/backend prerequisites.

**Tech Stack:** Existing Git, Python standard library, Node, Flutter; no new packages.

**Spec:** [integration scope](../specs/2026-11-02-bh07-main-integration-scope.md)

**Preparation complete (v4):** 59-file tooling-only candidate;311Python,fixture8/8,analyze0,190Flutter. Fresh Git checkout under core.autocrlf=true preserves all59 hashes and629 main files; final package review closes P2. No merge or main bank runtime; owner scope decision pending.

## Global Constraints

- No merge, push, deploy, live DB mutation, app/backend editing or automatic acceptance of full V2b/BH-07.
- Keep the active branch, main ref, all existing app/backend files and historical evidence unchanged.
- Never print credentials; capture network errors privately and report only safe metadata.
- Keep candidate fixture bundles tied to their original tested source; historical replay is not new runtime evidence.

## Review Focus

- Source imports or replay probes resolving outside the exported candidate.
- Missing fixtures causing false compatibility failures, or unnoticed app dependencies hidden by fixture replay.
- A passing offline test being presented as a passing main runtime.
- A patch silently including inherited app/backend or unrelated verification work.
- A stale main revision or accidental writes to the active branch/main during packaging.

### Task 1: Pin and inventory

**Files:** Create `docs/reviews/bh07/bank_tooling_main_integration.md` and its evidence directory; use ignored build automation for inspection.

- [x] Confirm clean starting source `57cd2c4`, local main `62d2c67`, merge base and inherited app/backend delta.
- [x] Check remote main safely and record exact base freshness.
- [x] Record direct/import/replay fixture dependencies and live UI/RPC/schema prerequisites.

### Task 2: Prepare and verify a draft package

**Files:** Create ignored `build/bh07-main-integration-<base>-<source>/` containing patch, manifest, main export and logs. Do not modify production files.

- [x] Export pinned main into a fresh directory; refuse overwriting an existing package.
- [x] Generate a tooling-only patch from pinned source plus an explicit candidate notice.
- [x] Run `git apply --check` and apply only under the exported directory.
- [x] Run selected bank/core tooling tests, fixture controls and historical auditors there; record actual counts and failures.
- [x] Verify baseline app/backend bytes and active Git refs remain unchanged.
- [x] Stage all59 paths, preserve6 ignored logs and verify actual Git checkout under core.autocrlf=true; use cached apply/index checkout only in a fresh clean private workspace, and create build/ before replay.

### Task 3: Report the integration boundary

- [x] Publish package hashes, logs, scope and missing live prerequisites.
- [x] Recommend a concrete next integration step; request approval before any main merge or widening to app/backend changes.
