# Chẩn đoán recovery Auth SITE_URL — 10/11/2026

**V4 vẫn FAIL; đã định vị nguyên nhân, chưa sửa/nhận runtime mới.** Source `791bcf7`, checkpoint diagnostics/harness đã Đạt review delta, full552test/548PASS+4SKIP. Owner đang giao tiếp tục Anti→review3→Codex tự sửa; không waiver FAIL hoặc tự nghiệm thu V8.

## Runtime runner không sửa

Output `.build/bh07-v4-recovery-diagnostic-791bcf7`, run `0031d57d`: FAIL tại `stage:port_discovery`, `command_failure.operation:target_port_discovery`, exit1, elapsed117.75s. Cleanup8/8 owned resources/private dumps được xác minh. Việc quan sát target Auth đang running ở một thời điểm không chứng minh service đã healthy hoặc không thoát sau đó.

## Probe và wrapper chẩn đoán

Probe Docker riêng dùng3container sleep của image đã cache,1internal network có label sở hữu, không khởi tạo DB: dynamic-internal-first, static-internal-first và dynamic-bridge-first đều trả port exit0/mapping127.0.0.1. Cleanup label-verified sạch. Kết quả không ủng hộ giả thuyết dynamic mapping hỏng chỉ do network internal.

Sau đó Codex chạy wrapper `.build/diagnose_v4_recovery_ports.py` quanh cùng runner. Wrapper gọi nguyên `cmd`, chỉ khi Docker port thất bại mới inspect state và phân loại log theo khóa/chuỗi tiền định, rồi ném lại exception gốc. Không thay success result, HTTP workload, snapshot/overlap gate hoặc cleanup. Không công bố raw log/env/args/credential. Đây là **lượt diagnostic wrapper**, không gọi là runtime acceptance của source không sửa.

Wrapper SHA-256 `915b8ab2d8a2d828cedab5d27e7448f716a2a81803b85bb54a593d250b94931c`. Output runner `.build/bh07-v4-recovery-port-diagnosis`, run `faf0482c`, FAIL cùng port stage, elapsed88.984s. Metadata `.build/v4-recovery-port-failure-metadata.json` SHA-256 `3f0b5b632be49afd2a10d40a50e096eb6065427542a78cb120acb95fafc47478`:

- Service thất bại: target_auth.
- Inspect exit0, container status exited, exit_code1, running false, OOM false.
- configuration_load_failed true; missing_configuration_keys chỉ có SITE_URL.
- database_authentication_failed false và database_connection_failed false theo các mẫu chẩn đoán đã kiểm (không chứng minh mọi dạng lỗi DB không tồn tại).
- Cleanup runner8/8 owned resources absent và private dumps removed true.

## Cơ sở sửa tối thiểu

Target Auth env thiếu `GOTRUE_SITE_URL`, trong khi source stack đã khai báo loopback site URL. [Source chính thống Auth v2.197.0](https://raw.githubusercontent.com/supabase/auth/v2.197.0/internal/conf/configuration.go) khai SiteURL required. Đã kiểm [changelog](https://supabase.com/changelog); không nâng client/library hoặc đổi pinned image trong nhiệm vụ này. Fetch changelog.md không đọc được do content-type, dùng trang changelog HTML thay thế.

Giao Task3 cho Anti thêm SITE_URL loopback không rỗng trong env recovery, viết test đi qua main bắt env file tại Docker run boundary. Không thêm arbitrary waits/retries để che service chết, không nới gate và không thay DTO/RPC/schema/seed. Stage diagnostics và CW5 cleanup phải giữ nguyên. Chỉ runtime source sạch tiếp theo mới xác nhận final login/replay/oracle/cleanup PASS.

## Evidence được giữ nguyên byte

- [Summary runner thường](v4_runtime_20261110_evidence/791bcf7_diagnostic_summary.json).
- [Summary lượt wrapper](v4_runtime_20261110_evidence/791bcf7_wrapped_summary.json).
- [Safe failure metadata](v4_runtime_20261110_evidence/791bcf7_port_failure_metadata.json).
- [Wrapper source đúng bytes đã chạy](v4_runtime_20261110_evidence/791bcf7_diagnostic_wrapper.py).
- [Port probe kết quả](v4_runtime_20261110_evidence/791bcf7_port_probe.json) và [source](v4_runtime_20261110_evidence/791bcf7_port_probe.py).

Các script này là artifact chẩn đoán Windows, không phải runner production hay chứng nhận runtime không wrapper. Nếu cần phát lại phải đặt lại đúng vị trí `.build/` và kiểm môi trường/owned resource mới; không chạy từ thư mục evidence hoặc dùng lại tài nguyên/process cũ. Metadata hash và wrapper hash ở trên được đối chiếu sau copy, giữ nguyên. Không lưu raw logs/secret vào evidence.
