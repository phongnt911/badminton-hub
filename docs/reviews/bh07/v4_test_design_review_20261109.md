# BH-07 V4 — review giới hạn thiết kế test/probe ngày 09/11/2026

Phạm vi: đọc `tests/test_bh07_v4_backup_concurrency.py` (458 dòng) và `scripts/bh07_backup/v4_concurrent_probe.py` (156 dòng) đang untracked trên nhánh `feat/bh07-completion-local`, HEAD `b72c563d9e519986dbd88ec98bcc3f015a41a442`. Anti đang sửa runner; **không đọc runner qua đường khác, không import hoặc chạy test/probe/runtime trong lượt này**. Các phát hiện dưới đây là lỗ hổng contract/coverage của test hiện có, chưa phải bằng chứng validator thực tế trả false PASS hoặc lỗi dữ liệu runtime.

## Phát hiện cần bổ sung control

### V4-T1 — P2: positive contract không bắt buộc fingerprint hợp lệ

- File:dòng: `scripts/bh07_backup/v4_concurrent_probe.py:99`, `:131`; `tests/test_bh07_v4_backup_concurrency.py:175–197`, `:367–374`.
- Probe gọi `validate_v4_rehearsal(canonical)` không truyền cả source/restored fingerprints và đòi PASS. Unit positive còn đặt hash `g`×64 và `h`×64 ở dòng 184–185, không phải SHA-256 hex, nhưng cũng đòi PASS. Negative duy nhất về fingerprint đổi `restored.payments.rows` từ 1 thành 2.
- Một validator bỏ qua hash, không yêu cầu fingerprint hoặc không kiểm source rows vẫn đáp ứng những kỳ vọng này. Không có đối chiếu dữ liệu snapshot mong đợi hoặc fingerprint trước/sau replay trong fixture hiện tại.
- Bổ sung RED controls cho thiếu từng fingerprint/table/hash, hash sai định dạng/nội dung, source thiếu một payment nhưng summary vẫn thành công, và replay đổi dữ liệu/hash trong khi row count không tăng. Positive phải dùng hash hợp lệ từ canonical data thực và ràng buộc rõ expected snapshot khác source hậu ghi như thế nào; không so source sau writer với restore một cách máy móc.

### V4-T2 — P2: relational/replay controls chỉ đổi flag hoặc cardinality

- File:dòng: `tests/test_bh07_v4_backup_concurrency.py:122–162`, `:320–365`, `:376–403`; probe `:61–80`, `:116–122`.
- Positive chỉ có operation IDs/amounts và các danh sách restored IDs, booleans `p0_present_in_restore`, `exact_cardinality_match`, `replay_p0_idempotent`. Không có payment row/amount trong restore, `club_transactions.source_payment_id`, audit `entity_id/request_id/actor`, operation result liên kết hoặc replay response IDs/row hashes để một oracle độc lập tính lại quan hệ. Các mutant hiện tại chỉ đổi presence flag, count hoặc amount sang string.
- Vì vậy coverage không phân biệt một payment đúng tiền với một payment sai **giá trị số nguyên**, một ledger gắn nhầm payment, audit/request sai liên kết hoặc replay trả ID khác nhưng vẫn không tăng count. Fixture còn thiếu bằng chứng FK/unique thực tế mà docstring tuyên bố.
- Bổ sung controls giữ nguyên mọi booleans/count nhưng thay restored payment ID bằng ID late writer; sai amount/actor/ledger source/audit entity/request/result; trùng IDs giữa hai operation; amount âm/0/bool; replay đổi payment/ledger ID hoặc hash với growth=0. Cần thêm receipt liên kết/row data tối thiểu hoặc expected hashes có provenance để kiểm các control đó, không chỉ thêm một boolean “relations_ok”.

### V4-T3 — P2: cleanup positive cho phép bỏ tài nguyên khỏi danh sách kiểm

