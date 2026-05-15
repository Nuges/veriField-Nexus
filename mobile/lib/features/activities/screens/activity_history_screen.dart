// =============================================================================
// VeriField Nexus — Activity History Screen
// =============================================================================
// Displays a list of all submitted activities with trust score badges,
// sync status, and filtering capabilities.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import 'dart:async';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';
import '../../../services/sync_service.dart';
import '../../../services/local_db_service.dart';
import '../../sync/widgets/sync_status_indicator.dart';
import '../../../core/utils/refresh_event_bus.dart';

class ActivityHistoryScreen extends StatefulWidget {
  const ActivityHistoryScreen({super.key});

  @override
  State<ActivityHistoryScreen> createState() => _ActivityHistoryScreenState();
}

class _ActivityHistoryScreenState extends State<ActivityHistoryScreen> {
  List<Map<String, dynamic>> _activities = [];
  bool _isLoading = true;
  bool _isOnline = true;
  int _pendingCount = 0;
  StreamSubscription? _refreshSub;

  @override
  void initState() {
    super.initState();
    _loadActivities();
    _refreshSub = RefreshEventBus.onActivityRefresh.listen((_) {
      if (mounted) _loadActivities();
    });
  }

  @override
  void dispose() {
    _refreshSub?.cancel();
    super.dispose();
  }

  /// Load activities from API (online) or local cache (offline).
  Future<void> _loadActivities() async {
    setState(() => _isLoading = true);

    try {
      _isOnline = await SyncService.isOnline();
      _pendingCount = await LocalDbService.getPendingCount();

      if (_isOnline) {
        // Sync pending activities first
        if (_pendingCount > 0) await SyncService.syncPendingActivities();

        final response = await ApiService.get('/activities?per_page=50');
        final activitiesList = response['data'] as List? ?? [];
        _activities = activitiesList.cast<Map<String, dynamic>>();

        // Update pending count after sync
        _pendingCount = await LocalDbService.getPendingCount();
      } else {
        // Offline: load from cache
        _activities = await LocalDbService.getCachedActivities();
      }
    } catch (e) {
      // Fallback to cached data on error
      _activities = await LocalDbService.getCachedActivities();
    }

    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('VeriField Nexus'),
        actions: const [
          SyncStatusIndicator(),
        ],
      ),
      body: Column(
        children: [
          // Offline/sync status banner
          SyncStatusBanner(isOnline: _isOnline, pendingCount: _pendingCount),

          // Activity list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
                : _activities.isEmpty
                    ? VFEmptyState(
                        icon: Icons.assignment_outlined,
                        title: 'No activities yet',
                        subtitle: 'Tap the button below to log your first field activity',
                      )
                    : RefreshIndicator(
                        onRefresh: _loadActivities,
                        color: AppColors.primary,
                        child: ListView.builder(
                          padding: const EdgeInsets.all(AppSpacing.base),
                          itemCount: _activities.length,
                          itemBuilder: (context, index) {
                            return _buildActivityCard(_activities[index], index);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  /// Build a single activity card with trust score badge.
  Widget _buildActivityCard(Map<String, dynamic> activity, int index) {
    final activityType = activity['activity_type'] ?? 'other';
    final trustScore = activity['trust_score'] as num?;
    final status = activity['status'] ?? 'pending';
    final capturedAt = activity['captured_at'] ?? activity['created_at'] ?? '';

    // Activity type metadata
    final typeInfo = _getTypeInfo(activityType);

    // Format date
    String dateStr = '';
    try {
      final date = DateTime.parse(capturedAt);
      dateStr = DateFormat('MMM d, yyyy • h:mm a').format(date);
    } catch (_) {
      dateStr = capturedAt;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        onTap: () {
          final id = activity['id'];
          if (id != null) context.push('/home/activity/$id');
        },
        child: Row(
          children: [
            // Activity type icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: (typeInfo['color'] as Color).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(typeInfo['icon'] as IconData, color: typeInfo['color'] as Color, size: 24),
            ),
            const SizedBox(width: AppSpacing.md),

            // Activity info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(typeInfo['label'] as String, style: AppTypography.title.copyWith(fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(dateStr, style: AppTypography.caption),
                  if (activity['description'] != null && activity['description'].toString().isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        activity['description'],
                        style: AppTypography.bodySmall,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),

            // Trust score gauge
            Column(
              children: [
                TrustScoreGauge(score: trustScore?.toDouble(), size: 44),
                const SizedBox(height: 4),
                _buildStatusChip(status),
              ],
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: Duration(milliseconds: 50 * index)).slideX(begin: 0.05);
  }

  /// Get activity type display info.
  Map<String, dynamic> _getTypeInfo(String type) {
    switch (type.toUpperCase()) {
      // New Smart Installation types
      case 'CLEAN_COOKING': return {'label': 'Clean Cooking', 'icon': Icons.local_fire_department_rounded, 'color': AppColors.warning};
      case 'AGRICULTURE': return {'label': 'Agriculture', 'icon': Icons.grass_rounded, 'color': AppColors.primary};
      case 'ENERGY_USE': return {'label': 'Energy Use', 'icon': Icons.bolt_rounded, 'color': AppColors.accent};
      case 'FORESTRY_LAND_USE': return {'label': 'Forestry & Land', 'icon': Icons.park_rounded, 'color': const Color(0xFF2E7D32)};
      case 'SAFE_WATER': return {'label': 'Safe Water', 'icon': Icons.water_drop_rounded, 'color': const Color(0xFF0288D1)};
      case 'TRANSPORT_MOBILITY': return {'label': 'Transport', 'icon': Icons.directions_car_rounded, 'color': AppColors.accentPurple};
      case 'OTHER': return {'label': 'Other', 'icon': Icons.more_horiz_rounded, 'color': AppColors.textTertiary};
      // Legacy types (backwards compatibility)
      case 'COOKING': return {'label': 'Clean Cooking', 'icon': Icons.local_fire_department_rounded, 'color': AppColors.warning};
      case 'FARMING': return {'label': 'Agriculture', 'icon': Icons.grass_rounded, 'color': AppColors.primary};
      case 'ENERGY': return {'label': 'Energy Use', 'icon': Icons.bolt_rounded, 'color': AppColors.accent};
      default: return {'label': type.replaceAll('_', ' '), 'icon': Icons.category_rounded, 'color': AppColors.textTertiary};
    }
  }

  /// Build a status chip badge.
  Widget _buildStatusChip(String status) {
    Color color;
    switch (status) {
      case 'verified': color = AppColors.trustHigh; break;
      case 'review': color = AppColors.trustMedium; break;
      case 'flagged': color = AppColors.trustLow; break;
      default: color = AppColors.textTertiary;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        status.toUpperCase(),
        style: AppTypography.caption.copyWith(color: color, fontSize: 9, fontWeight: FontWeight.w700),
      ),
    );
  }
}
