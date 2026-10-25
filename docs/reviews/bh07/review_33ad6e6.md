# Review V2b — 33ad6e6 — vòng sửa1/2

## Kết luận

**Chưa đạt gói sửa Provider/VM harness vòng1/2.** Đóng HP1 trong phần phân định phạm vi, HP4 vàHP5; HP2/HP3 còn mở, thêm HP6/HP7: **4 P2, không có P0/P1 mới được xác định**. Phần app profile heap của V2b vẫn **NOT RUN**, không yêu cầu biến Provider harness thành bằng chứng toàn ứng dụng và không kết luận app có leak thực tế.

- Ngày:25/10/2026 (Asia/Saigon).
- Tested source:`33ad6e6fd7e33b8495ec9dda0732df1b6df2096b`.
- Origin docs thực tế:`f40d7798edb4b726dc3dcd7ded2c0e44cbebf79d`; SHA dài `f40d7790b2d354b63eeae69a538202d0ec735497` trong yêu cầu không tồn tại.
- Base thực tế/commit cha:`2dac374fd98389b3ec9c54ec11f5781b01d32c77`, khác SHA dài trong yêu cầu/handoff (HP7).
- Reviewer không viết/sửa source gói heap. Checkout docs tip sạch trước kiểm, runtime tree bằng source33ad6e6. Chỉ thêm report/evidence/trạng thái; không sửa app/backend/contract hoặc bundle tác giả. V1/V5b giữ Đạt local.

## Rà soát HP1–HP5

| Điểm | Kết luận |
|---|---|
| HP1 | **Đóng về phạm vi**: source comment/handoff/summary tách Provider harness với app profile NOT RUN. Không coi đây là Đạt toàn V2b. Claim Finalizer vẫn chưa có implementation, cần bỏ trong metadata generator theo HP3. |
| HP2 | **Còn mở**. Năm controls cũ đã được sửa, nullable subscription được track; nhưng comment/string trong dispose vẫn được tính thành cancel/remove (bên dưới). Audit vẫn heuristic, không phải Dart AST/retention-path proof. |
| HP3 | **Còn mở**. Input FAIL cũ không còn tạo toàn PASS, nhưng subset/no-tests và Markdown vẫn có false-green/mâu thuẫn. |
| HP4 | **Đóng** cho bundle mới: log được track,4/4 hash khớp; source hashes4/4 khớp Git blob và current files; git_dirty=false/paths[] theo lần chạy tác giả. Không gán log mới thành log lịch sử ccad24c. |
| HP5 | **Đóng**: raw-byte manifest, CRLF/mismatch/missing/extra bị từ chối, positive PASS; self5 và probes cũ PASS đúng kỳ vọng; readonly trước/sau không đổi. |

## Phát hiện còn mở

### HP2 — P2: Comment/string được công nhận là đã dispose

- File:dòng:`scripts/bh07_heap/audit_ast_memory.py:171`, `scripts/bh07_heap/audit_ast_memory.py:179`.
- Tái hiện:`python docs/reviews/bh07/review_33ad6e6_evidence/extra_controls.py`, phần dispose_controls.
- Kỳ vọng: chỉ code thực thi cancel/remove trong dispose mới thỏa điều kiện audit; comment/string không phải lời gọi. Positive cancel thật phải giữ NONE.
- Thực tế: `_sub` nullable không được cancel, nhưng `// _sub?.cancel();` hoặc `print('_sub?.cancel()')` trong dispose đều được báo **LeakRisk NONE**, không có uncancelled subscription. `/* auth.removeListener(_onAuthChanged); */` cũng được coi là remove thật. Positive cancel thật trả NONE. Body extraction cân bằng braces vẫn tìm regex trong raw text, chưa phân biệt executable tokens với comment/string.
- Cách sửa: phân tích/tokenize lexical code trước nhận diện lời gọi và cân bằng braces, hoặc dùng parser hiện có; không claim chính xác khi chưa phân tích được. Thêm positive call và negative comment/string/block-comment/brace-in-string controls, giữ nguyên5 controls trước. Không sửa Provider app để làm xanh checker.