- File:dòng: `scripts/bh07_backup/v4_concurrent_probe.py:82–100`; unit `:164–170`, `:407–424`.
- Probe positive có `networks_verified_absent=True` nhưng `resources_verified_absent` chỉ liệt kê hai DB container, không có network. Unit negative chỉ kiểm danh sách rỗng hoặc `ok=False`; không có manifest tài nguyên sở hữu làm expected set.
- Danh sách không rỗng không chứng minh đã kiểm hết DB/Auth/REST/gateway/network hay private files của lượt chạy; một tài nguyên bị quên có thể không làm bộ control đỏ.
- Positive cần danh sách expected owned resources riêng, phân loại container/network/private file và receipt inspection cho từng mục. Thêm mutant bỏ đúng một tài nguyên nhưng giữ flags True, chỉ giữ một tên tùy ý, thay tên/kind/run ID, duplicate receipt, inspect lỗi hoặc remove thành công nhưng vẫn present. Chỉ kiểm tài nguyên thật sự sở hữu; không suy rằng mọi stack đều phải có cùng số lượng cố định.

### V4-T4 — P2: barrier control chưa kiểm chứng DB execution overlap

- File:dòng: unit `:110–120`, `:439–454`; probe `:49–59`, `:139–147`.
- Positive overlap là các timestamp/flags tự gán; barrier test gọi `notify_dump_started` rồi xác nhận `is_dump_active=True`, không có receipt của DB backend. Không có negative giữ flags True nhưng writer requests chỉ được schedule, quan sát dump thuộc PID/lượt khác, hoặc hai writer không thực sự chồng lấn nhau dù mỗi writer có một phần giao với dump.
- Cần test quyết định từ observation records của backend/query/session đúng lượt, snapshot đúng, cả hai writer thực thi trong khoảng dump còn hoạt động. Bổ sung missing/wrong PID/query/run/snapshot, worker timeout/exception, dump kết thúc trước commit, writer A/B không giao nhau; kiểm wait timeout và không cho local `notify` thay DB observation. Đây là yêu cầu bổ sung test cho bằng chứng overlap, không kết luận runner hiện có hay không có cơ chế quan sát đúng.

## Phạm vi kết luận và NOT RUN

Đã đọc source test/probe bằng `ctx_read` và đối chiếu các nhánh mutant hiện có; `git status --short` xác nhận chúng chưa commit. Không xem/import runner bị gateway giữ lại, không né kiểm soát admission, không chạy controls hoặc tạo DB/browser/Docker mới. Không sửa file của Anti hay report V8 đã chốt.

**Chưa đủ coverage để dùng test/probe này làm bằng chứng chốt V4.** Giao bốn nhóm control trên cho lượt triển khai/review đầy đủ; root cần kiểm runner thực và chạy từng mutant trước khi quyết định phát hiện fail-open nào thực sự mở ở implementation. Không chốt verdict runtime V4/toàn BH-07 trong báo cáo này.

## Bổ sung 09/11/2026 — đối chiếu review chức năng R1 và khả năng phát lại

Đọc [review chức năng R1](review_v4_concurrent_backup_r1.md), 24 dòng, và nguyên [probe reviewer](v4_review_r1_evidence/probes.py), 46 dòng. Không import/thực thi code Anti đang thay đổi. Kết quả “1 positive +11 mutant đều PASS” là lần chạy do Codex root ghi nhận ở review R1, **không phải lượt tự chạy mới của reviewer này**. Source runner vẫn chưa được reviewer này đọc; không kết luận có secret thật hoặc app leak từ admission failure.

### Giới hạn cần đính chính cho diễn giải V4-R1

- `probes.py:34` đặt `source_operations.p0_precommit.amount_vnd=99999`. Đây là số nguyên dương hợp lệ về kiểu/miền giá trị; fixture không có request payload độc lập hay restored row amount để xác định số tiền mong đợi vẫn là 10000. PASS cho control này chứng minh chưa ràng buộc amount với dữ liệu kỳ vọng độc lập, **không tự nó chứng minh validator chấp nhận một giao dịch sai tiền hoặc DB bị hỏng**. Cụm “số tiền sai” trong review R1 cần được hiểu/đính chính đúng giới hạn này. Control mạnh hơn phải giữ request/expected amount=10000 và chỉ đổi observed payment/ledger amount, hoặc giữ fingerprint snapshot đúng và thay dữ liệu quan hệ được kiểm.
- `probes.py:27` thay mọi source fingerprint rows thành 999. Muốn gọi đây là mâu thuẫn cardinality phải xác định fingerprint được scope đúng ba operation của lượt chạy hoặc có expected snapshot/source count độc lập. Table-wide source có thêm dữ liệu fixture không liên quan có thể hợp lệ; không suy 999 tự động đồng nghĩa mất/duplicate payment. Missing fingerprint và digest sai định dạng là thiếu/sai evidence, chưa phải sai dữ liệu persisted.
- Các control duplicate payment/request và substituted restored P0 ID vẫn có ý nghĩa semantic trong canonical workload đã mô tả: P0 và writer A cùng Owner, cùng loại RPC nhưng amount/request intent khác; snapshot chỉ có P0. Cần ràng buộc actor/operation/payload và snapshot membership rõ để không cấm nhầm request ID trùng **giữa hai actor** (idempotency key thực còn scope theo actor/operation).

