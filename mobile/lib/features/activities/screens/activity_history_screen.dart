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
import 'dart:convert';
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
  Map<String, dynamic>? _user;
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

        final response = await ApiService.get('/installations?per_page=50');
        final activitiesList = response['activities'] as List? ?? [];
        _activities = activitiesList.cast<Map<String, dynamic>>();

        // Fetch user details for welcome header
        try {
          _user = await ApiService.get('/auth/me');
        } catch (_) {}

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
        title: Row(
          children: [
            const Icon(Icons.energy_savings_leaf_rounded, color: AppColors.primary, size: 20),
            const SizedBox(width: 8),
            const Text('VeriField Nexus'),
          ],
        ),
        actions: [
          const SyncStatusIndicator(),
          if (_user != null) ...[
            const SizedBox(width: 8),
            Center(
              child: Text(
                'Hi, ${_user!['full_name'].toString().split(' ')[0]}',
                style: AppTypography.bodySmall.copyWith(
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary,
                ),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: () {
                context.go('/profile');
              },
              child: Container(
                margin: const EdgeInsets.only(right: AppSpacing.md),
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.primary.withValues(alpha: 0.3), width: 1.5),
                  image: _user!['avatar_url'] != null && _user!['avatar_url'].toString().isNotEmpty
                      ? DecorationImage(
                          image: NetworkImage(ApiService.formatImageUrl(_user!['avatar_url'].toString())),
                          fit: BoxFit.cover,
                        )
                      : null,
                ),
                child: _user!['avatar_url'] == null || _user!['avatar_url'].toString().isEmpty
                    ? Center(
                        child: Text(
                          _user!['full_name'].toString().substring(0, 1).toUpperCase(),
                          style: AppTypography.caption.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.bold,
                            fontSize: 10,
                          ),
                        ),
                      )
                    : null,
              ),
            ),
          ] else
            const SizedBox(width: AppSpacing.md),
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

  String _formatStoveModel(String model) {
    if (model.isEmpty) return '';
    return model
        .replaceAll('_', ' ')
        .replaceAll('-', ' ')
        .split(' ')
        .map((word) => word.isEmpty ? '' : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  /// Build a single activity card with trust score badge.
  Widget _buildActivityCard(Map<String, dynamic> activity, int index) {
    final activityType = activity['activity_type'] ?? 'other';
    final trustScore = activity['trust_score'] as num?;
    final status = activity['status'] ?? 'pending';
    final capturedAt = activity['captured_at'] ?? activity['created_at'] ?? '';
    
    // Parse dynamic activity data safely
    Map<String, dynamic>? activityData;
    if (activity['activity_data'] is Map) {
      activityData = Map<String, dynamic>.from(activity['activity_data']);
    } else if (activity['activity_data'] is String) {
      try {
        activityData = Map<String, dynamic>.from(jsonDecode(activity['activity_data']));
      } catch (_) {}
    }

    // Resolve a highly-descriptive dynamic title based on activity type
    String displayTitle;
    if (activityType.toUpperCase() == 'HYBRID_ENERGY') {
      // Hybrid Energy display title
      displayTitle = 'Hybrid Energy System';
      if (activityData != null) {
        final ownerName = activityData['owner_name']?.toString() ?? '';
        final solarCapacity = activityData['solar_capacity_kwp']?.toString() ?? '';
        final siteId = activityData['site_id']?.toString() ?? '';

        if (ownerName.isNotEmpty && solarCapacity.isNotEmpty) {
          displayTitle = '$ownerName • ${solarCapacity}kWp Solar';
        } else if (ownerName.isNotEmpty) {
          displayTitle = 'Energy: $ownerName';
        } else if (siteId.isNotEmpty) {
          displayTitle = 'Site: $siteId';
        }
      }
    } else {
      // Clean Cooking display title (default)
      displayTitle = 'Clean Cooking Stove';
      if (activityData != null) {
        final headName = activityData['head_name']?.toString() ?? '';
        final stoveModel = activityData['stove_model']?.toString() ?? '';
        final serialNumber = activityData['serial_number']?.toString() ?? '';

        if (headName.isNotEmpty && stoveModel.isNotEmpty) {
          displayTitle = '${_formatStoveModel(stoveModel)} • $headName';
        } else if (headName.isNotEmpty) {
          displayTitle = 'Stove: $headName';
        } else if (stoveModel.isNotEmpty) {
          displayTitle = '${_formatStoveModel(stoveModel)} Installation';
        } else if (serialNumber.isNotEmpty) {
          displayTitle = 'Stove SN: $serialNumber';
        }
      }
    }

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
                color: (typeInfo['color'] as Color).withOpacity(0.15),
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
                  Text(displayTitle, style: AppTypography.title.copyWith(fontSize: 15, fontWeight: FontWeight.bold)),
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
      case 'CLEAN_COOKING':
      case 'COOKING':
        return {'label': 'Clean Cooking', 'icon': Icons.soup_kitchen_rounded, 'color': AppColors.warning};
      case 'HYBRID_ENERGY':
        return {'label': 'Hybrid Energy', 'icon': Icons.solar_power_rounded, 'color': Color(0xFFF59E0B)};
      default:
        return {'label': 'Activity', 'icon': Icons.assignment_outlined, 'color': AppColors.textSecondary};
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
