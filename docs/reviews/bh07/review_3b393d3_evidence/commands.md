# Coordinator audit 28/10/2026 Asia/Saigon

Clean checkout 3b393d33dd3dd773a92c1e4f2f4cbfd27af259e6, parent/runtime source b13e468d33e0d96437b58bb2da6088bff689b9eb, publisher source29f44a8. Initial fetch in network sandbox failed proxy connection; fetch with network permissions succeeded. No source changes or runtime/DB mutation by coordinator.

Audit commands are recorded in audit.json, outputs in *_0.log (generic readonly integrity/secret/encoding) and *_1.log (semantic auditor). Source audit code is audit.py; it uses paths of this reviewer workspace/scratch. All subprocess exits were checked against expected values. Each bundle has three payload hashes and one manifest. Five bundles were checked against Git blobs and full before/after byte hashes. Two obsolete bundles fail semantic verification deliberately, while their byte integrity remains valid. QA bundle passes semantic verification; R1 also passes; the historical bank-only QA bundle is audited for integrity only.

No new Flutter/Python suite or runtime was run by coordinator: docs/evidence-only diff, accepted source unchanged. QA report claims312 Python,34 oracle,6 fixture,8 guard,analyze0,247Flutter+1skip; no individual suite logs accompany this four-file runtime bundle, so those are not independently recertified here. No new SQL query or raw heap parse by coordinator. Runtime receipt and sanitized path records are cross-checked, not substituted for fresh runtime.

Own manifest is generated from reviewer output only, then verified readonly. No author manifest is regenerated. No production/staging contact. All old bundle bytes preserved.