V4-R1 mức **P1** có thể giữ như blocker của oracle/evidence chấp nhận backup: thiếu evidence hoặc dữ liệu nội bộ mâu thuẫn vẫn ra PASS. Không diễn giải mức P1 đó thành bằng chứng thất thoát tài chính/app leak. V4-R2 mức **P2** phù hợp với trạng thái/provenance theo contract clean-source; không phải lỗi nghiệp vụ app. V4-R3 mức **P2** dựa trên test đỏ do root ghi nhận; reviewer này chưa tái chạy nên không bổ sung kết luận nguyên nhân publication-secret hoặc bỏ assertion. Phần review R1 ghi cleanup/overlap là khoảng trống chưa chứng minh runtime sai là đúng giới hạn.

### Khả năng tái lập và sửa tối thiểu cho bộ probe

`probes.py:7,23` import `build_canonical_summary` từ file **Anti đang sửa**. Bảo toàn bytes của `probes.py` không bảo toàn input: cùng probe sau khi canonical đổi sẽ không còn là exact replay lượt R1. `fp()` ở dòng 12–13 còn cấp cùng một digest giả cho mọi bảng, nên các verdict không chứng minh hash của row data thật. Probe hiện in diagnostic và exit0 là phù hợp nếu chỉ dùng quan sát; không gọi exit0 này là acceptance (review R1 đã phân biệt đúng).

Giữ nguyên probe/review R1 và thêm bản đính chính; không sửa lịch sử thành fixture khác. Với lượt kiểm tiếp, cách tối thiểu là lưu immutable JSON gồm canonical summary, source/restored/expected-snapshot fingerprint và các expected row/link/amount receipts; ghi hash các input cùng validator source đã kiểm, đồng thời lưu nguyên JSON output diagnostic. Một probe mới chỉ import validator, đọc frozen JSON rồi áp dụng mutant; positive phải PASS trước khi nhận negative là meaningful, exception phải ghi riêng thay vì tính là rejection hợp lệ. Nếu input bytes đúng lượt R1 chưa được lưu thì fixture đóng băng từ hiện trạng hoặc tái dựng sau đó phải mang nhãn **input mới/tái dựng**, không nhận là original exact replay.

Đây là assessment/erratum về độ chặt bằng chứng của review R1. Không chạy test mới, không sửa probe/review của root, không sửa bốn file Anti sở hữu, không đổi verdict runtime V4 hoặc nghiệm thu BH-07.

## Bổ sung 09/11/2026 — QA header và capture synthetic mới

Đã đọc fresh dòng đầu của `AGENTS.md`, `README.md`, `docs/00_START_HERE.md`, `docs/09_IMPLEMENTATION_PLAN.md`, `bh07_readiness.md`: cả năm đều đặt trạng thái 09/11 ở vị trí đầu, dẫn đúng continuation/review R1 và giữ toàn BH-07/V8 chưa nghiệm thu. Claim 437 là baseline, test V4 còn đỏ thuộc candidate đầu với 27 tests/1 FAIL theo R1; không mô tả đã chạy Docker/DB hay đã review đầy đủ source. Không thấy mâu thuẫn tài liệu mới có mức P0/P1/P2 trong phạm vi QA này.

