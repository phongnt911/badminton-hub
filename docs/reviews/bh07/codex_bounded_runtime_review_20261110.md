# Runtime Codex bounded COPY — 10/11/2026

**Toàn lượt FAIL, exit1; không nghiệm thu V4/BH-07/V8.** Hai P2 CW5/CW4 đã được sửa/review source riêng; kết quả runtime dưới đây không nâng thành full PASS. Codex chạy Docker thật source `46c9d98`, git_dirty false, run `180f1ea2`, elapsed121.015s. Đây là runtime Codex, không phải reviewer tự chạy Docker.

## Bằng chứng đo được

[Summary nguyên byte](v4_runtime_20261110_evidence/codex_bounded_summary.json), SHA-256 `b5aff80050d18ab87eaa216d6a7f4edddae63c5a8edab427e6d1c3add1087b7f`.

- Snapshot export giữ mở, pg_dump exit0; dump lifetime `1794299759.868991`–`1794299767.282839` (~7.414s).
- Writer A200 `1794299760.1501656`–`1794299760.2316463`; B200 `1794299760.1506798`–`1794299760.1978142`. Cả hai HTTP call nằm trọn trong lifetime dump.
- Selected backend496 COPY `tooling_rehearsal.rehearsal_padding` sample `1794299760.1506798`–`1794299760.1564305` (~5.751ms), nằm trọn trong giao HTTP thật; `overlap_verified:true`. Đây là overlap có đo, không dựng receipt hoặc nới gate.
- Có [source fingerprints](v4_runtime_20261110_evidence/codex_bounded_source_fingerprints.json) và [restored fingerprints](v4_runtime_20261110_evidence/codex_bounded_restored_fingerprints.json). File target ghi1payment/1ledger/1audit/1request. Padding260.000 dòng/257.920.000 byte, digest `0ba98c3dc484e3fefba82f7dd034dc06`, `restored_match:true` sau query đối chiếu thực.

## Phần chưa hoàn tất

Sau khi main đã ghi restored fingerprints và xác minh padding, một lệnh Docker tiếp theo trả1; lỗi công bố chỉ là `RuntimeError: docker exited 1`. Vùng code tiếp theo dựng target Auth/PostgREST, nối bridge, tìm host port, login và replay. Artifact không ghim command/stage cụ thể nên nguyên nhân chính xác **UNKNOWN**; không suy ra config Auth sai hoặc lỗi database.

`restored_verification` còn rỗng và `execution_completed` chưa được bật. Vì vậy chưa có final receipt/oracle/replay verdict; số dòng target và padding match không đủ tuyên bố toàn restore/recovery PASS. Full runtime vẫn FAIL theo validator. Bước tiếp nếu tiếp tục rehearsal là thêm stage/command identity an toàn để chẩn đoán lỗi sau restore; không log JWT/env/dump/stderr chưa lọc.

Cleanup receipt ok true,7 container+1network verified absent, private dumps removed true. Codex kiểm inventory riêng sau runtime: không có container, networks chỉ bridge/host/none. Image cache giữ lại; không prune hoặc tác động DB khác.

Reviewer subagent riêng chỉ đọc artifact, xác nhận provenance clean source, overlap đúng bounds, source counts3:3:3:3/target1:1:1:1, padding match và cleanup8/8. Reviewer nhấn mạnh counts chưa chứng minh final identities/relations/replay invariant; không nhận review artifact này là một lần chạy Docker độc lập.

## Kiểm chứng source và giới hạn

Trên source trước đổi config `2bc90b2`: full Python541test/537PASS+4SKIP exit0, reviewer42test PASS. Trên source config `46c9d98`:42runtime-collection và49controls PASS, reviewer42test PASS. Full541test chạy đồng thời Docker có1FAIL trong test V5b `test_r1_owned_inventory_must_succeed_before_reset` (subtest inventory rỗng),156.305s; full serial chạy lại cũng1FAIL ở subtest partial-owned-id,138.272s. Cả hai lần là **536PASS+1FAIL+4SKIP**, exit1. Không ghi full suite candidate mới PASS. Chạy riêng test đó PASS.

Codex kiểm thêm classifier tại `tests/test_v5b_runner_flaws.py:284,323`: tìm substring `db` và `reset` ở bất kỳ argument, nên workdir có `db` nằm trong đường dẫn `/bh07-reset-verify` cũng bị nhận là reset trước inventory gate. [Probe độc lập](codex_observer_cleanup_evidence/v5b_temp_path_probe.py) chỉ ép prefix thư mục tạm `v5b-db-`, không sửa source test: tái hiện3subtest sai `True != False`,0error; không gọi Docker/reset thật. Đây là lỗi harness có thể tái hiện, không kết luận runner V5b thật reset DB sai. Không sửa V5b ngoài phạm vi. Log `.build/v4-codex-padding-full-python.log`, `.build/v4-codex-padding-v5b-isolated.log`, `.build/v4-codex-padding-full-python-serial.log` đều giữ nguyên.

Flutter mới NOT RUN, app/schema không đổi. Không merge/deploy/pilot/BH-08 hoặc ký risk acceptance thay owner. Giữ bằng chứng FAIL trước đó nguyên byte.
