# BH-07 bank tooling integration scope

The owner approved dependency review and preparation of a scoped integration package after local acceptance at `57cd2c4`. Approval does not include merging main, pushing, deploying, accepting all BH-07 gates or starting another implementation task.

Prepare a reproducible draft patch against a pinned main revision, containing the bank tooling and the actual source/test/evidence dependencies needed to verify it offline. Export main into an ignored build directory and apply the patch only there. Do not switch/rebase the current branch, create a linked worktree, alter main, or copy app/backend changes merely to make checks green.

The package must distinguish offline tool compatibility from live bank runtime compatibility. The accepted runtime belongs to `a095a45`; it must never be relabeled as a run against main. Main lacks the heap framework and also differs in BH-07 app code and migration. Missing UI/RPC/schema/fixture prerequisites and the still-open full BH-07 gates must be explicit.

Deliver a file/hash manifest, dependency inventory, apply-check result, offline test logs, app/backend preservation check, draft patch and an integration recommendation. Check remote main without printing credentials or raw authentication errors. If remote main differs, report the base drift rather than quietly claiming the local revision is current.

Any newly required production adaptation remains Antigravity implementation work using only Gemini 3.8 Flash (High), followed by Codex review. This preparation copies verified source bytes and runs existing checks; it does not implement adaptations.

Observed checkout requirement: the package may generate an exact root-anchored Git attributes policy to preserve the selected bytes under autocrlf=true, without changing global settings or app/backend files. Validate actual working-tree and fresh-index hashes, stage ignored logs, and create ignored build/ before probe replay. Cached apply followed by forced index checkout is permitted only inside a newly created clean private verification/integration workspace, never in a user-modified checkout.
