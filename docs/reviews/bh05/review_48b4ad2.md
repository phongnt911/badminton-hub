# Review độc lập BH-05C — 48b4ad2

Ngày 16/10/2026 (Việt Nam). Nhánh feat/bh05c-ui, tested HEAD `48b4ad2`, code remediation `ef88f05`. Vai trò reviewer theo docs/ai/REVIEWER.md tại chore/ai-roles (`163bc45`); đọc AGENTS/04/08 và BH05/R2/R7 ở 09. Không sửa code/migrations hoặc apply remote DB.

## Phạm vi

`git diff origin/main...HEAD`, main remote da1285d, merge-base d8dfe74; tập trung phần C và bản sửa C1–C3, bao gồm API roster ClubProvider được thêm để phục vụ UI. Không lặp lỗi A/B đã đóng hoặc nghiệm thu main/production.

## C1-R — P2: đang tải lại lời mời vẫn cho chấp nhận bằng cache cũ

**File:dòng:** `lib/screens/session_detail_screen.dart:708-710` (hasInvitation/canAccept), `:770-773` (nút chấp nhận).

**Mô tả:** hasInvitation chỉ kiểm invitationErrorMessage==null và invitation!=null, không kiểm !isLoadingInvitation. Provider giữ invitation trước đó khi bắt đầu refresh. Vì vậy cùng lúc UI hiện “Đang tải lời mời…” thì nút “Chấp nhận lời mời” vẫn enabled nếu đã có cache. Có thể gửi accept bằng lời mời chưa được xác minh lại, đã bị host thu hồi/hết hiệu lực ở server. Server vẫn kiểm quyền/expiry nên không tuyên bố bypass hoặc vượt slot; đây là phần UI-state C1 chưa hoàn tất, trái mục tiêu remediation “lỗi/đang tải thì không trình bày dữ liệu cũ như lời mời đã xác minh”.

Probe độc lập: tải invitation i1 thành công, giữ lần refresh thứ hai bằng Completer; isLoadingInvitation=true, dòng loading có hiển thị nhưng FilledButton accept.onPressed vẫn khác null. Kỳ vọng nút ẩn/disabled trong lúc tải → FAIL. Probe hoàn tất request và không thay application code.

**Cách sửa:** canAccept/hasInvitation phải loại trạng thái đang tải hoặc tách cờ actionable chỉ khi tải thành công; không cần thay RPC/quyền. Thêm widget regression với cache cũ + refresh đang chờ, lỗi/null sau refresh, và nút chỉ bật lại sau response thành công hợp lệ. Giữ nhánh error+retry đã có.

## Kết quả độc lập

- Flutter3.47.7/Dart3.13.5: flutter analyze --no-pub → No issues found, exit 0.
- flutter test --no-pub → **131/131 PASS**, exit 0.
- Bốn probe UI độc lập: **3 PASS /1 FAIL**. [Log](review_48b4ad2_probe_results.txt). Ba probe baseline từ review_8974d3c đã chạy lại cùng probe mới; file test tạm chuyển sang `/workspace/scratch/bh05c-r2-review/review_bh05c_probe_test.dart`, không giữ thay đổi implementation trong repo.
- `BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh05/run_bh05_tests.py`: **84/84 PASS**, exit 0; [JSON](bh05_test_results_20261015183710.json) ghi tested commit/hash/worktree (có thể gồm probe/báo cáo review, không sửa implementation). Chỉ PostgreSQL17.11/Auth stub, DB test clean/legacy, toàn chuỗi migrations; không áp staging/production.

## NOT RUN

- HTTP/PostgREST/JWT thật, thiết bị/browser e2e; staging/production apply, nghiệm thu đồng thời A/B/C trên main.
- Runner BH02/BH03/BH04 riêng và lịch cạnh tranh DB mới ngoài runner BH05.
- Không thực hiện host revoke qua HTTP trong khi client đang refresh; probe kiểm UI onPressed dưới trạng thái loading có cache, không chứng minh exploit server.

## Kết luận

**Chưa đạt** phần C tại `48b4ad2` — còn C1-R mức P2 (tiếp nối C1). Reviewer tự chốt, không hỏi chủ dự án xác nhận. Không sửa code hoặc merge main. Bản sửa đang review là vòng sửa 1; phần còn lại cần test tái hiện trước khi sửa theo giới hạn tối đa hai vòng của quy trình.
