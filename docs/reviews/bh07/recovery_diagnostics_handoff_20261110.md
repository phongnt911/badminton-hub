# Bàn giao chẩn đoán khôi phục V4 & sửa harness V5b (Tasks 1+2, Sửa vòng 2/3) — 10/11/2026

**Trạng thái:** Chờ Codex review độc lập vòng 2/3 sau khi khắc phục triệt để RD3 (type-guard edge) và RD4 (ghi chú không tương thích probe lịch sử) theo [recovery_diagnostics_review_after_r1_20261110.md](recovery_diagnostics_review_after_r1_20261110.md).
**Phạm vi:** Hoàn thành sửa đổi hẹp bằng công cụ file (no shell / no subagents / no runtime execution). Không sửa app, backend, database schema, migration, hoặc can thiệp bằng chứng/báo cáo lịch sử. Task 3 (sửa lỗi recovery cụ thể) chờ kết quả chẩn đoán runtime từ Codex sau khi hoàn tất nghiệm thu tooling Tasks 1+2.

---

## 1. Rationale & Chi tiết sửa đổi sau Review After-R1 (RD3 & RD4)

### Khắc phục RD3 (P2): Bổ sung String Type-Guard trước mọi phép kiểm tra Set/Whitelist Membership
- **Vấn đề:** Trong Python, phép thử `val in some_set` với `val` là kiểu không băm được (unhashable) như `list` hoặc `dict` sẽ lập tức ném ngoại lệ `TypeError: unhashable type: 'list'`.
  - Tại resolver [`resolve_safe_operation`](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py#L272) và [`set_stage`](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py#L310), truyền `[]` hoặc `{}` gây `TypeError` thay vì fallback an toàn hoặc ném `ValueError`.
  - Tại publication sink trong [`runner.main()`](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py#L1747), nếu ngoại lệ mang `err.operation = []` hoặc `current_stage = []`, error handler bị vỡ bởi `TypeError` trước khi kịp ghi nhận `summary['status'] = 'FAIL'`.
  - Tại metadata validator [`validate_v4_rehearsal`](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py#L845), việc kiểm tra membership của `op` và `stg` thiếu type-guard gây crash validator; đồng thời alias `failed_operation` nếu mang kiểu non-dict (như `list` hay `str`) trước đó bị bỏ qua trong im lặng.
- **Khắc phục:**
  1. **Resolver & Helper:**
     - `resolve_safe_operation`: Thêm type-guard `isinstance(op, str) and op in SAFE_OPERATIONS_WHITELIST`. Mọi kiểu unhashable/non-string đều rơi vào nhánh an toàn trả về `OP_DOCKER_GENERIC`.
     - `set_stage`: Kiểm tra `not isinstance(stage, str) or stage not in PREDEFINED_STAGES`, ném `ValueError` an toàn, không bao giờ để lọt `TypeError`.
  2. **Publication Sink:**
     - `safe_op = raw_op if (isinstance(raw_op, str) and raw_op in SAFE_OPERATIONS_WHITELIST) else None`.
     - `if isinstance(current_stage, str) and current_stage in PREDEFINED_STAGES:` bảo vệ cả phép thử `in` lẫn tra cứu dictionary `STAGE_DEFAULT_ERROR_LABELS.get(current_stage)`.
  3. **Metadata Validator (`validate_v4_rehearsal`):**
     - `command_failure`: Thêm `not isinstance(op, str) or op not in SAFE_OPERATIONS_WHITELIST` tạo finding `unwhitelisted_operation` thay vì crash.
     - `failed_operation`: Nếu khác `None`, bắt buộc kiểm tra `if not isinstance(failed_op, dict): findings.append('invalid_failed_operation: failed_operation must be dict')`. Nếu là dict, áp dụng type-guard chuỗi cho `operation`.
     - `stage` & `diagnostics.stage`: Thêm type-guard `not isinstance(stg, str) or stg not in PREDEFINED_STAGES` tạo finding `unrecognized_stage`.
     - `diagnostics.failed_operation`: Type-guard chuỗi chống unhashable.
     - `actors`: Thêm `not isinstance(actor_name, str) or actor_name not in FINANCE_AUTHORIZED_ROLES`.
  4. **Test Suite:**
     - Mở rộng `test_safe_operation_whitelist_rejects_arbitrary_user_text` kiểm tra `resolve_safe_operation` và `set_stage` với các kiểu unhashable `([], {}, set(), [1, 2])`.
     - Thêm `test_publication_sink_rejects_unhashable_and_malformed_metadata_vectors`: kiểm chứng publication sink tiếp nhận `err.operation = []` và `err.exit_code = {}` mà không ném `TypeError`, kết luận đúng status `FAIL`, stage `target_auth_start`, và fallback nhãn an toàn tiền định.
     - Thêm `test_validator_rejects_unhashable_and_malformed_metadata_vectors`: kiểm chứng validator bắt đúng các finding `unwhitelisted_operation`, `invalid_exit_code`, `invalid_failed_operation`, `unrecognized_stage` đối với các vector metadata unhashable / non-dict.

---

## 2. Khắc phục RD4 (P2): Xác định rõ tính không tương thích của Probe lịch sử V5b

- **Vấn đề thực tế:**
  - Probe lịch sử [v5b_temp_path_probe.py](codex_observer_cleanup_evidence/v5b_temp_path_probe.py) ghi đè hàm tạo `TemporaryDirectory` bằng cách ép cứng đối số từ khóa `prefix='v5b-db-'`.
  - Trong test harness mới, [`test_r1_owned_inventory_must_succeed_before_reset`](../../../tests/test_v5b_runner_flaws.py#L271) đã được tham số hóa và chủ động truyền `tempfile.TemporaryDirectory(prefix=prefix)` qua 4 loại tiền tố (`neutral-`, `v5b-db-`, `v5b-reset-`, `v5b-db-reset-`).
  - Do đó, khi chạy probe cũ trực tiếp trên harness mới, Python ném `TypeError: tempfile.TemporaryDirectory() got multiple values for keyword argument 'prefix'` trên cả 16 subtest (16 errors, không phải assertion failures).
- **Kết luận & Hướng dẫn kiểm chứng:**
  - **Giữ nguyên vẹn byte file lịch sử:** Tuyệt đối không sửa file [v5b_temp_path_probe.py](codex_observer_cleanup_evidence/v5b_temp_path_probe.py) thuộc bằng chứng lịch sử.
  - **Không khẳng định probe cũ replay PASS:** Probe cũ chính thức **KHÔNG TƯƠNG THÍCH** với test harness mới vì xung đột duplicate keyword argument `prefix`.
  - **Kiểm chứng thay thế chuẩn xác:** Kiểm chứng tính đúng đắn của token check V5b qua **16 controls mới** trong `tests/test_v5b_runner_flaws.py` (đã bao hàm đầy đủ kịch bản `v5b-db-` mà probe lịch sử từng kiểm tra), hoặc một probe thích ứng mới chỉ truyền prefix một lần. (Codex đã chạy và xác nhận 22/22 PASS).

---

## 3. Danh sách file thuộc quyền sở hữu & thay đổi

| File | Hành động | Trọng tâm sửa đổi vòng 2/3 |
|---|---|---|
| [scripts/bh07_backup/run_v4_concurrent_rehearsal.py](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py) | Sửa đổi | Bổ sung string type-guard ở resolver, set_stage, publication sink, và metadata validator; từ chối non-dict `failed_operation` |
| [tests/test_bh07_v4_runtime_collection.py](../../../tests/test_bh07_v4_runtime_collection.py) | Sửa đổi | Thêm 2 test methods và mở rộng test unhashable/malformed vectors cho sink và validator |
| [tests/test_v5b_runner_flaws.py](../../../tests/test_v5b_runner_flaws.py) | Giữ nguyên | 22/22 PASS (16 controls path/inventory & unit test token) |
| [docs/reviews/bh07/recovery_diagnostics_handoff_20261110.md](recovery_diagnostics_handoff_20261110.md) | Cập nhật | Bổ sung chi tiết RD3 type-guard và đính chính rõ ràng tính không tương thích của probe lịch sử theo RD4 |

---

## 4. Lệnh khuyến nghị Codex thực hiện kiểm chứng

Codex thực hiện kiểm chứng độc lập theo thứ tự ưu tiên:

```powershell
# 1. Chạy reviewer synthetic controls R1 (kỳ vọng 4 booleans false, stages khớp)
python .build/recovery-diagnostics-r1-controls.py

# 2. Chạy targeted test suite V4 runtime collection (kỳ vọng 52/52 PASS, bao gồm 2 test unhashable vector mới)
python -m unittest tests.test_bh07_v4_runtime_collection -v

# 3. Chạy targeted test suite V5b runner flaws (kỳ vọng 22/22 PASS, 16 subtests bao hàm v5b-db-)
python -m unittest tests.test_v5b_runner_flaws -v

# 4. Chạy kiểm tra hợp đồng V4 concurrency
python -m unittest tests.test_bh07_v4_backup_concurrency -v
```

> [!NOTE]
> Không chạy `python docs/reviews/bh07/codex_observer_cleanup_evidence/v5b_temp_path_probe.py` vì probe này truyền lặp đối số `prefix` với harness mới (TypeError 16 errors). 16 subtests trong `tests/test_v5b_runner_flaws.py` là kiểm chứng chính thức thay thế.

---

## 5. Giới hạn & Bước tiếp theo

1. **Giới hạn triển khai:** Theo quy định ủy quyền, Anti CLI chỉ sử dụng file tools, không gọi shell/subagent/runtime/Docker.
2. **Không nới lỏng gate:** Toàn bộ gate kiểm định logic concurrency, relational integrity, padding digest và fail-closed cleanup giữ nguyên vẹn.
3. **Bước kế tiếp:** Khi Codex review nghiệm thu hoàn tất Tasks 1+2, Codex thực hiện 1 lần chạy rehearsal Docker cô lập để thu thập receipt với stage cụ thể, chuẩn bị cơ sở cho Task 3.
4. **Trạng thái nghiệm thu:** Toàn bộ BH-07/V8 vẫn **CHƯA NGHIỆM THU**. Không tự ý merge, push, deploy, pilot hoặc ký risk acceptance thay chủ dự án.
