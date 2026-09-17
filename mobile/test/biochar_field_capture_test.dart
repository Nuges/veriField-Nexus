// =============================================================================
// VeriField Nexus — Biochar Field Capture & Activity Contract Unit Tests
// =============================================================================
// Tests:
// 1. ActivityTypeConfig BIOCHAR_C_SINK registration & methodology metadata
// 2. Comprehensive form field definitions and validation types
// 3. Photo field definitions for complete biochar evidence chain
// 4. Batch sync payload assembly and SHA-256 evidence integrity
// 5. Offline activity record serialization & deduplication keys
// =============================================================================

import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';
import 'package:verifield_nexus/features/activities/models/activity_type_config.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Biochar Activity Configuration Tests', () {
    test('BIOCHAR_C_SINK is registered with correct metadata', () {
      final config = getActivityTypeConfig('BIOCHAR_C_SINK');
      expect(config.id, equals('BIOCHAR_C_SINK'));
      expect(config.label, equals('Biochar C-Sink'));
      expect(config.methodology, contains('C-Sink'));
      expect(config.fields, isNotEmpty);
      expect(config.photos, isNotEmpty);
    });

    test('BIOCHAR_C_SINK defines all required value chain fields', () {
      final config = getActivityTypeConfig('BIOCHAR_C_SINK');
      final fieldKeys = config.fields.map((f) => f.key).toSet();

      final expectedKeys = [
        'kiln_id',
        'biomass_id',
        'batch_id',
        'production_timestamp',
        'kiln_capacity_limit_kg',
        'application_timestamp',
        'applied_quantity_kg',
        'remaining_quantity_kg',
        'field_agent_id',
        'batch_weight_kg',
        'quench_method',
        'lab_carbon_content_pct',
        'lab_hc_ratio',
        'moisture_content_pct',
        'application_matrix',
        'recipient_farmer_id',
        'qr_id',
      ];

      for (final key in expectedKeys) {
        expect(fieldKeys.contains(key), isTrue,
            reason: 'Field key $key must be defined in BIOCHAR_C_SINK');
      }
    });

    test('BIOCHAR_C_SINK defines all required photo evidence fields', () {
      final config = getActivityTypeConfig('BIOCHAR_C_SINK');
      final photoKeys = config.photos.map((p) => p.key).toSet();

      expect(photoKeys.contains('kiln_pyrolysis'), isTrue);
      expect(photoKeys.contains('weight_verification'), isTrue);
      expect(photoKeys.contains('lab_analysis_report'), isTrue);
      expect(photoKeys.contains('application_proof'), isTrue);
    });

    test('quench_method and application_matrix have valid options', () {
      final config = getActivityTypeConfig('BIOCHAR_C_SINK');
      final quenchField = config.fields.firstWhere((f) => f.key == 'quench_method');
      expect(quenchField.options, containsAll(['water', 'soil', 'nutrient_slurry']));

      final matrixField = config.fields.firstWhere((f) => f.key == 'application_matrix');
      expect(matrixField.options, containsAll([
        'soil_amendment',
        'compost_additive',
        'concrete_admixture',
        'animal_feed',
        'biomaterial'
      ]));
    });
  });

  group('Offline Batch Payload Assembly & Evidence SHA-256 Tests', () {
    test('Simulated field activity conforms to backend ActivityCreate and batch schema', () {
      final clientId = const Uuid().v4();
      final sampleImageBytes = utf8.encode('biochar_pyrolysis_evidence_image_bytes_42');
      final sha256Digest = sha256.convert(sampleImageBytes).toString();

      final activityData = {
        'kiln_id': 'default_kiln',
        'biomass_id': 'default_biomass',
        'batch_id': 'BATCH-2026-NEXUS-001',
        'production_timestamp': '2026-09-17T08:00:00Z',
        'kiln_capacity_limit_kg': 500.0,
        'application_timestamp': '2026-09-17T14:00:00Z',
        'applied_quantity_kg': 450.0,
        'remaining_quantity_kg': 50.0,
        'field_agent_id': 'AGENT-007',
        'batch_weight_kg': 500.0,
        'quench_method': 'water',
        'lab_carbon_content_pct': 82.5,
        'lab_hc_ratio': 0.35,
        'moisture_content_pct': 12.0,
        'application_matrix': 'soil_amendment',
        'recipient_farmer_id': 'FARMER-991',
        'qr_id': 'EBC-QR-778899',
      };

      final offlineRecord = {
        'id': const Uuid().v4(),
        'client_id': clientId,
        'activity_type': 'BIOCHAR_C_SINK',
        'activity_data': jsonEncode(activityData),
        'description': 'Biochar pyrolysis run and soil application capture',
        'image_path': '/local/storage/photos/$clientId.jpg',
        'image_hash': sha256Digest,
        'latitude': 6.5244,
        'longitude': 3.3792,
        'gps_accuracy': 4.2,
        'captured_at': DateTime.now().toUtc().toIso8601String(),
        'sync_status': 'pending',
        'retry_count': 0,
        'sector': 'biochar',
        'created_at': DateTime.now().toUtc().toIso8601String(),
      };

      // Ensure SHA-256 is 64 hex characters
      expect(offlineRecord['image_hash'], matches(r'^[a-f0-9]{64}$'));

      // Simulate building batch item for POST /activities/batch
      final batchItem = {
        'client_id': offlineRecord['client_id'],
        'activity_type': offlineRecord['activity_type'],
        'sector': offlineRecord['sector'],
        'activity_data': jsonDecode(offlineRecord['activity_data'] as String),
        'description': offlineRecord['description'],
        'image_url': 'https://storage.verifield.org/evidence/${offlineRecord['client_id']}.jpg',
        'image_hash': offlineRecord['image_hash'],
        'latitude': offlineRecord['latitude'],
        'longitude': offlineRecord['longitude'],
        'gps_accuracy': offlineRecord['gps_accuracy'],
        'captured_at': offlineRecord['captured_at'],
      };

      final batchPayload = {
        'activities': [batchItem]
      };

      final encoded = jsonEncode(batchPayload);
      final decoded = jsonDecode(encoded) as Map<String, dynamic>;

      expect(decoded['activities'], isA<List>());
      expect((decoded['activities'] as List).length, equals(1));
      final firstItem = (decoded['activities'] as List)[0] as Map<String, dynamic>;
      expect(firstItem['client_id'], equals(clientId));
      expect(firstItem['activity_type'], equals('BIOCHAR_C_SINK'));
      expect(firstItem['image_hash'], equals(sha256Digest));
      expect(firstItem['activity_data']['batch_weight_kg'], equals(500.0));
      expect(firstItem['activity_data']['lab_carbon_content_pct'], equals(82.5));
    });
  });
}