Đã đọc nguyên `capture_current.py`, `diagnostic_capture_20261109.json` và phần đính chính R1: capture ghi rõ synthetic mới, không phải DB runtime hoặc input R1 nguyên bản; lưu canonical/fingerprint synthetic, 12 kết quả và source hashes. Script từ chối overwrite file đã tồn tại và chỉ lưu khi hash trước/sau bằng nhau. `Test-Path` cho continuation/R1/capture/script đều True; `Get-FileHash .../diagnostic_capture_20261109.json -Algorithm SHA256` cho `72944b37a5921d873163aaab818a23faecf17bc6a21b4b639e80777ace3d5225`, đúng digest trong R1. Không diễn giải digest synthetic `a`×64 thành hash DB thật hoặc claim input mới là replay byte-identical.

QA chỉ đọc tài liệu/capture và kiểm path/hash; không import, chạy probe/test hoặc đọc runner bằng công cụ khác. Anti đang sửa/retry riêng; candidate chưa được nghiệm thu, V4 không có runtime PASS và kết luận toàn BH-07 không đổi.

## Bổ sung 09/11/2026 — QA review sau sửa vòng 1/3

Đã đọc [review sau R1](review_v4_concurrent_backup_after_r1.md), [control mới](v4_review_r1_evidence/post_r1_controls.py) và [capture lưu input/output](v4_review_r1_evidence/post_r1_capture_20261109.json), không import/chạy code. Capture thể hiện đúng một positive PASS; duplicate ledger/audit ID và bool/float row counts FAIL; serial writer intervals và unrelated cleanup names vẫn PASS. Các finding V4-R4/R5 được giới hạn ở quyết định validator trên receipt synthetic, chưa chứng minh HTTP/DB execution hay cleanup runtime bị sai. Giữ R1 relational evidence chưa đủ và chỉ gọi R2/R3 hết triệu chứng quan sát là đúng mức bằng chứng. Các count 40 tests/35 author controls thuộc lượt root đã chạy, không phải lần tự kiểm của reviewer này; full-suite count vẫn chờ kết quả kết thúc như review ghi.

Capture mới lưu từng input summary/fingerprint và result, được gắn nhãn synthetic mới, không phải replay input R1 nguyên bản hoặc hash row DB. `Test-Path` cho review/control/capture đều True; hash file capture hiện tại là `01157cfa3ce713e915556d9997bf7c5221c9232d648d014f21472daa9db737ed`.

**Giới hạn attribution cần giữ rõ:** `post_r1_controls.py:13` import validator trước khi tính source hash lần đầu ở dòng 20. Guard dòng 54–56 chứng minh các file trên đĩa không đổi giữa hai lần hash, nhưng không tự chứng minh module đã import dùng đúng bytes được hash nếu có thay file giữa import và hash đầu. Không có bằng chứng race này thực sự xảy ra và không phủ nhận các output đã lưu. Với capture sau cần hash nguồn **trước import validator và load fixture**, rồi kiểm lại sau execution trong process mới; giữ capture hiện tại nguyên bytes, không gán guard hiện tại thành chứng thực tuyệt đối của loaded-source identity.

Năm header hiện hành đã chuyển sang vòng sửa 2/3, giữ V4/BH-07 chưa nghiệm thu và không còn dùng test đỏ ban đầu làm trạng thái hiện tại sau khi 40 targeted tests xanh. Assessment này không đóng V4-R4/R5 hoặc nghiệm thu R1 relational/runtime; không sửa root/Anti files và không chạy bộ test.

## Bổ sung 09/11/2026 — QA review sau sửa vòng 2/3

Đã đọc [review sau R2](review_v4_concurrent_backup_after_r2.md), `post_r2_controls.py`, `post_r2_request_controls.py` và các input/result lưu trong hai capture, không import hoặc chạy code. Capture đầu có positive PASS; serial writers/unrelated cleanup/ledger amount sai/audit request sai FAIL; request payment ID sai PASS. Capture bổ sung có positive PASS; request ID sai/thiếu request FAIL; normalized request status 500 và cặp replay fingerprint `not-a-digest` bằng nhau vẫn PASS. Mutant request payment giữ P0 payment ID đúng ở operation/payment/ledger nhưng thay normalized `row_evidence.request.payment_id`, tính lại digest và đặt restored row evidence cùng dữ liệu sai: đây là mâu thuẫn **receipt** được quan sát, chưa phải bằng chứng stored DB result thực đã hỏng.

