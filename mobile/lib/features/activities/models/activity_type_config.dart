// =============================================================================
// VeriField Nexus — Activity Type Configuration (Cookstove Only)
// =============================================================================
// Defines the Clean Cooking activity type with icons, colors, and form fields.
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

/// Activity type configuration.
class ActivityTypeConfig {
  final String id;
  final String label;
  final String description;
  final IconData icon;
  final Color color;
  final String methodology;
  final List<FormFieldDef> fields;

  const ActivityTypeConfig({
    required this.id,
    required this.label,
    required this.description,
    required this.icon,
    required this.color,
    required this.methodology,
    required this.fields,
  });
}

/// All supported activity types (Cookstove only).
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
  ),
];

/// Lookup helper.
ActivityTypeConfig getActivityTypeConfig(String id) {
  return activityTypes.firstWhere((t) => t.id == id, orElse: () => activityTypes.first);
}
