# Báo cáo QA độc lập — Runtime review V2b app-profile heap (97d0e7e)

- Ngày: 26/10/2026, Asia/Saigon.
- QA độc lập: Thực hiện độc lập trên máy đủ môi trường, không tham gia viết hoặc sửa gói app-profile/oracle/auditor này.
- Base commit kiểm chứng: `97d0e7e3be59fa8504d7ec0d6b55a0e67495ebff` trên nhánh `feat/bh07-app-profile-runtime-review`.
- Tested source runtime QA: `97d0e7e3be59fa8504d7ec0d6b55a0e67495ebff` (`git_dirty: false` tại thời điểm khởi động đo).
- Evidence QA riêng: [review_runtime_97d0e7e_evidence/](review_runtime_97d0e7e_evidence/). Không ghi đè bundle tác giả cũ; không xuất bản raw heap dump.
- Tiêu chí: [bh07_readiness.md §4.4](bh07_readiness.md). Bàn giao Codex điều phối chốt theo quy trình.

## 1. Kết luận

**Đạt trong phạm vi phép đo runtime profile độc lập 2 chu kỳ trên Web profile (V8/dart2js) + Chrome thật qua CDP.**

1. Đã tự thực thi đo runtime thật 2 chu kỳ `Owner → logout → Cohost` và `Owner → logout → Member` trong cùng SPA document (`performance.timeOrigin` không đổi giữa các mốc trong chu kỳ).
2. Sentinel STK ngân hàng riêng của Owner (`bank`) có mặt trong Dart/V8 heap khi Owner đang xem màn hình tài chính và biến mất hoàn toàn (0 occurrences, `present: false`) sau khi logout và sau khi Cohost/Member đăng nhập.
3. 24/24 record count/presence trong 8 snapshots nhất quán theo validator `heap_oracle.scan_problems`.
4. Bundle tác giả cũ tại `app_profile_heap_evidence/` được giữ nguyên vẹn 100% hash, không bị can thiệp hay ghi đè.
5. Toàn bộ 146 test Python, các probe/control cũ và kiểm tra tĩnh/unit Flutter đều PASS.
6. **Không suy bank sentinel thành mọi retained object/path đã sạch**: Cổng V2b §4.4 đầy đủ **chưa đóng** (retained paths tổng thể và Dart VM desktop/mobile giữ NOT RUN). Toàn BH-07 chưa nghiệm thu; không merge main/staging/production, deploy/pilot/BH-08.

## 2. Phát hiện (P0 / P1 / P2)

| Mức | file:dòng | Kết quả | Hướng xử lý |
| --- | --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi kiểm chứng này | — |
| P1 | — | Không có phát hiện mở trong phạm vi kiểm chứng này | — |
| P2 | — | Không có phát hiện mở trong phạm vi kiểm chứng này | — |

Không sửa source app, backend hoặc oracle/auditor để làm xanh kết quả.

## 3. Bằng chứng QA độc lập tự chạy

### 3.1. Replay test suites và adversarial controls

| Lệnh / Kiểm tra | Exit code | Kết quả độc lập |
| --- | --- | --- |
| `python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links` | 0 | **146/146 OK**, không skip (59.2 s) |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | **15/15** controls passed, fixture tạm được dọn |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | **8/8** controls passed |
| `count_controls.py` (review 0f11bb4) | 0 | Positive `[]`; 4 mutant count có finding; CLI exit 1 kèm `contradicts`, readonly |
| `closure_controls.py` (review 76334e2) | 0 | Literal/escaped cùng presence; retained escaped FAIL; thiếu metadata length/hash bị chặn |
| `extra_controls.py` (review 57ec02c) | 0 | Positive PASS; syntax/summary/Markdown/symlink/raw-sentinel bị chặn; CLI `{}` exit 1 |
| `probes.py` (review 8914b2f) | 0 | 8/8 ca probe cũ có finding chặn |
| `build_probe.js` (review 8914b2f) | 1 | Exit 1 đúng kỳ vọng từ chối `--reuse-build` |
| `link_audit.py` (review 57ec02c) | 0 | `[]` dead links |
| `reviewer_relation_controls.py` (review 5f2b5a6) | 0 | **5/5** assertions khớp |
| `verify_evidence.py` trên author bundle | 0 | PASS, readonly (hash 4 file tác giả không đổi) |
| `verify_evidence.py` trên QA runtime bundle | 0 | **PASS**, hoàn chỉnh, hash-consistent, không raw heap, không secret |
| `flutter analyze --no-pub` | 0 | No issues found (1.1 s) |
| `flutter test --no-pub` | 0 | **247 passed + 1 skipped** (suite HTTP/Auth skip mặc định) |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | 0 | Cú pháp hợp lệ |

### 3.2. Kết quả đo runtime 2 chu kỳ (`Owner → logout → Cohost/Member`)

- Môi trường: Windows 10 (10.0.26100), Node v24.21.0, Flutter 3.47.6, Chrome 155.0.8059.85.
- Local Supabase: API URL `http://127.0.0.1:54321`, CLI v2.121.0.
- Build profile: 37,8 s, 39 artifacts, `served_match: true`.
- Lệnh chạy: `$env:BH07_APPHEAP_EVIDENCE = "$PWD\docs\reviews\bh07\review_runtime_97d0e7e_evidence"; node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` (Exit code: 0).
- Kết quả: `status=RUN verdict=PASS cycles=2`.

