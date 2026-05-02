// =============================================================================
// VeriField Nexus — Property List Screen
// =============================================================================
// Displays all properties with sustainability metrics.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/router/app_router.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';

class PropertyListScreen extends StatefulWidget {
  const PropertyListScreen({super.key});

  @override
  State<PropertyListScreen> createState() => _PropertyListScreenState();
}

class _PropertyListScreenState extends State<PropertyListScreen> {
  List<Map<String, dynamic>> _properties = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProperties();
  }

  Future<void> _loadProperties() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.get('/properties');
      final list = response['properties'] as List? ?? [];
      _properties = list.cast<Map<String, dynamic>>();
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_rounded),
            onPressed: () => context.push(AppRoutes.newProperty),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _properties.isEmpty
              ? VFEmptyState(
                  icon: Icons.inventory_2_outlined,
                  title: 'No assets',
                  subtitle: 'Add an asset to track sustainability',
                  action: VFButton(
                    label: 'Add Asset',
                    icon: Icons.add_rounded,
                    onPressed: () => context.push(AppRoutes.newProperty),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadProperties,
                  color: AppColors.primary,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.base),
                    itemCount: _properties.length,
                    itemBuilder: (context, index) => _buildPropertyCard(_properties[index], index),
                  ),
                ),
    );
  }

  Widget _buildPropertyCard(Map<String, dynamic> property, int index) {
    final typeIcons = {
      'residential': Icons.home_rounded,
      'commercial': Icons.business_rounded,
      'agricultural': Icons.agriculture_rounded,
      'industrial': Icons.factory_rounded,
      'mixed': Icons.domain_rounded,
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    typeIcons[property['property_type']] ?? Icons.home_rounded,
                    color: AppColors.primary, size: 22,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(property['name'] ?? 'Unnamed', style: AppTypography.title.copyWith(fontSize: 16)),
                      if (property['address'] != null)
                        Text(property['address'], style: AppTypography.caption, maxLines: 1, overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    (property['property_type'] ?? 'residential').toString().toUpperCase(),
                    style: AppTypography.caption.copyWith(color: AppColors.accent, fontSize: 10, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: Duration(milliseconds: 50 * index)).slideX(begin: 0.05);
  }
}
