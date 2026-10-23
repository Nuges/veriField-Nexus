/// UI capabilities. The server remains authoritative for tenant and mutation access.
class FieldAccess {
  static String role(Object? value) {
    final normalized = value.toString().trim().toUpperCase().replaceAll(RegExp(r'[\s-]+'), '_');
    const aliases = {'ADMIN': 'ORG_ADMIN', 'ORG_OWNER': 'ORG_ADMIN', 'TENANT_ADMIN': 'ORG_ADMIN', 'ORGANIZATION_ADMIN': 'ORG_ADMIN', 'SUPERADMIN': 'SUPER_ADMIN', 'PLATFORM_SUPER_ADMIN': 'SUPER_ADMIN', 'VVB': 'VERIFIER', 'VVB_VERIFIER': 'VERIFIER', 'VVB_AUDITOR': 'AUDITOR', 'THIRD_PARTY_AUDITOR': 'AUDITOR', 'OPERATOR': 'FIELD_AGENT', 'TECHNICIAN': 'FIELD_AGENT', 'SURVEYOR': 'FIELD_AGENT', 'PROJECT_DEVELOPER': 'PROJECT_MANAGER', 'DEVELOPER': 'PROJECT_MANAGER', 'PORTFOLIO_MANAGER': 'PROJECT_MANAGER', 'PROGRAMME_MANAGER': 'PROJECT_MANAGER', 'MRV_OFFICER': 'QA_OFFICER', 'MRV_MANAGER': 'QA_OFFICER'};
    return aliases[normalized] ?? normalized;
  }
  static bool canCapture(Object? value) => const {'SUPER_ADMIN', 'ORG_ADMIN', 'PROJECT_MANAGER', 'FIELD_SUPERVISOR', 'FIELD_AGENT'}.contains(role(value));
  static bool canReview(Object? value) => const {'VERIFIER', 'AUDITOR'}.contains(role(value));
  static bool canReadAudits(Object? value) => canReview(value) || const {'SUPER_ADMIN', 'ORG_ADMIN', 'PROJECT_MANAGER', 'QA_OFFICER'}.contains(role(value));
  static bool canReadSensors(Object? value) => const {'SUPER_ADMIN', 'ORG_ADMIN', 'PROJECT_MANAGER', 'FIELD_SUPERVISOR', 'QA_OFFICER', 'VERIFIER', 'AUDITOR'}.contains(role(value));
  static String? sector(Object? value) {
    final normalized = value?.toString().trim().toUpperCase().replaceAll(RegExp(r'[\s-]+'), '_');
    const aliases = {'COOKSTOVE': 'COOKSTOVES', 'CLEAN_COOKING': 'COOKSTOVES', 'AGRICULTURE': 'AGRICULTURE_LAND_USE', 'AGRICULTURE_SOIL': 'AGRICULTURE_LAND_USE', 'BIOCHAR_C_SINK': 'BIOCHAR', 'EV_TRIP': 'EV_MOBILITY'};
    final code = aliases[normalized] ?? normalized;
    return const {'COOKSTOVES', 'HYBRID_ENERGY', 'BIOCHAR', 'EV_MOBILITY', 'AGRICULTURE_LAND_USE'}.contains(code) ? code : null;
  }
  static String? projectSector(Map<String, dynamic> project) {
    final baseline = project['baseline_parameters'];
    return sector(project['sector']) ?? sector(project['sector_id']) ?? (baseline is Map ? sector(baseline['sector']) ?? sector(baseline['sector_code']) : null);
  }
  static String? activityType(String? sectorCode) => const {'COOKSTOVES': 'CLEAN_COOKING', 'HYBRID_ENERGY': 'HYBRID_ENERGY', 'BIOCHAR': 'BIOCHAR_C_SINK', 'EV_MOBILITY': 'EV_TRIP', 'AGRICULTURE_LAND_USE': 'soil_sample_collection'}[sectorCode];
}
