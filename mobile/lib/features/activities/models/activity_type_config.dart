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
  ActivityTypeConfig(
    id: 'AGRICULTURE',
    label: 'Agriculture',
    description: 'Sustainable land management',
    icon: Icons.grass_rounded,
    color: AppColors.primary,
    methodology: 'Verra VM0042',
    fields: [
      // Plot Details
      FormFieldDef(key: 'plot_id', label: 'Plot ID', type: 'string', required: true),
      FormFieldDef(key: 'farmer_name', label: 'Farmer Name', type: 'string', required: true),
      FormFieldDef(key: 'farmer_phone', label: 'Farmer Phone', type: 'string', required: true),
      FormFieldDef(key: 'land_tenure', label: 'Land Tenure Type', type: 'enum', required: true,
          options: ['owned', 'leased', 'communal', 'other']),
      FormFieldDef(key: 'plot_area_hectares', label: 'Plot Area (ha)', type: 'float', required: true),
      FormFieldDef(key: 'agro_zone', label: 'Agro-ecological Zone', type: 'enum', required: true,
          options: ['sudan_savanna', 'guinea_savanna', 'forest_transition', 'humid_forest', 'mangrove']),
      // Baseline Data
      FormFieldDef(key: 'baseline_land_use', label: 'Previous Land Use', type: 'enum', required: true,
          options: ['cropland_conventional', 'degraded_pasture', 'bare_eroded', 'fallow', 'natural_veg']),
      FormFieldDef(key: 'baseline_practice', label: 'Previous Practice', type: 'enum', required: true,
          options: ['conventional_tillage', 'burning', 'no_cover_crop', 'synthetic_only', 'none']),
      FormFieldDef(key: 'baseline_crop', label: 'Previous Crop', type: 'string'),
      FormFieldDef(key: 'baseline_synthetic_fert', label: 'Synthetic Fert Before?', type: 'boolean', required: true),
      FormFieldDef(key: 'baseline_fert_amount', label: 'Amount Before (kg/ha)', type: 'float'),
      FormFieldDef(key: 'baseline_burning', label: 'Burning Practiced Before?', type: 'boolean', required: true),
      // Project Practice
      FormFieldDef(key: 'crop_type', label: 'Crop Type', type: 'enum', required: true,
          options: ['maize', 'cassava', 'rice', 'sorghum', 'cowpea', 'yam', 'soybean', 'mixed', 'other']),
      FormFieldDef(key: 'practice_type', label: 'Practice Type', type: 'enum', required: true,
          options: ['conservation_tillage', 'cover_cropping', 'agroforestry', 'composting', 'crop_rotation', 'biochar', 'other']),
      FormFieldDef(key: 'soil_type', label: 'Soil Type', type: 'enum', required: true,
          options: ['clay', 'loam', 'sandy', 'silt', 'peat']),
      FormFieldDef(key: 'irrigation_method', label: 'Irrigation Method', type: 'enum',
          options: ['rainfed', 'drip', 'flood', 'sprinkler']),
      FormFieldDef(key: 'fertiliser_type', label: 'Fertiliser Type', type: 'enum', required: true,
          options: ['none', 'organic_only', 'synthetic_only', 'both']),
      FormFieldDef(key: 'biomass_retained', label: 'Biomass Retained?', type: 'boolean', required: true),
      FormFieldDef(key: 'livestock_integration', label: 'Livestock Integration?', type: 'boolean'),
      // Measurements
      FormFieldDef(key: 'soil_organic_carbon', label: 'Soil Organic Carbon (%)', type: 'float'),
      FormFieldDef(key: 'soil_moisture', label: 'Soil Moisture (%)', type: 'float'),
      FormFieldDef(key: 'crop_yield', label: 'Crop Yield (tonnes/ha)', type: 'float'),
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
      // System Details
      FormFieldDef(key: 'system_id', label: 'System ID', type: 'string', required: true),
      FormFieldDef(key: 'device_type', label: 'Device Type', type: 'enum', required: true,
          options: ['solar_panel', 'solar_lantern', 'biogas', 'wind', 'micro_hydro', 'solar_water_heater', 'solar_pump']),
      FormFieldDef(key: 'manufacturer', label: 'Manufacturer/Model', type: 'string'),
      FormFieldDef(key: 'serial_number', label: 'Serial Number', type: 'string'),
      // Technical Specs
      FormFieldDef(key: 'capacity_kw', label: 'Installed Capacity (kW)', type: 'float', required: true),
      FormFieldDef(key: 'battery_storage_kwh', label: 'Battery Storage (kWh)', type: 'float'),
      FormFieldDef(key: 'grid_connected', label: 'Grid Connected?', type: 'boolean', required: true),
      FormFieldDef(key: 'daily_output_kwh', label: 'Daily Generation (kWh)', type: 'float'),
      FormFieldDef(key: 'metered', label: 'Metered?', type: 'boolean', required: true),
      // Baseline Data
      FormFieldDef(key: 'baseline_energy', label: 'Baseline Energy Source', type: 'enum', required: true,
          options: ['kerosene_lamp', 'diesel_generator', 'grid_electricity', 'candles', 'firewood', 'charcoal', 'no_access']),
      FormFieldDef(key: 'baseline_fuel_volume', label: 'Monthly Baseline Fuel (L/kWh)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_energy_cost', label: 'Monthly Baseline Cost (₦)', type: 'float', required: true),
      FormFieldDef(key: 'baseline_hours', label: 'Hours of Access Before', type: 'float', required: true),
      // Usage
      FormFieldDef(key: 'households_served', label: 'Households Served', type: 'int', required: true),
      FormFieldDef(key: 'population_served', label: 'Population Served', type: 'int', required: true),
      FormFieldDef(key: 'project_hours', label: 'Hours of Access Now', type: 'float', required: true),
      FormFieldDef(key: 'system_condition', label: 'System Condition', type: 'enum', required: true,
          options: ['good', 'needs_maintenance', 'faulty', 'decommissioned']),
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
      // Plot Details
      FormFieldDef(key: 'plot_id', label: 'Plot ID', type: 'string', required: true),
      FormFieldDef(key: 'community_name', label: 'Community/Owner Name', type: 'string', required: true),
      FormFieldDef(key: 'land_tenure', label: 'Land Tenure', type: 'enum', required: true,
          options: ['owned', 'community', 'government', 'leased']),
      FormFieldDef(key: 'plot_area_hectares', label: 'Plot Area (ha)', type: 'float', required: true),
      FormFieldDef(key: 'ecosystem_type', label: 'Ecosystem Type', type: 'enum', required: true,
          options: ['tropical_dry', 'tropical_moist', 'savanna', 'mangrove', 'riparian', 'degraded_grassland']),
      // Baseline Land Use
      FormFieldDef(key: 'baseline_land_use', label: 'Previous Land Use', type: 'enum', required: true,
          options: ['degraded_cropland', 'bare_eroded', 'degraded_grassland', 'deforested', 'shrubland']),
      FormFieldDef(key: 'years_deforested', label: 'Years Since Deforested', type: 'int'),
      FormFieldDef(key: 'evidence_previous_forest', label: 'Evidence of Prev Forest?', type: 'boolean', required: true),
      FormFieldDef(key: 'baseline_carbon_stock', label: 'Baseline Carbon (tCO2/ha)', type: 'float'),
      // Planting Data
      FormFieldDef(key: 'tree_count', label: 'Trees Planted/Surviving', type: 'int', required: true),
      FormFieldDef(key: 'species', label: 'Species', type: 'string', required: true),
      FormFieldDef(key: 'native_species', label: 'Native Species?', type: 'boolean', required: true),
      FormFieldDef(key: 'planting_pattern', label: 'Planting Pattern', type: 'enum', required: true,
          options: ['row', 'grid', 'random', 'contour']),
      // Survival Monitoring
      FormFieldDef(key: 'survival_rate_pct', label: 'Survival Rate (%)', type: 'float', required: true),
      FormFieldDef(key: 'avg_height_cm', label: 'Average Height (cm)', type: 'float', required: true),
      FormFieldDef(key: 'avg_dbh_cm', label: 'Average DBH (cm)', type: 'float'),
      FormFieldDef(key: 'canopy_cover', label: 'Canopy Cover (%)', type: 'enum',
          options: ['<25', '25-50', '50-75', '>75']),
      FormFieldDef(key: 'threats_observed', label: 'Threats Observed', type: 'enum', required: true,
          options: ['none', 'grazing', 'fire', 'pests', 'drought', 'flooding', 'human']),
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
      // Installation Details
      FormFieldDef(key: 'water_point_id', label: 'Water Point ID', type: 'string', required: true),
      FormFieldDef(key: 'water_source_type', label: 'Source Type', type: 'enum', required: true,
          options: ['borehole', 'handpump', 'solar_pump', 'gravity_fed', 'biosand_filter', 'ceramic_filter', 'chlorination']),
      FormFieldDef(key: 'community_name', label: 'Community Name', type: 'string', required: true),
      // Usage Data
      FormFieldDef(key: 'households_served', label: 'Households Served', type: 'int', required: true),
      FormFieldDef(key: 'population_served', label: 'Population Served', type: 'int', required: true),
      FormFieldDef(key: 'daily_volume_liters', label: 'Daily Volume Dispensed (L)', type: 'float', required: true),
      FormFieldDef(key: 'operating_hours', label: 'Operating Hours/Day', type: 'float', required: true),
      FormFieldDef(key: 'days_operational', label: 'Days Operational/Month', type: 'int', required: true),
      // Baseline Data
      FormFieldDef(key: 'baseline_water_source', label: 'Previous Water Source', type: 'enum', required: true,
          options: ['unprotected_well', 'river_stream', 'rainwater', 'purchased', 'borehole']),
      FormFieldDef(key: 'baseline_treatment', label: 'Previous Treatment', type: 'enum', required: true,
          options: ['boiling', 'chemical', 'none', 'solar_disinfection']),
      FormFieldDef(key: 'baseline_fuel', label: 'Previous Fuel for Boiling', type: 'enum',
          options: ['wood', 'charcoal', 'kerosene', 'lpg']),
      FormFieldDef(key: 'baseline_fuel_cost', label: 'Monthly Fuel Cost Before (₦)', type: 'float'),
      // Water Quality & Status
      FormFieldDef(key: 'water_quality_tested', label: 'Water Quality Tested?', type: 'boolean', required: true),
      FormFieldDef(key: 'test_result', label: 'Test Result', type: 'enum',
          options: ['pass', 'fail']),
      FormFieldDef(key: 'operational_status', label: 'Status', type: 'enum', required: true,
          options: ['active', 'faulty', 'maintenance', 'decommissioned']),
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
