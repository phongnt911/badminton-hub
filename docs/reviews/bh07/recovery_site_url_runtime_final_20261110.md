# V4 recovery runtime final — 10/11/2026

**PASS trong phạm vi Docker local/staging-like; BH-07/V8 chưa nghiệm thu.** Source `7589179798b4849e6a6f2e961ebcfe03aafeea6c`, Git sạch khi chạy; run `9abccc56`, runner thường không wrapper, exit0, 113.656s, execution_completed=true, stage=completed, findings rỗng.

Codex chạy Docker thực tế. Reviewer riêng kiểm source, artifact và tự chạy validator PASS; đây không phải lần Docker thứ hai của reviewer. Không còn P0/P1/P2 trong phạm vi V4 đã review.

- P0 có trước snapshot. Hai writer HTTP authenticated thật trả200 trong cửa sổ dump7.750s; COPY sample4.950ms nằm hoàn toàn trong cả hai khoảng HTTP.
- Source counts3:3:3:3; restored1:1:1:1. P0 phục hồi khớp identities/relationships/stored result và digest tính lại; writes sau snapshot bị loại đúng.
- Replay authenticated trả cùng payment ID, không tăng dòng; fingerprint trước/sau giống nhau trên48bảng và schema. Padding khớp.
- Cleanup xác minh8/8resource owned vắng và private dump đã xóa. Inventory độc lập sau run:0container, chỉ network mặc định bridge/host/none.
- Full553test:549PASS+4SKIP, exit0,161.649s;53runtime-collection PASS;49probe controls PASS. Flutter mới NOT RUN; app/schema không đổi so với b25aaef.

## Evidence

[Summary](v4_runtime_20261110_evidence/7589179_summary.json), [source fingerprints](v4_runtime_20261110_evidence/7589179_source_fingerprints.json), [restored fingerprints](v4_runtime_20261110_evidence/7589179_restored_fingerprints.json) là bản sao nguyên byte. Summary SHA256 `c3eda1aa1e7cf0d22cb33ef6dace1460439a857f99ed0d5d0dbed37e0f40819a`.

Lệnh: Python `scripts/bh07_backup/run_v4_concurrent_rehearsal.py --out .build/bh07-v4-site-url-7589179`. Log local full suite `.build/recovery-site-url-full-python.log`, probe `.build/recovery-site-url-probe.log`. Validator `validate_v4_rehearsal(summary, source_fingerprints, restored_fingerprints)` trả ok=true/verdict=PASS/findings=[].

[Review source/test](recovery_site_url_review_20261110.md) và [diagnosis](recovery_site_url_diagnosis_20261110.md) giải thích delta SITE_URL. Những run FAIL trước giữ nguyên lịch sử, được supersede trong phạm vi local V4 bằng run này. Managed PITR/offsite V3 không được chứng minh bởi V4 local.

[Ma trận hiện hành](bh07_completion_status_20261110.md) và [bảng quyết định owner](bh07_v8_risk_decision_packet_20261110.md) còn V2/V2b/V3/V5/V7. Không ký risk acceptance, merge/deploy/pilot/BH-08.