| Chu kỳ | Actor path | Same doc | Mốc | Snapshot bytes | sha256[:12] | `bank` (present / occ) | `probe` (present / occ) | `expense` (present / occ) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner → logout → cohost | true | baseline | 58.391.821 | `ce5393b1a277` | false / 0 | **true / 1** | false / 0 |
| 1 | Owner → logout → cohost | true | owner_active | 84.284.234 | `207896445b28` | **true / 1** | **true / 1** | false / 0 |
| 1 | Owner → logout → cohost | true | post_logout | 69.412.978 | `fa5285a37344` | false / 0 | **true / 1** | false / 0 |
| 1 | Owner → logout → cohost | true | post_cohost | 81.973.743 | `ff214ea69394` | false / 0 | **true / 1** | false / 0 |
| 2 | Owner → logout → member | true | baseline | 58.359.025 | `c33bca69be3b` | false / 0 | **true / 1** | false / 0 |
| 2 | Owner → logout → member | true | owner_active | 84.832.453 | `adc612084d18` | **true / 1** | **true / 1** | false / 0 |
| 2 | Owner → logout → member | true | post_logout | 69.136.499 | `e195f6f64ead` | false / 0 | **true / 1** | false / 0 |
| 2 | Owner → logout → member | true | post_member | 73.611.276 | `fc7b4e9f58ce` | false / 0 | **true / 1** | false / 0 |

### 3.3. Đối chiếu bảo toàn tính toàn vẹn (Readonly & Cleanup)

- **Bundle tác giả (`app_profile_heap_evidence/`):**
  - `hashes.sha256`: `e1e1b8acbebdccd74fadcde0d248417a7da8c0afd1e302ef5988d460bf9077ad` (khớp)
  - `report.md`: `d23b6ce1a16cd20fa88cf9c460154053256242d852d6102fdc80d3c3c38b2cb6` (khớp)
  - `run.log`: `abd654eb894efb9064366e4d10427d220bd5f8f319e07e04a97536f338cf1ed6` (khớp)
  - `summary.json`: `2a8ee7ae15b6dc24fcb5ae7ed2c65c52fb6c2990cfb7cd9e6a434bf3be6cbe3f` (khớp)
- **Bundle QA runtime (`review_runtime_97d0e7e_evidence/`):**
  - `hashes.sha256`: `6b8c916df4b247225bb1532205b0cf67848547f505db844137eeb16074871f90  summary.json`, `cc91a6fa59fb3dc141d23d984848cec81e00524c327da3137836c6aeca665a19  run.log`, `99340cc547a3481bfa60d95e70a8bfee33c2656149d94a0e608524b99382053a  report.md`
- **Xác minh dọn dẹp (Cleanup verification):**
  `dump_dir_outside_repo: true`, `raw_snapshots_remaining: 0`, `dumps_dir_removed: true`, `chrome_profile_dir_removed: true`, `ok: true`.
  Quét toàn bộ workspace không có file `.heapsnapshot`, `.heapprofile` hay `.heaptimeline`.

## 4. NOT RUN và giới hạn kỹ thuật trung thực

| Hạng mục | Trạng thái kỹ thuật | Điều kiện / Ranh giới |
| --- | --- | --- |
| Phép đo retained paths tổng thể của tất cả models, caches, listeners, ghi chú, số dư | **NOT RUN** | **Không suy một bank sentinel thành mọi retained object/path đã sạch.** Phép đo sentinel chứng minh giá trị STK ngân hàng của Owner không còn reachable trong heap V8; chưa phải là kiểm chứng đồ thị tham chiếu (retained graph) toàn diện cho toàn bộ app model. Cổng V2b §4.4 đầy đủ **chưa đóng**. |
| Đo heap Dart VM trên desktop/mobile (VM-service) | **NOT RUN** | Gói này đo V8/dart2js heap của web profile. Host không có Visual Studio / Android SDK để đo Dart VM heap desktop/mobile. |
| Đo tải thật, nhiều actor đồng thời, mobile browser khác | **NOT RUN** | Chưa chạy trong phạm vi V2b. |
| V3/V4 Managed Supabase backup, PITR, retention, concurrent writers | **NOT RUN** | Cổng vận hành chưa chạy. |
| V5 Staging/production deploy và restore thật | **NOT RUN** | Cần môi trường và phê duyệt riêng. |
| V6 Banking / VietQR / webhook thật | **NOT RUN** | Ngoài phạm vi BH-07 hiện hành. |
| V7 Rehearsal tải thật/pilot và V8 Nghiệm thu toàn BH-07 | **NOT RUN** | Không nghiệm thu toàn dự án; không merge main/staging/production. |

## 5. Bàn giao

Báo cáo và bằng chứng được commit lên nhánh `feat/bh07-app-profile-runtime-review` và bàn giao Codex điều phối chốt theo đúng quy trình.
