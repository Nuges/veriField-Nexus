// =============================================================================
// VeriField Nexus — Activity Type Configuration
// =============================================================================
// Defines all supported activity types with icons, colors, and form fields.
// Currently supports: Clean Cooking, Hybrid Energy.
// Used by the dynamic form engine to render type-specific input fields.
// =============================================================================

import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';

/// Field definition for dynamic form rendering.
class FormFieldDef {
  final String key;
  final String label;
  final String type; // string, int, float, enum, boolean, text
  final bool required;
  final List<String>? options; // For enum fields

  const FormFieldDef({
    required this.key,
    required this.label,
    required this.type,
    this.required = false,
    this.options,
  });
}

/// Photo field definition for dynamic evidence capture.
class PhotoFieldDef {
  final String key;
  final String label;
  final bool required;
  final String prompt;

  const PhotoFieldDef({
    required this.key,
    required this.label,
    this.required = false,
    required this.prompt,
  });
}

/// Activity type configuration.
class ActivityTypeConfig {
  final String id;
  final String label;
  final String description;
  final IconData icon;
  final Color color;
  final String methodology;
  final List<FormFieldDef> fields;
  final List<PhotoFieldDef> photos;

  const ActivityTypeConfig({
    required this.id,
    required this.label,
    required this.description,
    required this.icon,
    required this.color,
    required this.methodology,
    required this.fields,
    required this.photos,
  });
}