### HP3 — P2: Subset xanh đủ10 controls; Markdown có thể PASS khi parsed suite FAIL

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:133`, `scripts/bh07_heap/run_heap_verification.py:138`, `scripts/bh07_heap/run_heap_verification.py:234`.
- Tái hiện: extra_controls.py, summary_controls; chỉ gọi hàm hiện hành với fixture output trong temp.
- Kỳ vọng: xác minh đủ7 test identities và từng control, skip/missing/unknown không được PASS; Markdown/JSON/count/exit cùng verdict.
- Thực tế: `test_ok=True` + `00:00 +1: All tests passed!` cho tests_passed1 nhưng **cả10 controls PASS**, Markdown **7/7 Provider test PASS**. `test_ok=True` + `No tests ran.` tạo JSON FAIL nhưng Markdown vẫn claim7/7 PASS. Numeric parse thất bại vẫn mặc định7; report dựa bool đầu vào thay vì verdict/coverage thực. Positive đủ7 PASS và failed fixture FAIL vẫn đúng, không bị đổi kỳ vọng.
- Cách sửa: structured reporter events/expected test identity mapping, đủ control coverage; không fallback thành7, không gán toàn PASS từ một marker chung. Dùng cùng parsed verdict/count/coverage để quyết định Markdown và kết quả runner; chưa chạy/skip ghi NOT_RUN/UNKNOWN đúng trường hợp. Loại claim Finalizer khỏi metadata nếu suite không sử dụng Finalizer; `WeakReference` target-null không phải xóa mọi bản sao RAM.

### HP6 — P2 mới: Lỗi git status bị ghi thành clean checkout

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:42`.
- Tái hiện: extra_controls.py, git_status_failure: rev-parse trả source hợp lệ, status phát sinh CalledProcessError128.
- Kỳ vọng: trạng thái cleanliness UNKNOWN/FAIL kèm lỗi; không được phát hành git_dirty=false khi chưa đọc được status.
- Thực tế: hàm nuốt exception, trả **git_dirty=false, dirty_paths=[]** như checkout sạch. Source hashes không thay thế được thông tin Git/những file khác trong working tree. Không khẳng định metadata bundle đang giả: source hashes hiện tại đã khớp; đây là fault control về provenance fail-open.
- Cách sửa: raise/fail-closed hoặc trường UNKNOWN có error và chặn success publication; không coi UNKNOWN_SHA/missing source hash là provenance hợp lệ. Có positive clean/dirty và status/rev-parse failure controls. Không cần sửa Git/permission thật để test.

### HP7 — P2 mới: Base review “thực tế” trong handoff không tồn tại

- File:dòng:`docs/reviews/bh07/private_heap_handoff.md:5`; thông tin/prompt base cùng SHA nếu được lặp lại.
- Tái hiện:
  ```bash
  git cat-file -e '2dac37434df6b9409b53e36e65f3bc85bf755b40^{commit}'
  git rev-parse '33ad6e6^'
  ```
- Kỳ vọng: base bàn giao resolve được và trỏ đúng review ccad24c/cha tested source.
- Thực tế: SHA dài trong handoff/yêu cầu không tồn tại. Base thật là **`2dac374fd98389b3ec9c54ec11f5781b01d32c77`**. Cùng prefix7 ký tự không làm hai SHA thành một.
- Cách sửa: docs-only đính chính thông tin hiện hành/prompt sang SHA thật, giữ trace input sai trong lịch sử; không đổi tested source hoặc chế tạo metadata. Dùng URL GitHub commit hợp lệ thay link tương đối `../../../commit/...` không phải file local trong handoff.

## Reviewer tự chạy

