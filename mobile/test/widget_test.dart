// =============================================================================
// VeriField Nexus — API Service Tests
// =============================================================================

import 'package:flutter_test/flutter_test.dart';
import 'package:verifield_nexus/services/api_service.dart';
import 'package:flutter/foundation.dart';

void main() {
  group('ApiService.baseUrl Tests', () {
    test('Returns correct local development URL based on target platform', () {
      if (defaultTargetPlatform == TargetPlatform.android) {
        expect(ApiService.baseUrl, equals('http://10.0.2.2:8000/api/v1'));
      } else {
        expect(ApiService.baseUrl, equals('http://localhost:8000/api/v1'));
      }
    });
  });
}
