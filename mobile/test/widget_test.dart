// =============================================================================

// VeriField Nexus — API Service & Contract Unit Tests

// =============================================================================



import 'package:flutter_test/flutter_test.dart';

import 'package:verifield_nexus/services/api_service.dart';



void main() {

  TestWidgetsFlutterBinding.ensureInitialized();



  group('ApiService Contract & Configuration Tests', () {

    test('Returns default environment URL when no environment variable is provided', () {

      expect(ApiService.baseUrl.contains('/api/v1'), isTrue);

    });



    test('Custom token management sets and retrieves token correctly', () async {

      expect(ApiService.customToken, isNull);

      await ApiService.setCustomToken('test_token_eyJhbGciOiJIUzI1NiI');

      expect(ApiService.customToken, equals('test_token_eyJhbGciOiJIUzI1NiI'));

      await ApiService.setCustomToken(null);

      expect(ApiService.customToken, isNull);

    });

  });

}
