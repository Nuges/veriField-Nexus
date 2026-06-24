// =============================================================================
// VeriField Nexus — API Service Tests
// =============================================================================

import 'package:flutter_test/flutter_test.dart';
import 'package:verifield_nexus/services/api_service.dart';
import 'package:flutter/foundation.dart';

void main() {
  group('ApiService.baseUrl Tests', () {
    test('Returns default environment URL when no environment variable is provided', () {
      expect(ApiService.baseUrl, equals('https://verifield-nexus.onrender.com/api/v1'));
    });
  });
}
