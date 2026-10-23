import 'package:flutter_test/flutter_test.dart';
import 'package:verifield_nexus/core/utils/field_access.dart';

void main() {
  test('only operational roles capture; administrators cannot act as VVB', () {
    const roles = ['SUPER_ADMIN', 'ORG_ADMIN', 'PROJECT_MANAGER', 'FIELD_SUPERVISOR', 'FIELD_AGENT', 'QA_OFFICER', 'VERIFIER', 'AUDITOR', 'COMPLIANCE_ADMIN', 'REGISTRY_ADMIN', 'FINANCE', 'INVESTOR', 'VIEWER'];
    for (final role in roles) {
      expect(FieldAccess.canCapture(role), ['SUPER_ADMIN', 'ORG_ADMIN', 'PROJECT_MANAGER', 'FIELD_SUPERVISOR', 'FIELD_AGENT'].contains(role), reason: role);
      expect(FieldAccess.canReview(role), ['VERIFIER', 'AUDITOR'].contains(role), reason: role);
    }
    expect(FieldAccess.canReview('vvb'), isTrue);
    expect(FieldAccess.canReview('admin'), isFalse);
    expect(FieldAccess.canCapture('unrecognized'), isFalse);
  });
  test('all five sectors lead to their own field form', () {
    const mappings = {'COOKSTOVES': 'CLEAN_COOKING', 'HYBRID_ENERGY': 'HYBRID_ENERGY', 'BIOCHAR': 'BIOCHAR_C_SINK', 'EV_MOBILITY': 'EV_TRIP', 'AGRICULTURE_LAND_USE': 'soil_sample_collection'};
    for (final item in mappings.entries) {
      expect(FieldAccess.activityType(FieldAccess.projectSector({'sector': item.key})), item.value);
      expect(FieldAccess.projectSector({'baseline_parameters': {'sector': item.key}}), item.key);
    }
    expect(FieldAccess.projectSector({'name': 'Farm'}), isNull);
    expect(FieldAccess.activityType(null), isNull);
  });
}
