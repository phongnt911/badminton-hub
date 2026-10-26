# Review V2b — b7eb881 — sau sửa HP3-A/B/C

## Kết luận

**Chưa đạt gói tooling Provider harness. Đóng HP3-A/HP3-B; HP3-C còn1 P2 về duplicate có tên đầy đủ giống hệt nhau.** Không xác định P0/P1 mới. HP1/HP2/HP4/HP5/HP6/HP7 và phạm vi Provider harness giữ nguyên; **app-profile heap vẫn NOT RUN**, không có kết luận app leak.

- Ngày:26/10/2026 (Asia/Saigon).
- Base review:`30feeb981b36473711d5ed4120ba7e14082f95c7` ([review cb5bf41](review_cb5bf41.md)).
- Tested source:`16e5b5116738ab9d4417fe11b651aea794868401`.
- Docs/evidence:`b7eb881663a85dbf0d3038d828ef82f43e728bca` (đúng origin khi fetch).
- Đây là review bản sửa theo ủy quyền ngoại lệ đã bàn giao, không tự mở lại hai vòng sửa trước. Reviewer không sửa source/app/backend/contract. Full runner ở worktree riêng source16e5b51 sạch trước capture; bundle tác giả giữ nguyên.

## Rà soát ba điểm

| Điểm | Kết luận |
|---|---|
| HP3-A | **Đóng trong các trường hợp được kiểm**: full runner trên checkout mới thực sự PASS7/7 VERIFIED, xử lý pub diagnostics trước JSON; replay stream reviewer cũ PASS; bỏ một expected testDone không PASS, partial protocol test trong32 tests cũng không PASS. |
| HP3-B | **Đóng**: success+skipped=true chuẩn Flutter được normalize NOT_RUN,6 pass+1skip,INCOMPLETE/FAIL; Markdown không claim7/7. Positive success/skipped=false giữ PASS. |
| HP3-C | **Chưa đóng**: unknown extra và duplicate khác prefix/group bị chặn, counts≤7. Nhưng exact same full name với2 test IDs bị dictionary gộp trước validator, vẫn PASS/VERIFIED và không báo duplicate. |

## Phát hiện còn mở

