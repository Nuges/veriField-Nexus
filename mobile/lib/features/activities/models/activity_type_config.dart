// =============================================================================
// VeriField Nexus — Activity Type Configuration
// =============================================================================
// Defines all supported activity types with icons, colors, and form fields.
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

/// All supported activity types.
final List<ActivityTypeConfig> activityTypes = [
  ActivityTypeConfig(
    id: 'CLEAN_COOKING',
    label: 'Clean Cooking',
    description: 'Stove installation & usage',
    icon: Icons.local_fire_department_rounded,
    color: AppColors.warning,
    methodology: 'Gold Standard TPDDTEC v3.1',
    fields: [
      FormFieldDef(key: 'stove_id', label: 'Stove ID', type: 'string', required: true),
      FormFieldDef(key: 'household_size', label: 'Household Size', type: 'int', required: true),
      FormFieldDef(key: 'primary_fuel', label: 'Primary Fuel', type: 'enum', required: true,
          options: ['wood', 'pellet', 'charcoal', 'LPG']),
      FormFieldDef(key: 'usage_flag', label: 'Currently in Use?', type: 'boolean', required: true),
    ],
  ),
  ActivityTypeConfig(
    id: 'AGRICULTURE',
    label: 'Agriculture',
    description: 'Sustainable land management',
    icon: Icons.grass_rounded,
    color: AppColors.primary,
    methodology: 'Verra VM0042',
    fields: [
      FormFieldDef(key: 'crop_type', label: 'Crop Type', type: 'string', required: true),
      FormFieldDef(key: 'plot_area_hectares', label: 'Plot Area (ha)', type: 'float', required: true),
      FormFieldDef(key: 'practice_type', label: 'Practice Type', type: 'enum', required: true,
          options: ['conservation_tillage', 'cover_cropping', 'agroforestry', 'composting', 'other']),
      FormFieldDef(key: 'soil_type', label: 'Soil Type', type: 'enum',
          options: ['clay', 'loam', 'sandy', 'silt', 'peat']),
    ],
  ),
  ActivityTypeConfig(
    id: 'ENERGY_USE',
    label: 'Energy Use',
    description: 'Renewable energy tracking',
    icon: Icons.bolt_rounded,
    color: AppColors.accent,
    methodology: 'CDM AMS-I.A.',
    fields: [
      FormFieldDef(key: 'device_type', label: 'Device Type', type: 'enum', required: true,
          options: ['solar_panel', 'solar_lantern', 'biogas', 'wind', 'micro_hydro']),
      FormFieldDef(key: 'capacity_kw', label: 'Capacity (kW)', type: 'float', required: true),
      FormFieldDef(key: 'daily_output_kwh', label: 'Daily Output (kWh)', type: 'float'),
      FormFieldDef(key: 'households_served', label: 'Households Served', type: 'int', required: true),
    ],
  ),
  ActivityTypeConfig(
    id: 'FORESTRY_LAND_USE',
    label: 'Forestry & Land',
    description: 'Reforestation & land use',
    icon: Icons.park_rounded,
    color: const Color(0xFF2E7D32),
    methodology: 'Verra VM0047 ARR',
    fields: [
      FormFieldDef(key: 'tree_count', label: 'Trees Planted', type: 'int', required: true),
      FormFieldDef(key: 'species', label: 'Species', type: 'string', required: true),
      FormFieldDef(key: 'plot_area_hectares', label: 'Plot Area (ha)', type: 'float', required: true),
      FormFieldDef(key: 'survival_rate_pct', label: 'Survival Rate (%)', type: 'float'),
    ],
  ),
  ActivityTypeConfig(
    id: 'SAFE_WATER',
    label: 'Safe Water',
    description: 'Water supply & purification',
    icon: Icons.water_drop_rounded,
    color: const Color(0xFF0288D1),
    methodology: 'Gold Standard Safe Water',
    fields: [
      FormFieldDef(key: 'water_source_type', label: 'Source Type', type: 'enum', required: true,
          options: ['borehole', 'handpump', 'solar_pump', 'gravity_fed', 'filter']),
      FormFieldDef(key: 'daily_volume_liters', label: 'Daily Volume (L)', type: 'float', required: true),
      FormFieldDef(key: 'households_served', label: 'Households Served', type: 'int', required: true),
      FormFieldDef(key: 'operational_status', label: 'Status', type: 'enum', required: true,
          options: ['active', 'faulty', 'maintenance']),
    ],
  ),
  ActivityTypeConfig(
    id: 'TRANSPORT_MOBILITY',
    label: 'Transport',
    description: 'Clean mobility (AMS-III.C)',
    icon: Icons.directions_car_rounded,
    color: const Color(0xFF7B1FA2),
    methodology: 'CDM AMS-III.C.',
    fields: [
      // Vehicle identification
      FormFieldDef(key: 'vehicle_type', label: 'Vehicle Type', type: 'enum', required: true,
          options: ['motorcycle_okada', 'tricycle_keke', 'car_taxi', 'minibus_danfo', 'bus', 'light_truck', 'heavy_truck', 'forklift']),
      FormFieldDef(key: 'energy_type', label: 'Energy Type', type: 'enum', required: true,
          options: ['EV', 'hybrid', 'CNG', 'LPG', 'diesel_retrofit']),
      FormFieldDef(key: 'vehicle_id', label: 'Vehicle ID', type: 'string', required: true),
      FormFieldDef(key: 'registration_number', label: 'Registration Number', type: 'string', required: true),
      // Usage data
      FormFieldDef(key: 'odometer_start', label: 'Odometer Start (km)', type: 'float', required: true),
      FormFieldDef(key: 'odometer_end', label: 'Odometer End (km)', type: 'float', required: true),
      FormFieldDef(key: 'operating_days', label: 'Operating Days', type: 'int', required: true),
      FormFieldDef(key: 'energy_used', label: 'Energy Used', type: 'float', required: true),
      FormFieldDef(key: 'energy_unit', label: 'Energy Unit', type: 'enum',
          options: ['kWh', 'litres', 'm3']),
      FormFieldDef(key: 'charging_source', label: 'Charging Source', type: 'enum',
          options: ['grid', 'solar_onsite', 'solar_offsite', 'generator', 'mixed']),
      // Forklift mode
      FormFieldDef(key: 'operating_hours', label: 'Operating Hours', type: 'float'),
    ],
  ),
  ActivityTypeConfig(
    id: 'OTHER',
    label: 'Other',
    description: 'Custom activity type',
    icon: Icons.more_horiz_rounded,
    color: AppColors.textTertiary,
    methodology: 'Manual Review',
    fields: [
      FormFieldDef(key: 'custom_activity_name', label: 'Activity Name', type: 'string', required: true),
      FormFieldDef(key: 'description', label: 'Description', type: 'text', required: true),
    ],
  ),
];

/// Lookup helper.
ActivityTypeConfig getActivityTypeConfig(String id) {
  return activityTypes.firstWhere((t) => t.id == id, orElse: () => activityTypes.last);
}