Schema thật dòng 501–508 có `operation_requests.actor_user_id/operation/request_id/payload_hash/result/created_at`; không có cột HTTP status, cũng không có cột payment_id trực tiếp. Review R2 đã phân biệt status receipt với DB và yêu cầu đối chiếu `result` thật, phù hợp bằng chứng. Cụm header “request result sai payment” nên luôn được hiểu trong phạm vi normalized receipt synthetic; có thể viết rõ “receipt request trỏ sai payment” để tránh hiểu là đã quan sát DB corruption. R4/R5 chỉ hết triệu chứng synthetic, chưa chứng minh DB execution/resource ownership runtime; R1 relational/full-source/runtime vẫn chưa đủ bằng chứng.

Cả hai script mới hash runner trước import/fixture load và kiểm lại sau, nên đã xử lý thứ tự import-before-hash của capture trước. Hai capture có nhãn synthetic mới, lưu input/output, từ chối overwrite; không gán thành replay cũ. `Get-FileHash` capture đầu cho `32ba90e16f29a3fd0158af506fe31e62d85616efe1c2fcf489afaf02ca6ff7eb`, khớp input hash ghi ở capture bổ sung; capture bổ sung có hash `35f25408ff0df4c2bbc1e9c13c3ea14b626bc55334c0ca03e399923b68ed7a7c`. Digest quan hệ được tính lại không đồng nghĩa table fingerprint synthetic đã thành hash dữ liệu DB thật.

Năm header fresh đều ghi vòng 3/3 cuối, targeted 49/author controls 44; full Python 477 được giới hạn về bản vòng 1 và Flutter mới trên app không đổi theo kết quả root báo cáo. Không có claim full suite vòng 2 mới hoặc runtime V4. AGENTS dòng 148 đúng quy tắc dừng nếu còn lỗi sau ba vòng; không tự mở vòng 4. Không phát hiện overclaim material mới ngoài giới hạn wording đã nêu; assessment không nghiệm thu V4/BH-07, không sửa root/Anti files hoặc chạy test.

## Bổ sung 09/11/2026 — QA kết luận dừng sau vòng 3/3

Đã đọc [review cuối](review_v4_concurrent_backup_final_20261109.md), `final_controls.py`, các name/result được lưu và các trường liên quan trong capture cuối; không import/chạy code. Capture có một positive PASS, bảy mutant FAIL, ba mutant vẫn PASS: nested request result status sai, thiếu result và sai request operation. Code control tính lại digest của row evidence và cập nhật restored evidence cùng dữ liệu sai; finding R1 được giới hạn rõ là mâu thuẫn/thiếu **receipt synthetic**, không phải quan sát DB corruption. Source hash được lấy trước fixture load/import rồi đối chiếu sau; capture ghi nhãn mới/not DB runtime. Runner/test hashes trong capture khớp các chuỗi được review cuối công bố. Hash capture tại lúc QA: `911b1025a925aee6398f9c41ce80956a222e0b1d4811aff4b671e23a063b99ed`.

R6 có căn cứ source probe đọc được: `fp(rows, sha_hex='a'*64)` ở dòng 39–40, replay before/after `'e'*64` ở dòng 147–148, `canonical_restored_fp=fp(1)` ở dòng 169 và assert positive ở dòng 174. Điều này khớp lỗi positive/replay fingerprint mismatch mà root báo; không nhận author mutants đã chạy khi positive dừng trước chúng. Mức P2 của fixture probe và P1 của evidence oracle chưa fail-closed không bị diễn giải thành lỗi tài chính app/runtime thật.

Năm header đầu và note đầu handoff implementer đều đã ghi Chưa đạt/Dừng sau vòng 3/3, giữ 56 targeted PASS riêng với standalone probe FAIL và ba semantic mutant còn PASS. Full-suite candidate cuối vẫn ghi đang chờ, không suy count 437/477 hay count dự kiến thành kết quả cuối. Review giữ Docker/DB V4 NOT RUN, full source review chưa làm và toàn BH-07/V8 chưa nghiệm thu. Link review/control/capture đều tồn tại. Không thấy lỗi tài liệu material mới trong phạm vi QA; giữ R1/R6 mở và quy tắc không tự mở vòng 4 theo AGENTS 148. Không sửa file root/Anti, không chạy test hoặc đọc runner qua fallback.