Evidence riêng:[review_33ad6e6_evidence/](review_33ad6e6_evidence/).

| Lệnh/kiểm tra | Kết quả mới |
|---|---|
| Heap test | Flutter3.47.7 Linux, `flutter test --no-pub test/integration/bh07_heap_verification_test.dart`: **exit0,7/7 PASS** |
| Analyze | `flutter analyze --no-pub`: **exit0,0 issue** |
| Full Flutter | `flutter test --no-pub`: **exit0,247 PASS+1 skip** |
| AST self-controls | **exit0,5/5** |
| AST main | Probe reviewer cũ chạy nguyên script hiện hành trên disposable script/lib copy38 file; **exit0**, JSON byte-identical bundle, Auth subscription tracked1. Tránh command ghi đè artifact tác giả. |
| Verifier self-controls | **exit0,5/5**, expected error output là negative cases, không phải lỗi orchestrator |
| Bundle verify | **exit0,4/4**, strict UTF-8 LF, secret scan theo verifier; toàn bundle fingerprint trước/sau bằng nhau |
| Probe cũ | `python docs/reviews/bh07/review_ccad24c_evidence/probes.py`: **exit0**, nguyên file/kỳ vọng/positive controls; output xác nhận5 case audit cũ và fail-summary/manifest đã được sửa |
| Extra controls | **exit0 của probe**, ghi rõ false-green HP2/HP3/HP6; không gọi các false-green là gate PASS |
| Source/provenance | Source hash4/4 khớp33ad6e6 Git blob/current bytes; không diff runtime tree source..docs, không diff lib/supabase từ base thật |

Dùng --no-pub với dependencies đã có; Flutter harness được bind loopback local. Khác tác giả Windows Flutter3.47.6. Log reviewer chuẩn hóa UTF-8 LF. Không chạy full orchestrator/generate vào bundle tác giả; các summary/Git/lexical controls dùng temp/monkeypatch giới hạn rồi khôi phục, không sửa source. Raw log mới hiện có nhưng không diễn giải thành thực thi profile app.

## NOT RUN

- **V2b app profile heap snapshot/retained paths** trên app thật, widget/Auth/SupabaseClient graph, Chrome CDP/VM-service memory measurement và raw-dump cleanup. Đây là phạm vi đã tách minh bạch, không phải Provider suite FAIL hay app leak đã chứng minh.
- Finalizer callbacks: suite không có Finalizer instance; metadata không được tính là kết quả đo.
- HTTP/JWT/Auth thật trong lượt này; fake Auth/mock repositories không thay bằng chứng cũ của V1/HTTP.
- Full runner regenerate bundle tác giả (tùy chọn) không chạy; đã tự chạy các thành phần và failure controls riêng.
- DB hồi quy mới không chạy vì không đổi backend/migration; V2 device/browser khác/offline/deep link, V3 managed backup/PITR/offsite/encryption/retention,V4 concurrent writers,V5 staging/production restore/deploy,V6 banking/webhook,V7 tải/pilot,V8 toàn BH-07 giữ NOT RUN.

## Bước tiếp

Giao sửa **vòng2/2** chỉ HP2/HP3/HP6/HP7. Giữ HP1 phạm vi bổ trợ/App profile NOT RUN, HP4/HP5 và các controls đã qua. Không yêu cầu sửa app hoặc ép đo toàn app trong vòng sửa tooling này. Tạo regression tests cho extra controls, không sửa kỳ vọng/positive để xanh; chạy lại commands, xuất source/bundle mới sạch và bàn giao reviewer. Nếu còn lỗi sau vòng2/2, dừng theo AGENTS và báo chủ dự án, không tự mở vòng3.

**Kết luận cuối: Chưa đạt gói sửa vòng1/2; V2b app-profile vẫn NOT RUN. V1/V5b giữ Đạt local; không merge main/staging/production/deploy/pilot/BH-08.**
