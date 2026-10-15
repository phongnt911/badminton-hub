# Review độc lập BH-05B — 135d7bd

Ngày 16/10/2026 (Việt Nam). Nhánh feat/bh05b-data; tested HEAD `135d7bd`. Theo docs/ai/REVIEWER.md trên chore/ai-roles (`83877f7`), AGENTS/04/08 và BH05/R2/R7 ở 09. Không sửa code, không apply remote DB.

## Phạm vi

Diff `git diff origin/main...HEAD` (main remote `da1285d`, merge-base `d8dfe74`). Vì B tách từ A (`7bc4423`), diff bao gồm A đã review; lượt này tập trung phần B mới ở commit 135d7bd: model/repository/provider và test provider. Không lặp lại các lỗi A1–A3 đã đóng, không review UI phần C như code mới của B. Quy trình reviewer lấy từ chore/ai-roles vì chưa merge vào main/A/B.

## B1 — P2: lỗi tải lời mời bị nuốt và biến thành “không có lời mời”

**File:dòng:** `lib/providers/session_provider.dart:493-497`; thiếu trạng thái loading/error của lời mời trong hàm `fetchMyInvitation` tại `:478-498`.

**Mô tả:** catch mọi exception rồi gán myInvitation=null, không lưu lỗi hoặc truyền lên detailErrorMessage. get_my_waitlist_invitation trả null hợp lệ cũng tạo cùng trạng thái. Khi offline/RPC thiếu/quyền lỗi, UI phần C chỉ có null nên không thể phân biệt request thất bại với không có lời mời để hiển thị error+retry đúng yêu cầu 04 và hợp đồng 08 §7. Probe độc lập: repository ném offline khi người dùng waitlisted; sau fetchSessionDetail, detailErrorMessage và myInvitation đều null, không có invitation error/loading API khác; test kỳ vọng lỗi quan sát được FAIL.

**Cách sửa:** state lời mời có loading/error riêng hoặc truyền lỗi lên state lỗi phù hợp; chỉ coi response thành công null là empty, không nuốt exception. Cho retry qua fetchMyInvitation, giữ auth/session guard; thêm test loading→error→retry→empty/success. Không đòi UI C trong commit B, nhưng B phải cung cấp đủ state cho UI dùng.

## B2 — P2: refresh trạng thái đăng ký vẫn giữ lời mời cũ

**File:dòng:** `lib/providers/session_provider.dart:279-283` (nhánh refresh chỉ tải lời mời khi waitlisted), `:255-261` (chỉ xóa myInvitation khi đổi session ID).

**Mô tả:** cùng session: lần đầu waitlisted có invitation i1, lần sau RPC detail trả confirmed/cancelled/không có registration, provider bỏ qua fetchMyInvitation nhưng không xóa i1. _runPlayerMutation refresh bằng cùng session nên accept/cancel thành công cũng có thể để lại invitation pending cũ trong state. UI sẽ nhận dữ liệu đăng ký mới kèm lời mời không còn hợp lệ. Server vẫn chặn thao tác sai nên đây là lỗi state, không tuyên bố chiếm thêm slot. Probe độc lập refresh từ waitlisted+i1 sang session không có registration: kỳ vọng myInvitation=null nhưng thực tế vẫn WaitlistInvitation, test FAIL.

**Cách sửa:** xóa state invitation khi detail mới không còn điều kiện hiển thị lời mời; invalidate request lời mời cũ bằng serial/detail-generation để response trễ không khôi phục lại state đã xóa. Thêm test waitlisted→confirmed/cancelled, accept/cancel refresh và response lời mời cũ đến trễ.

## Kiểm thử độc lập

- Flutter 3.47.7/Dart3.13.5, `flutter analyze --no-pub`: No issues found, exit 0.
- `flutter test --no-pub`: **111/111 PASS**, exit 0.
- `BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh05/run_bh05_tests.py`: **84/84 PASS**, exit 0, PostgreSQL17.11/Auth stub trên clean/legacy, toàn chuỗi migrations. [JSON tự chạy](bh05_test_results_20261015175816.json).
- Hai probe độc lập cho B1/B2: **0 PASS/2 FAIL**, tái hiện như mô tả. [Log tóm tắt](review_135d7bd_probe_results.txt). Probe được đặt tạm dưới test/providers để chạy rồi chuyển sang `/workspace/scratch/bh05b-review/review_bh05b_probe_test.dart`; không giữ thay đổi application/test implementation trong repo.
- Metadata worktree_dirty trong JSON có thể gồm file probe tạm/bằng chứng review, không phải sửa mã triển khai. Tested application code vẫn là 135d7bd.

## NOT RUN

- Supabase HTTP/PostgREST/JWT thật, thiết bị/browser e2e, staging/production apply.
- Review/nghiệm thu UI phần C; unit test hiện có phần B chủ yếu mock repository, không chứng minh HTTP RPC wiring thực tế.
- Không chạy lại riêng runner BH02/BH03/BH04; runner BH05 áp toàn chuỗi migration không thay cho mọi suite hồi quy cũ.
- Không thêm concurrency DB mới trong lượt B; dùng các ca hai kết nối của runner A. Chưa thực nghiệm response lời mời trễ sau refresh, chỉ nêu guard cần có khi sửa B2.

## Kết luận

**Chưa đạt** phần B tại `135d7bd` — còn B1 và B2 mức P2. Báo cáo được push lên nhánh review theo yêu cầu thường trực; chưa sửa code, chưa đổi trạng thái ticket thành Đạt, chưa merge main. Reviewer chốt kết luận cuối cùng **Chưa đạt** phần B tại 135d7bd; không cần chủ dự án xác nhận. Người triển khai xử lý B1/B2 trước khi gửi review lại.
