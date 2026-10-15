# Review độc lập BH-05C — 8974d3c

Ngày 16/10/2026 (Việt Nam). Nhánh feat/bh05c-ui, tested HEAD `8974d3cf317da00d86e7d3c169a13620bd0c8a49`. Theo docs/ai/REVIEWER.md tại chore/ai-roles (`163bc45`); đọc AGENTS/04/08 và BH05/R2/R7 tại 09. Không sửa code hoặc apply remote DB.

## Phạm vi

Diff `git diff origin/main...HEAD`, main remote da1285d, merge-base d8dfe74. Nhánh C kế thừa A/B đã review; tập trung màn chi tiết và widget test mới tại 8974d3c. Dù hai file UI trùng bản tham chiếu trên main, phần C vẫn phải được kiểm với provider B hiện tại; không dùng trùng file làm bằng chứng nghiệm thu.

## C1 — P2: UI bỏ qua loading/error lời mời đã có trong provider B

**File:dòng:** `lib/screens/session_detail_screen.dart:514-520`.

**Mô tả:** _PlayerRegistrationCard chỉ nhận myInvitation/submitting, không nhận isLoadingInvitation/invitationErrorMessage hoặc callback retry. Khi RPC lỗi, provider có error nhưng màn hình chỉ hiện waitlisted, giống không có lời mời; khi đang tải cũng không có chỉ báo. B1 đã sửa tầng state nhưng UI không sử dụng. Probe độc lập: authenticated waitlisted, repository ném offline; provider.invitationErrorMessage khác null, widget không hiển thị thông báo lỗi. Test FAIL.

**Cách sửa:** truyền/render state lời mời loading/error/empty, nút retry gọi fetchMyInvitation cho đúng session; khi lỗi không trình bày dữ liệu cũ như lời mời đã xác minh. Thêm widget test loading→error→retry→invitation/null hợp lệ.

## C2 — P2: buổi đầy chặn luôn đăng ký vào danh sách chờ

**File:dòng:** `lib/screens/session_detail_screen.dart:655-665`.

**Mô tả:** người đã đăng nhập chưa có registration gặp session.isFull thì chỉ thấy “Buổi đã đủ người”, không có đường gọi requestJoinSession. Hợp đồng request_join_session/R7 quy định auto_confirm khi đầy chuyển waitlisted, còn host_approval gửi pending không chiếm slot. UI dùng count để chặn trước khiến luồng waitlist không tiếp cận được qua màn này. Probe với public/published, capacity=1, confirmedCount=1, authenticated: không có nút đăng ký; test FAIL. Không tuyên bố DB vượt capacity; lỗi ở hành vi UI theo capacity.

**Cách sửa:** buổi còn mở đăng ký thì vẫn cho gửi yêu cầu vào waitlist/pending, có nhãn phù hợp; để RPC quyết định slot và trạng thái. Không dựa vào client count để thay quy tắc server. Bổ sung test full auto_confirm→waitlisted và pending không giữ chỗ, submitting/error/retry.

## C3 — P2: dialog thành viên dùng roster không đúng scope và không theo dõi tải

**File:dòng:** `lib/screens/session_detail_screen.dart:945-952`, `:988-991`, `:1034-1059`. Caller tương tác với `lib/providers/club_provider.dart:180-182` (code kế thừa).

**Mô tả:** khi mở chi tiết buổi CLB từ link hoặc danh sách buổi, ClubProvider chưa nhất thiết đã chọn CLB đó. Dialog gọi fetchMembers nhưng hàm trả ngay nếu _currentClubId không khớp. _clubProvider được gán sau frame mà không setState, không watch/listen provider; kết quả tải sau đó cũng không làm dropdown rebuild. Nếu cache CLB khác có sẵn, dialog còn dùng currentMembers không lọc scope và không fetch vì danh sách khác rỗng. Phần C cũng không hiển thị loading/error/retry roster; người dùng không thể chọn đúng member hoặc chọn nhầm rồi bị server từ chối.

Probe độc lập: ClubProvider mới, mở session có clubId=c1 rồi “Thêm người”, không mở màn CLB trước; dialog có hiển thị nhưng repository.listClubMembers(c1) không được gọi. Test FAIL. Chưa có runtime probe cache CLB khác, phần đó đối chiếu đường code.

**Cách sửa:** tải roster theo clubId của buổi bằng API có scope hợp lệ, không phụ thuộc CLB đang được màn khác chọn; subscribe/watch đúng dữ liệu và loading/error/empty. Không đưa roster CLB khác vào dropdown. Thêm test mở trực tiếp, response trễ/retry và chuyển giữa hai CLB. Không mở thêm quyền DB để chữa lỗi UI.

## Kết quả tự chạy

- Flutter3.47.7/Dart3.13.5: flutter analyze --no-pub → No issues found, exit 0.
- flutter test --no-pub → **123/123 PASS**, exit 0.
- BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh05/run_bh05_tests.py → **84/84 PASS**, exit 0, PostgreSQL17.11/Auth stub, clean/legacy toàn chuỗi migration. [JSON](bh05_test_results_20261015181849.json).
- Probe UI độc lập: **0 PASS/3 FAIL**, [log](review_8974d3c_probe_results.txt). Test tạm đã chuyển khỏi repo sang `/workspace/scratch/bh05c-review/review_bh05c_probe_test.dart`; không giữ thay đổi application/tests triển khai. Worktree metadata trong JSON có thể gồm probe/evidence review.

## NOT RUN

- HTTP/PostgREST/JWT thật, thiết bị thật/browser e2e, staging/production apply; không nghiệm thu toàn A/B/C trên main.
- Các runner BH02/BH03/BH04 riêng; không thêm lịch cạnh tranh DB ngoài runner BH05.
- Các nhánh UI khác chưa có probe bổ sung trong lượt này, gồm cache CLB khác và response roster trễ. Không suy từ 123 test PASS rằng đã bao phủ toàn bộ UI.

## Kết luận

**Chưa đạt** phần C tại `8974d3c`: C1/C2/C3 mức P2. Reviewer tự chốt và cập nhật trạng thái; không cần chủ dự án xác nhận. Không sửa code, merge main hoặc triển khai tiếp trong lượt này.
