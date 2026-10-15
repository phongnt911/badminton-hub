import 'package:flutter_test/flutter_test.dart';
import 'package:badminton_hub/core/app_config.dart';

void main() {
  test('configuration is explicit and test/production targets are guarded', () {
    const expectedValid = bool.fromEnvironment('EXPECT_VALID');
    if (expectedValid) {
      expect(AppConfig.validate, returnsNormally);
    } else {
      expect(AppConfig.validate, throwsStateError);
    }
  });
}
