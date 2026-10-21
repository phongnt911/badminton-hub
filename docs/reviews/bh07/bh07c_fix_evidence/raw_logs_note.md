# Ghi chú bổ sung bảy log gốc

Ngày 21/10/2026. Theo [review 02a9b85](../review_02a9b85.md), bảy log gốc của tác giả được liệt kê trong manifest nhưng không có trên nhánh. Nguyên nhân: `.gitignore` dòng 3 bỏ qua `*.log`, nên commit `f63e5a4` chỉ đưa lên các file exit/manifest.

Bảy file dưới đây vẫn còn nguyên trong working tree, không được chạy lại hoặc tạo lại. Đã kiểm tra SHA-256 khớp đúng `sha256.txt` hiện có trước khi force-add, rồi force-add nguyên bytes. Không sửa code/test.

| Log | Bytes | SHA-256 |
|---|---:|---|
| `red_targeted.log` | 20176 | `b70f63b4e5242eb322e396a476f24445be339ba007b3f3d3d6fa6a2bbe14b0e6` |
| `flutter_analyze.log` | 198 | `ad05d978ab1854a7d1fba36eb70322ac0fb687fcd7cf956f56bf71e106c724f5` |
| `flutter_test.log` | 77436 | `d8fd6f4f84b9c22dad3b5903d2640e79210f9104d8428e96c9b9c51797d3095a` |
| `targeted_utc.log` | 19704 | `cf3eefe34dc6fa9bbaa1bf9179c2c99464deffc83d2c8dd748362355972e931f` |
| `targeted_vietnam.log` | 19794 | `e2b11dc5c7dd07d2b61ac53996605bbfa36103db5b8798d5bb6d2cb932a513a2` |
| `bh07_db_runner.log` | 6342 | `a71741baa4ecffd31cf3536e8f2779a0d95fd3d930aa04e93c36455852e419f7` |
| `diff_check.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

`diff_check.log` rỗng là đúng: `git diff --check` không có output, exit 0 (`diff_check_exit.txt`).

Các log này là bằng chứng lịch sử của lần chạy trên code `02a9b85`; không phải lần chạy mới. Review độc lập `review_02a9b85.md` vẫn là kết luận hiện hành, dựa trên lần reviewer tự chạy. Code không đổi.
