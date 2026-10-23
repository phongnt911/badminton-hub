# Review BH-07 — 6d00e9c cleanup R1

- Base: `ec0784f359ed877177330c59dbf40e0ce384ecbf`.
- Tested source: `6d00e9cea29c29a2b57d3291fb92be7600110f98`.
- Docs/evidence và checkout reviewer: `0d4f9c0f4fbf2c1e4a33e28eda81bf73c3f6895c`.
- Reviewer Codex tự chạy lại, không sửa source bản fix của người triển khai. Codex từng viết baseline b626a78; đây là review bản sửa của AI triển khai khác, không tuyên bố độc lập với toàn bộ lịch sử tác giả.
- Linux/Docker tại `/workspace/badminton-hub`, khác môi trường Windows của tác giả. Flutter3.47.7, PostgreSQL17.11, GoTrue2.197.0, PostgREST16.4, Kong2.8.1.
- Checkout sạch trước chạy. Tree `scripts/bh07_backup` tại source và docs commit giống nhau (`b48f366c8df8e7a9dad802a0d93b33818fe3c2fa`); source không bị thay trong review. JSON runner tự ghi HEAD docs0d4f9c0, không mạo nhận chạy checkout6d00e9c.

**Kết luận: Chưa đạt bản sửa R1.** Không đóng backup/restore hoặc chuyển bước kế; browser đã đóng giữ nguyên. Không merge main/deploy/pilot.

## Phát hiện

### R1 — P2: Inspect lỗi Docker context bị coi nhầm là resource đã biến mất

- File:dòng: `scripts/bh07_backup/run_local_rehearsal.py:294`, `:302`, `:307`.
- Lệnh tái hiện lỗi Docker thật (không thay context mặc định, không tạo resource): `DOCKER_CONTEXT=bh07-review-missing-context docker inspect synthetic-container` (PowerShell dùng `$env:DOCKER_CONTEXT` trong process riêng). Docker trả exit1: `Failed to initialize: unable to resolve docker endpoint: context ...: context not found: open .../meta.json: no such file or directory`.
- Probe reviewer: `python docs/reviews/bh07/review_6d00e9c_evidence/inspect_probe.py`. Probe lấy nguyên finally/return bằng loader AST của `scripts/bh07_backup/cleanup_probe.py`, dùng stderr thật trên và Docker stub có resource synthetic đang tồn tại; không copy predicate hay sửa source. Có positive cleanup bình thường và control lỗi daemon không chứa `not found`.
- Kỳ vọng: lỗi context/daemon/transport/permission hoặc bất kỳ inspect thất bại không chứng minh đúng resource vắng mặt phải được ghi cleanup error, status FAIL/exit khác0. Không tuyên bố resource đã dọn. Tiếp tục dọn các resource khác và private path, giữ lỗi chạy chính.
- Thực tế: substring `not found` nhận mọi stderr loại này là False (resource vắng). Hai resource synthetic còn nguyên, `rm_calls=[]`, network còn, nhưng summary PASS, `cleanup_failed=false`, `cleanup_errors=[]`, exit0. Positive baseline đúng; lỗi daemon thông thường được chặn, nhưng lỗi context thật lọt. Probe exit0 nghĩa là tái hiện đúng lỗi, không phải runner PASS hợp lệ.
- Ảnh hưởng: mất khả năng truy cập Docker context trong cleanup có thể giữ container/volume/network mà vẫn báo thành công; yêu cầu R1 chưa được giải quyết triệt để. Luồng chạy thật bình thường đã dọn sạch; chưa quan sát resource thật bị bỏ lại.
- Cách sửa: phân biệt lỗi kiểm tra với bằng chứng vắng mặt; chỉ chấp nhận thông báo absence đúng kind/tên resource từ daemon hoặc kết quả liệt kê thành công xác nhận absence. Không dùng substring `not found` chung. Thêm negative controls dùng stderr context thật, daemon/permission/transport, lỗi ở inspect trước và sau remove, network remove failure, remove trả0 nhưng resource vẫn còn; giữ5 control cũ, giữ lỗi chính và cleanup tiếp tục. Không xóa tài nguyên ngoài sở hữu; không log raw error chứa credential. Phát lại probe reviewer giữ nguyên kỳ vọng.
- Trạng thái: **FAIL. R1 vẫn mở; cần AI triển khai sửa vòng2/2.**

### P0/P1

Không phát hiện trong phạm vi bản sửa đã kiểm; không suy sang nghiệm thu toàn BH-07.

## Kiểm chứng tự chạy

| Kiểm tra | Exit | Kết quả |
|---|---|---|
| `python scripts/bh07_backup/cleanup_probe.py` |0|5/5 ok=true; không bao phủ inspect context lỗi|
| Probe reviewer cũ, file giữ nguyên |1|Dừng ở positive vì Docker stub cũ trả0 cho mọi lệnh nhưng không mô phỏng inspect/absence. Không phải bằng chứng regression; không sửa kỳ vọng/file cũ. Dùng probe mới với stateful stub + AST hiện tại để đối chiếu|
| Rehearsal output mới ngoài repo |0|13/13, dirty_before_run rỗng, private removed=true, cleanup_errors=[], cleanup_failed=false|
| Docker state sau rehearsal |0|Không còn source/target container và network; không còn `/tmp/bh07-backup-*`|
| `flutter analyze` |0|0 issue|
| `flutter test` |0|240 PASS +1 skip|
| BH-07 DB trên container reviewer riêng |0|23/23 PASS, JSON dirty=false, HEAD0d4f9c0; Auth stub, không thay bằng chứng HTTP|
| Manifest tác giả `--verify` |0|18/18, UTF8/LF,0 secret/JWT ngoài allowlist, hash toàn thư mục trước/sau không đổi|
| Probe inspect bổ sung |0|1 positive +1 daemon control đúng,1 context error tái hiện false success|

`git diff ec0784f..6d00e9c -- lib test supabase` rỗng; evidence cũ `backup_restore_evidence` và `review_b626a78_evidence` không đổi; `git diff --check` worktree sạch trước review. Docs commit chỉ docs/evidence/trạng thái. Lần tác giả thất bại tại2c6225f có log/summary riêng, status FAIL/exit1,5 check PASS, dirty rỗng; source này tồn tại trong lịch sử rồi mới6d00e9c. Không thấy mâu thuẫn provenance trong phần kiểm được; không thể chứng minh từ xa mọi sự kiện máy Windows. Giữ các log thất bại, không thay chúng bằng lần xanh.

Bằng chứng lượt này ở `review_6d00e9c_evidence/`; không ghi đè evidence tác giả. Chỉ tạo report/probe reviewer/docs trạng thái, không sửa script triển khai/app/unit/migration/RPC/contract.

## NOT RUN

Managed Supabase backup/PITR/offsite/encryption/retention; concurrent writers; staging/production/restore thật; browser/device/offline/deep link; banking/webhook; rehearsal tải thật/pilot và nghiệm thu toàn BH-07. Không gây mất context thật giữa một live rehearsal (fault injection dùng AST hiện tại với stderr Docker thật, tài nguyên synthetic); không thử permission fault thật trên archive/secret. BH-02..06 đầy đủ không chạy lại vì app/backend không đổi.

**Chưa đạt — sửa R1 vòng2/2 trước khi reviewer chốt.**
