import 'dart:convert';
import 'dart:io';

/// Công cụ dòng lệnh (CLI script) để kết nối và thao tác trực tiếp với Supabase từ terminal
///
/// Hướng dẫn sử dụng:
///   dart run scripts/supabase_client.dart ping
///   dart run scripts/supabase_client.dart query `<tên_bảng>`
///   dart run scripts/supabase_client.dart info
void main(List<String> args) async {
  const defaultUrl = 'https://vqelcjxljddxoyplgcvm.supabase.co';
  const defaultKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxZWxjanhsamRkeG95cGxnY3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyODc0NjIsImV4cCI6MjEwNjg2MzQ2Mn0.u_lf-7_EYW9SGuVL5iiOw5hXiuiR-Sq4HE7xw-kdgpg';

  final supabaseUrl =
      Platform.environment['SUPABASE_URL'] ?? defaultUrl;
  final supabaseKey =
      Platform.environment['SUPABASE_ANON_KEY'] ?? defaultKey;

  if (args.isEmpty || args[0] == 'help') {
    stdout.writeln('=== Badminton Hub — Supabase Direct CLI Tool ===');
    stdout.writeln('Cách dùng:');
    stdout.writeln('  dart run scripts/supabase_client.dart ping');
    stdout.writeln('  dart run scripts/supabase_client.dart query <tên_bảng>');
    stdout.writeln('  dart run scripts/supabase_client.dart info');
    return;
  }

  final command = args[0];

  switch (command) {
    case 'info':
      stdout.writeln('=== Thông Tin Kết Nối Supabase ===');
      stdout.writeln('Supabase URL: $supabaseUrl');
      stdout.writeln('Project Ref:  vqelcjxljddxoyplgcvm');
      stdout.writeln('Anon Key:     ${supabaseKey.substring(0, 20)}...');
      stdout.writeln('Auth Health:  $supabaseUrl/auth/v1/health');
      stdout.writeln('REST Root:    $supabaseUrl/rest/v1/');
      break;

    case 'ping':
      stdout.writeln('Đang kiểm tra kết nối tới Supabase ($supabaseUrl)...');
      final client = HttpClient();
      try {
        // 1. Kiểm tra REST endpoint
        final restUri = Uri.parse('$supabaseUrl/rest/v1/venues?select=id&limit=1');
        final restReq = await client.getUrl(restUri);
        restReq.headers.set('apikey', supabaseKey);
        restReq.headers.set('Authorization', 'Bearer $supabaseKey');
        final restRes = await restReq.close();
        await restRes.drain();
        stdout.writeln('  [REST API] HTTP ${restRes.statusCode} OK (Bảng venues phản hồi tốt)');

        // 2. Kiểm tra Auth endpoint
        final authUri = Uri.parse('$supabaseUrl/auth/v1/health');
        final authReq = await client.getUrl(authUri);
        authReq.headers.set('apikey', supabaseKey);
        final authRes = await authReq.close();
        final authBody = await authRes.transform(utf8.decoder).join();
        stdout.writeln('  [Auth API] HTTP ${authRes.statusCode} ($authBody)');

        stdout.writeln('=> Kết nối Supabase thành công và hoạt động bình thường!');
      } catch (e) {
        stderr.writeln('Lỗi khi kiểm tra kết nối: $e');
        exitCode = 1;
      } finally {
        client.close(force: true);
      }
      break;

    case 'query':
      if (args.length < 2) {
        stderr.writeln('Vui lòng chỉ định tên bảng cần truy vấn: query <tên_bảng>');
        exitCode = 1;
        return;
      }
      final table = args[1];
      stdout.writeln('Đang truy vấn bảng "$table"...');
      final client = HttpClient();
      try {
        final uri = Uri.parse('$supabaseUrl/rest/v1/$table?select=*&limit=10');
        final req = await client.getUrl(uri);
        req.headers.set('apikey', supabaseKey);
        req.headers.set('Authorization', 'Bearer $supabaseKey');
        req.headers.set('Content-Type', 'application/json');

        final res = await req.close();
        final body = await res.transform(utf8.decoder).join();
        if (res.statusCode >= 200 && res.statusCode < 300) {
          final decoded = jsonDecode(body);
          if (decoded is List) {
            stdout.writeln('Tìm thấy ${decoded.length} bản ghi (tối đa 10):');
            stdout.writeln(const JsonEncoder.withIndent('  ').convert(decoded));
          } else {
            stdout.writeln(body);
          }
        } else {
          stderr.writeln('Lỗi HTTP ${res.statusCode}: $body');
          exitCode = 1;
        }
      } catch (e) {
        stderr.writeln('Lỗi truy vấn: $e');
        exitCode = 1;
      } finally {
        client.close(force: true);
      }
      break;

    default:
      stderr.writeln('Lệnh không nhận dạng: $command. Chạy với `help` để xem trợ giúp.');
      exitCode = 1;
  }
}
