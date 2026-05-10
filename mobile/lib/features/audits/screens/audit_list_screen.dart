// =============================================================================
// VeriField Nexus — Audit List Screen (Live API)
// =============================================================================
// Displays assigned audit tasks fetched from the backend API.
// No hardcoded data — fully production-ready.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';

class AuditListScreen extends StatefulWidget {
  const AuditListScreen({super.key});

  @override
  State<AuditListScreen> createState() => _AuditListScreenState();
}

class _AuditListScreenState extends State<AuditListScreen> {
  List<Map<String, dynamic>> _audits = [];
  bool _isLoading = true;
  String? _error;
  String _statusFilter = 'all';

  @override
  void initState() {
    super.initState();
    _loadAudits();
  }

  Future<void> _loadAudits() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final endpoint = _statusFilter == 'all'
          ? '/audits?per_page=50'
          : '/audits?status=$_statusFilter&per_page=50';
      final response = await ApiService.get(endpoint);
      final auditsList = response['audits'] as List? ?? [];
      setState(() {
        _audits = auditsList.cast<Map<String, dynamic>>();
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _updateAuditStatus(String auditId, String newStatus) async {
    try {
      await ApiService.patch('/audits/$auditId', body: {'status': newStatus});
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audit marked as $newStatus')),
        );
      }
      await _loadAudits();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Audit Tasks', style: AppTypography.title),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAudits,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          _buildFilterBar(),

          // Content
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.primary),
                  )
                : _error != null
                    ? _buildErrorState()
                    : _audits.isEmpty
                        ? VFEmptyState(
                            icon: Icons.fact_check_outlined,
                            title: 'No audit tasks',
                            subtitle: _statusFilter == 'all'
                                ? 'No audits have been assigned yet.'
                                : 'No audits with status "$_statusFilter".',
                          )
                        : RefreshIndicator(
                            onRefresh: _loadAudits,
                            color: AppColors.primary,
                            child: ListView.builder(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              itemCount: _audits.length,
                              itemBuilder: (context, index) {
                                return _buildAuditCard(_audits[index], index);
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    final filters = ['all', 'pending', 'completed', 'failed'];
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: filters.map((filter) {
            final isActive = _statusFilter == filter;
            return Padding(
              padding: const EdgeInsets.only(right: AppSpacing.sm),
              child: ChoiceChip(
                label: Text(filter[0].toUpperCase() + filter.substring(1)),
                selected: isActive,
                onSelected: (_) {
                  setState(() => _statusFilter = filter);
                  _loadAudits();
                },
                selectedColor: AppColors.primary.withValues(alpha: 0.2),
                labelStyle: AppTypography.caption.copyWith(
                  color: isActive ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 64, color: AppColors.textTertiary),
            const SizedBox(height: AppSpacing.md),
            Text('Could not load audits', style: AppTypography.title),
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error ?? 'Unknown error',
              style: AppTypography.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            VFButton(label: 'Retry', onPressed: _loadAudits, icon: Icons.refresh),
          ],
        ),
      ),
    );
  }

  Widget _buildAuditCard(Map<String, dynamic> audit, int index) {
    final status = audit['status'] ?? 'pending';
    final deadline = audit['deadline'];
    final propertyName = audit['property_name'] ?? 'Unknown Asset';
    final propertyAddress = audit['property_address'] ?? '';
    final propertyType = audit['property_type'] ?? '';
    final agentName = audit['agent_name'] ?? '';

    // Format deadline
    String deadlineStr = '';
    if (deadline != null) {
      try {
        final date = DateTime.parse(deadline);
        deadlineStr = DateFormat('MMM d, yyyy').format(date);
      } catch (_) {
        deadlineStr = deadline.toString();
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (propertyType.isNotEmpty) _buildTypeChip(propertyType),
                _buildStatusChip(status),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(propertyName, style: AppTypography.title),
            if (propertyAddress.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  const Icon(Icons.location_on_outlined, size: 16, color: AppColors.textSecondary),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: Text(propertyAddress, style: AppTypography.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ],
            if (agentName.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  const Icon(Icons.person_outline, size: 16, color: AppColors.textSecondary),
                  const SizedBox(width: AppSpacing.xs),
                  Text('Assigned: $agentName', style: AppTypography.caption),
                ],
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (deadlineStr.isNotEmpty)
                  Text('Due: $deadlineStr', style: AppTypography.caption),
                if (status == 'pending')
                  SizedBox(
                    height: 32,
                    child: ElevatedButton(
                      onPressed: () => _updateAuditStatus(audit['id'], 'completed'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                      ),
                      child: const Text('Complete'),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: Duration(milliseconds: 50 * index)).slideX(begin: 0.05);
  }

  Widget _buildTypeChip(String type) {
    IconData icon;
    Color color;
    switch (type) {
      case 'cooking': icon = Icons.local_fire_department; color = AppColors.warning; break;
      case 'farming': icon = Icons.grass; color = AppColors.primary; break;
      case 'energy': icon = Icons.bolt; color = AppColors.accent; break;
      default: icon = Icons.home; color = AppColors.textTertiary;
    }
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          type.toUpperCase(),
          style: AppTypography.caption.copyWith(color: color, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildStatusChip(String status) {
    Color color;
    String label;
    switch (status) {
      case 'pending': color = AppColors.warning; label = 'Pending'; break;
      case 'completed': color = AppColors.trustHigh; label = 'Completed'; break;
      case 'failed': color = AppColors.trustLow; label = 'Failed'; break;
      default: color = AppColors.textTertiary; label = 'Unknown';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        label,
        style: AppTypography.caption.copyWith(color: color, fontWeight: FontWeight.bold),
      ),
    );
  }
}