/// All supported activity types.
final List<ActivityTypeConfig> activityTypes = [
  ActivityTypeConfig(
    id: 'CLEAN_COOKING',
    label: 'Clean Cooking',
    description: 'Stove installation & usage',
    icon: Icons.soup_kitchen_rounded,
    color: AppColors.warning,
    methodology: 'Gold Standard TPDDTEC v3.1',
    fields: [
      // Stove Details
      FormFieldDef(key: 'stove_id', label: 'Stove ID (QR/BLE)', type: 'string', required: true),
      FormFieldDef(key: 'stove_model', label: 'Stove Model', type: 'enum', required: true,
          options: ['baikuc_gen1', 'tlud_forced', 'rocket', 'gasifier', 'jiko', 'lpg_burner', 'electric_ics', 'other']),
      FormFieldDef(key: 'manufacturer', label: 'Manufacturer', type: 'string'),
      FormFieldDef(key: 'serial_number', label: 'Serial Number', type: 'string'),
      // Household Details
      FormFieldDef(key: 'household_id', label: 'Household ID', type: 'string', required: true),
      FormFieldDef(key: 'head_name', label: 'Head of Household Name', type: 'string', required: true),
      FormFieldDef(key: 'phone_number', label: 'Phone Number', type: 'string'),
      FormFieldDef(key: 'household_size', label: 'Household Size', type: 'int', required: true),
      FormFieldDef(key: 'meals_per_day', label: 'Meals per Day', type: 'enum', required: true,
          options: ['1', '2', '3', '4+']),
      FormFieldDef(key: 'consent_obtained', label: 'Consent Obtained?', type: 'boolean', required: true),
      // Baseline Data
      FormFieldDef(key: 'baseline_fuel', label: 'Primary Baseline Fuel', type: 'enum', required: true,
          options: ['wood', 'charcoal', 'crop_residue', 'dung', 'kerosene', 'lpg', 'grid_electric']),
      FormFieldDef(key: 'baseline_stove', label: 'Baseline Stove Type', type: 'enum', required: true,
          options: ['3_stone_fire', 'traditional_clay', 'metal_grate', 'kerosene_stove', 'gas_burner', 'other']),
      FormFieldDef(key: 'baseline_fuel_consumption', label: 'Monthly Fuel Before (kg/L)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_fuel_cost', label: 'Monthly Fuel Cost Before (₦)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_cooking_duration', label: 'Daily Cooking Before (hrs)', type: 'float', required: true),
      FormFieldDef(key: 'fuel_source', label: 'Fuel Source', type: 'enum', required: true,
          options: ['collected_free', 'purchased']),
      // Project Data
      FormFieldDef(key: 'primary_fuel', label: 'Project Primary Fuel', type: 'enum', required: true,
          options: ['wood', 'pellet', 'charcoal', 'lpg', 'biogas', 'electric']),
      FormFieldDef(key: 'usage_flag', label: 'Currently in Use?', type: 'boolean', required: true),
      FormFieldDef(key: 'project_cooking_duration', label: 'Daily Cooking Now (hrs)', type: 'float', required: true),
      FormFieldDef(key: 'stove_condition', label: 'Stove Condition', type: 'enum', required: true,
          options: ['good', 'minor_damage', 'needs_repair', 'abandoned']),
    ],
    photos: [
      PhotoFieldDef(
        key: 'stove_installation',
        label: 'Stove Installation Photo',
        required: true,
        prompt: 'Take a clear photo of the newly installed clean cookstove in the kitchen.',
      ),
      PhotoFieldDef(
        key: 'baseline_fuel_source',
        label: 'Old Stove / Baseline Fuel Photo',
        required: false,
        prompt: 'Capture the traditional open fire or old cooking device (if present).',
      ),
    ],
  ),

  // -------------------------------------------------------------------------
  // Hybrid Energy — Solar/Gas/Diesel displacement MRV
  // -------------------------------------------------------------------------
  ActivityTypeConfig(
    id: 'HYBRID_ENERGY',
    label: 'Hybrid Energy',
    description: 'Solar/Gas/Diesel displacement MRV',
    icon: Icons.solar_power_rounded,
    color: Color(0xFFF59E0B), // Amber
    methodology: 'Verra AMS-I.F / Gold Standard',
    fields: [
      // Site & Owner Identity
      FormFieldDef(key: 'site_id', label: 'Site ID', type: 'string', required: true),
      FormFieldDef(key: 'owner_name', label: 'Site Owner / Manager Name', type: 'string', required: true),
      FormFieldDef(key: 'owner_phone', label: 'Owner Phone Number', type: 'string'),
      FormFieldDef(key: 'site_type', label: 'Site Type', type: 'enum', required: true,
          options: ['residential', 'commercial', 'industrial', 'institutional', 'telecom_tower', 'agricultural']),
      // Baseline Generator Details
      FormFieldDef(key: 'baseline_generator_type', label: 'Baseline Generator Type', type: 'enum', required: true,
          options: ['diesel', 'petrol', 'heavy_fuel_oil']),
      FormFieldDef(key: 'baseline_generator_capacity_kva', label: 'Generator Capacity (kVA)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_fuel_consumption_lph', label: 'Fuel Consumption Rate (L/hr)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_avg_daily_runtime_hrs', label: 'Avg Daily Runtime (hrs)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_operating_days_per_year', label: 'Operating Days Per Year', type: 'int', required: true),
      FormFieldDef(key: 'baseline_monthly_fuel_cost', label: 'Monthly Fuel Cost (₦)', type: 'float'),
      // Post-Installation Hybrid System
      FormFieldDef(key: 'solar_capacity_kwp', label: 'Solar PV Capacity (kWp)', type: 'float', required: true),
      FormFieldDef(key: 'battery_capacity_kwh', label: 'Battery Storage (kWh)', type: 'float'),
      FormFieldDef(key: 'inverter_capacity_kva', label: 'Inverter Capacity (kVA)', type: 'float', required: true),
      FormFieldDef(key: 'gas_generator_capacity_kva', label: 'Gas Generator (kVA)', type: 'float'),
      FormFieldDef(key: 'diesel_backup_capacity_kva', label: 'Diesel Backup (kVA)', type: 'float'),
      FormFieldDef(key: 'installer_name', label: 'Installer / EPC Company', type: 'string'),
      FormFieldDef(key: 'installation_date', label: 'Installation Date', type: 'string', required: true),
      // Data Source Configuration
      FormFieldDef(key: 'data_source', label: 'Primary Data Source', type: 'enum', required: true,
          options: ['smart_inverter_api', 'hybrid_inverter_manual', 'analog_manual']),
      FormFieldDef(key: 'inverter_brand', label: 'Inverter Brand / Model', type: 'string'),
      FormFieldDef(key: 'inverter_serial_number', label: 'Inverter Serial Number', type: 'string'),
      FormFieldDef(key: 'avg_sun_hours', label: 'Average Peak Sun Hours (hrs/day)', type: 'float', required: true),
      FormFieldDef(key: 'system_efficiency', label: 'System Efficiency Factor (0-1)', type: 'float'),
      // Verification Checklist
      FormFieldDef(key: 'system_installed', label: 'System Installed & Commissioned?', type: 'boolean', required: true),
      FormFieldDef(key: 'system_operational', label: 'System Currently Operational?', type: 'boolean', required: true),
      FormFieldDef(key: 'tamper_signs', label: 'Tampering Signs Detected?', type: 'boolean', required: true),
      FormFieldDef(key: 'usage_confirmed', label: 'Active Usage Confirmed?', type: 'boolean', required: true),
      FormFieldDef(key: 'consent_obtained', label: 'Owner Consent Obtained?', type: 'boolean', required: true),
    ],
    photos: [
      PhotoFieldDef(
        key: 'solar_installation',
        label: 'Solar PV Installation Photo',
        required: true,
        prompt: 'Take a wide-angle shot of the newly installed solar panels or hybrid system.',
      ),
      PhotoFieldDef(
        key: 'baseline_generator',
        label: 'Baseline Diesel Generator Photo',
        required: true,
        prompt: 'Capture the old baseline diesel or petrol generator for displacement proof.',
      ),
      PhotoFieldDef(
        key: 'inverter_label',
        label: 'Inverter Nameplate Photo',
        required: false,
        prompt: 'Capture the brand/serial number printed on the inverter unit.',
      ),
    ],
  ),
];

/// Lookup helper.
ActivityTypeConfig getActivityTypeConfig(String id) {
  return activityTypes.firstWhere((t) => t.id == id, orElse: () => activityTypes.first);
}
