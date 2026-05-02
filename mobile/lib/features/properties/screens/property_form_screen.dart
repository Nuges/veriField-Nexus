// =============================================================================
// VeriField Nexus — Property Form Screen
// =============================================================================
// Create or edit a property for the real estate sustainability module.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';
import '../../../services/location_service.dart';

class PropertyFormScreen extends StatefulWidget {
  const PropertyFormScreen({super.key});

  @override
  State<PropertyFormScreen> createState() => _PropertyFormScreenState();
}

class _PropertyFormScreenState extends State<PropertyFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _addressController = TextEditingController();
  String _selectedType = 'cookstove';
  Map<String, double>? _locationData;
  bool _isSubmitting = false;
  bool _isCapturingLocation = false;

  final List<Map<String, dynamic>> _propertyTypes = [
    {'id': 'cookstove', 'label': 'Cookstove', 'icon': Icons.local_fire_department_rounded},
    {'id': 'property', 'label': 'Property', 'icon': Icons.home_rounded},
    {'id': 'agriculture', 'label': 'Agriculture Plot', 'icon': Icons.agriculture_rounded},
    {'id': 'solar', 'label': 'Solar Installation', 'icon': Icons.solar_power_rounded},
    {'id': 'other', 'label': 'Other Asset', 'icon': Icons.inventory_2_rounded},
  ];

  @override
  void initState() {
    super.initState();
    _captureLocation();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _captureLocation() async {
    setState(() => _isCapturingLocation = true);
    _locationData = await LocationService.getLocationData();
    if (mounted) setState(() => _isCapturingLocation = false);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);

    try {
      await ApiService.post('/properties', body: {
        'name': _nameController.text.trim(),
        'address': _addressController.text.trim().isNotEmpty ? _addressController.text.trim() : null,
        'property_type': _selectedType,
        'latitude': _locationData?['latitude'],
        'longitude': _locationData?['longitude'],
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Asset created! 📦')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Asset')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              VFTextField(
                label: 'Asset Name',
                hint: 'Enter asset name',
                controller: _nameController,
                prefixIcon: const Icon(Icons.home_outlined, color: AppColors.textTertiary),
                validator: (v) => v == null || v.isEmpty ? 'Name is required' : null,
              ).animate().fadeIn(delay: 100.ms),
              const SizedBox(height: AppSpacing.base),

              VFTextField(
                label: 'Address (Optional)',
                hint: 'Enter full address',
                controller: _addressController,
                maxLines: 2,
                prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.textTertiary),
              ).animate().fadeIn(delay: 200.ms),
              const SizedBox(height: AppSpacing.xl),

              // Property Type
              Text('Asset Type', style: AppTypography.bodySmall),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: _propertyTypes.map((type) {
                  final isSelected = _selectedType == type['id'];
                  return GestureDetector(
                    onTap: () => setState(() => _selectedType = type['id']),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.primary.withValues(alpha: 0.15) : AppColors.surface,
                        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                        border: Border.all(color: isSelected ? AppColors.primary : AppColors.border),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(type['icon'] as IconData, size: 18, color: isSelected ? AppColors.primary : AppColors.textTertiary),
                          const SizedBox(width: 8),
                          Text(type['label'] as String, style: AppTypography.bodySmall.copyWith(
                            color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
                          )),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ).animate().fadeIn(delay: 300.ms),
              const SizedBox(height: AppSpacing.xl),

              // GPS
              VFCard(
                child: Row(
                  children: [
                    Icon(
                      _locationData != null ? Icons.gps_fixed : Icons.gps_not_fixed,
                      color: _locationData != null ? AppColors.primary : AppColors.textTertiary,
                    ),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: Text(
                        _isCapturingLocation ? 'Getting location...'
                            : _locationData != null
                                ? '${_locationData!['latitude']!.toStringAsFixed(4)}, ${_locationData!['longitude']!.toStringAsFixed(4)}'
                                : 'Location unavailable',
                        style: AppTypography.bodySmall,
                      ),
                    ),
                    IconButton(icon: const Icon(Icons.refresh, color: AppColors.textTertiary), onPressed: _captureLocation),
                  ],
                ),
              ).animate().fadeIn(delay: 400.ms),
              const SizedBox(height: AppSpacing.xl),

              SizedBox(
                width: double.infinity,
                child: VFButton(
                  label: 'Create Asset',
                  onPressed: _submit,
                  isLoading: _isSubmitting,
                  icon: Icons.add_box_rounded,
                ),
              ).animate().fadeIn(delay: 500.ms),
            ],
          ),
        ),
      ),
    );
  }
}