### HP3-C — P2: Duplicate tên đầy đủ bị last-write-wins trước khi kiểm coverage

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:208`; regression chưa bao phủ exact-name case tại `tests/test_bh07_heap_controls.py:316` (test duplicate đang đổi tên group).
- Tái hiện từ repo root:
  ```bash
  python docs/reviews/bh07/review_b7eb881_evidence/duplicate_probe.py
  ```
  Probe lấy7 identity/event thật trong raw runner output; giữ nguyên positive, thêm test ID999 với **name bằng chính xác full name** của Baseline đã có. Source/event cũ không bị sửa trên đĩa. Compare negative khác group cũng được giữ.
- Kỳ vọng:8 visible test IDs, một expected identity xuất hiện hai lần phải FAIL/không VERIFIED, tests_duplicate có thông tin; không claim7/7. Count canonical không vượt7 nhưng không được dùng dedupe để che duplicate.
- Thực tế: `_parse_json_events()` dùng `results[name] = ...` nên event củaID999 ghi đè record cùng tên trước `_verdict_from_results`. Kết quả **PASS,tests_passed7,tests_duplicate[],VERIFIED**, Markdown **7/7 Provider test PASS**. Main-boundary control với external commands stubbed cũng trả **exit0**. Đây là control của quyết định gate, không giả làm lần chạy full runner thứ hai.
- Đối chứng:7 real expected identities bình thường PASS; duplicate cùng expected identity nhưng **khác tên group** FAIL/UNVERIFIED, main-boundary exit1 đúng. Chỉ đổi equality của full name thì gate xanh sai.
- Xác nhận bằng Flutter thật: fixture reviewer [duplicate_names_fixture.txt](review_b7eb881_evidence/duplicate_names_fixture.txt) được copy thành .dart ở scratch ngoài repo rồi chạy Flutter test --reporter json. [Log](review_b7eb881_evidence/real_duplicate_names.log) ghi **hai testStart IDs3/4, cùng full name `reviewer identical test name`**, cả hai success, exit0. Tên không phải khóa duy nhất của protocol; đây là dạng stream hợp lệ.
- Cách sửa: giữ từng record theo testID/list và phát hiện duplicate canonical identity **trước khi** giảm xuống dict theo tên; không làm mất multiplicity của exact full name. Bổ sung exact-name/different-ID regression và giữ duplicate khác group, unknown extra, skipped, prefix diagnostics và7-test positive đã qua. Counts/control/Markdown/exit phải dùng cùng kết quả duplicate đã được giữ lại. Không cần sửa app/backend/Provider suite hoặc viết lại các gate đã đóng.

## Reviewer tự chạy

Evidence riêng:[review_b7eb881_evidence/](review_b7eb881_evidence/).

| Lệnh/kiểm tra | Kết quả mới |
|---|---|
| python scripts/bh07_heap/run_heap_verification.py | **Exit0**, source16e5b51 sạch trước chạy; suite **PASS7/7,VERIFIED**, provenance CLEAN,AST CLEAN,manifest4/4. Lượt này có package-resolution diagnostics, không dùng wrapper/--no-pub để né parser. |
| python -m unittest tests.test_bh07_heap_controls -v | **Exit0,32/32 OK**; không coi32 tests là đủ bao phủ exact-name duplicate |
| audit_ast_memory.py --test-controls | **Exit0,12/12** |
| clean_and_manifest.py --test-controls | **Exit0,5/5** |
| clean_and_manifest.py --verify | **Exit0,4/4** bundle tác giả; hash trước/sau giống nhau, source hashes4/4 khớp16e5b51 vàcurrent bytes |
| review_cb5bf41_evidence/protocol_probe.py | **Exit0**, nguyên file: raw prefix PASS7/7; JSON-only positive PASS; true skip FAIL6+1; unknown extra FAIL7/UNVERIFIED; hai Markdown negative đều không claim7/7 |
| review_ccad24c_evidence/probes.py | **Exit0**, nguyên file vàpositive/negative expectation giữ nguyên |
| review_33ad6e6_evidence/extra_controls.py | **Exit0**, nguyên file; lexical dispose vàUNKNOWN Git/error giữ đúng; legacy full-positive COUNT_ONLY không đổi |
| flutter analyze --no-pub | **Exit0,0 issue** |
| flutter test --no-pub | **Exit0,247 PASS+1 skip** |
| Flutter duplicate-name diagnostic fixture | **Exit0,2/2**, distinct IDs/same names thật; fixture ngoài app/test source, không cộng thành249 regression tests |
| Exact duplicate protocol probe | Exit0 của probe orchestration; output công bố1 false-green, không gọi negative case đó là gate PASS |
| Source/scope | Source..docs không đổi runtime tree; base..source chỉ runner +Python regression tests; Provider heap suite/lib/backend/migration giữ nguyên. Handoff2 SHA40-hex resolve. |

Reviewer Linux Flutter3.47.7, khác tác giả Windows3.47.6. Full runner dùng SDK trên PATH, không sửa command/expectation; output vào worktree reviewer để giữ author bundle. Runner-generated JSON/report/log mới được lưu ở runner_output; manifest gốc của lượt này được giữ nguyên bytes dưới tên original_manifest.txt để tương thích recursive verifier. Các log reviewer đóng gói UTF-8 LF, không có raw heap dump.

## NOT RUN và giới hạn giữ nguyên

- **App-profile heap snapshot/retained paths trên app thật**:NOT RUN. Provider harness không chứng minh mọi bản sao dữ liệu đã rời RAM; không nâng thành Đạt toàn V2b.
- Real HTTP/JWT/Auth/DB/migration/managed backup/PITR/offsite/encryption/retention/concurrent writers trong lượt tooling này.
- Device/browser khác/offline/deep link,banking/webhook,staging/production restore/deploy,load rehearsal/pilot và nghiệm thu toàn BH-07.
- Stubbed main-boundary controls không phải full runtime; chúng chỉ kiểm đường quyết định exit với input protocol âm/dương có kiểm soát. Full runner thật7/7 đã chạy riêng và được ghi rõ ở bảng.

## Bước tiếp

Bản sửa ngoại lệ vẫn còn HP3-C, **dừng gói và báo chủ dự án quyết định**, không tự giao đợt sửa mới hoặc chỉnh source trong vai reviewer. Cách sửa và positive/negative controls cụ thể đã có để dùng nếu được ủy quyền riêng. Giữ HP3-A/B,HP1/HP2/HP4/HP5/HP6/HP7 đã đóng trong phạm vi; V1/V5b Đạt local,app-profile heap NOT RUN; không merge main/staging/production/deploy/pilot/BH-08.

**Kết luận cuối: Chưa đạt gói tooling sau sửa HP3, còn1 P2 HP3-C exact-name duplicate.**
