import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';

class AuditListScreen extends StatefulWidget {
  const AuditListScreen({super.key});

  @override
  State<AuditListScreen> createState() => _AuditListScreenState();
}

class _AuditListScreenState extends State<AuditListScreen> {
  // Mock data for audits
  final List<Map<String, dynamic>> _audits = [
    {
      'id': 'a1',
      'title': 'High-Risk Farm Inspection',
      'type': 'farming',
      'status': 'pending',
      'priority': 'high',
      'dueDate': '2026-05-04',
      'location': 'Region 12, Plot 4A',
      'reason': 'Anomaly Detected: GPS inconsistency',
    },
    {
      'id': 'a2',
      'title': 'Clean Cookstove Verification',
      'type': 'cooking',
      'status': 'in_progress',
      'priority': 'medium',
      'dueDate': '2026-05-05',
      'location': 'Village Center, House 42',
      'reason': 'Routine cross-check',
    },
    {
      'id': 'a3',
      'title': 'Energy Meter Audit',
      'type': 'energy',
      'status': 'completed',
      'priority': 'low',
      'dueDate': '2026-05-01',
      'location': 'District 9, Building B',
      'reason': 'Monthly verification',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Audit Tasks', style: AppTypography.h3),
        centerTitle: false,
      ),
      body: _audits.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.fact_check_outlined, size: 64, color: AppColors.textTertiary),
                  const SizedBox(height: AppSpacing.md),
                  Text('No pending audits', style: AppTypography.title),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Assigned audits will appear here.',
                    style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: _audits.length,
              itemBuilder: (context, index) {
                final audit = _audits[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: VFCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            _buildPriorityChip(audit['priority']),
                            _buildStatusChip(audit['status']),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Text(audit['title'], style: AppTypography.title),
                        const SizedBox(height: AppSpacing.xs),
                        Row(
                          children: [
                            const Icon(Icons.location_on_outlined, size: 16, color: AppColors.textSecondary),
                            const SizedBox(width: AppSpacing.xs),
                            Text(audit['location'], style: AppTypography.bodySmall),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Container(
                          padding: const EdgeInsets.all(AppSpacing.sm),
                          decoration: BoxDecoration(
                            color: AppColors.error.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.info_outline, size: 16, color: AppColors.error),
                              const SizedBox(width: AppSpacing.sm),
                              Expanded(
                                child: Text(
                                  audit['reason'],
                                  style: AppTypography.caption.copyWith(color: AppColors.error),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Due: ${audit['dueDate']}', style: AppTypography.caption),
                            if (audit['status'] != 'completed')
                              SizedBox(
                                height: 32,
                                child: ElevatedButton(
                                  onPressed: () {
                                    // Handle start audit
                                  },
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppColors.primary,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                                  ),
                                  child: const Text('Start Audit'),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }

  Widget _buildPriorityChip(String priority) {
    Color color;
    switch (priority) {
      case 'high': color = AppColors.error; break;
      case 'medium': color = AppColors.warning; break;
      default: color = AppColors.primary;
    }
    return Row(
      children: [
        Icon(Icons.flag, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          '${priority.toUpperCase()} PRIORITY',
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
      case 'in_progress': color = AppColors.primary; label = 'In Progress'; break;
      case 'completed': color = AppColors.trustHigh; label = 'Completed'; break;
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
