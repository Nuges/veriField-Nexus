// =============================================================================
// VeriField Nexus — Sync Queue Screen
// =============================================================================
// Displays pending offline activities, retry attempts, and detailed server
// validation logs. Allows manual triggers of "Retry All" or "Retry Failed".
// =============================================================================

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../services/local_db_service.dart';
import '../../../services/sync_service.dart';

class SyncQueueScreen extends StatefulWidget {
  const SyncQueueScreen({super.key});

  @override
  State<SyncQueueScreen> createState() => _SyncQueueScreenState();
}

class _SyncQueueScreenState extends State<SyncQueueScreen> {
  List<Map<String, dynamic>> _pendingActivities = [];
  bool _isLoading = true;
  bool _isSyncing = false;
  String? _syncMessage;
  String? _lastSyncTime;

  @override
  void initState() {
    super.initState();
    _loadPendingActivities();
    _loadLastSyncTime();
  }

  Future<void> _loadLastSyncTime() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      setState(() {
        _lastSyncTime = prefs.getString('last_sync_time');
      });
    } catch (e) {
      debugPrint('Error loading last sync time: $e');
    }
  }

  Future<void> _loadPendingActivities() async {
    setState(() => _isLoading = true);
    try {
      final activities = await LocalDbService.getPendingActivities();
      setState(() {
        _pendingActivities = activities;
      });
    } catch (e) {
      debugPrint('Error loading pending activities: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _triggerSync({bool failedOnly = false, bool forceAll = false}) async {
    setState(() {
      _isSyncing = true;
      _syncMessage = 'Syncing...';
    });

    try {
      final result = await SyncService.syncPendingActivities(
        failedOnly: failedOnly,
        forceAll: forceAll,
      );
      setState(() {
        _syncMessage = result.message;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.message)),
        );
      }
      await _loadPendingActivities();
      await _loadLastSyncTime();
    } catch (e) {
      setState(() {
        _syncMessage = 'Sync failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSyncing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: Text('Sync Queue', style: AppTypography.title),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.primary),
            onPressed: _isSyncing ? null : () {
              _loadPendingActivities();
              _loadLastSyncTime();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                _buildSyncHeader(),
                Expanded(
                  child: _pendingActivities.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.cloud_done_rounded, size: 48, color: AppColors.primary),
                              const SizedBox(height: 12),
                              Text(
                                'No pending items. You are fully synced!',
                                style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          itemCount: _pendingActivities.length,
                          itemBuilder: (context, index) {
                            final item = _pendingActivities[index];
                            final isFailed = item['sync_status'] == 'failed';
                            final retryCount = item['retry_count'] ?? 0;
                            final errorMsg = item['error_message'] as String?;
                            final activityType = item['activity_type'] ?? 'Activity';
                            final capturedAt = item['captured_at'] ?? item['created_at'] ?? 'N/A';
                            
                            return Card(
                              color: AppColors.surfaceLight,
                              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                                side: BorderSide(
                                  color: isFailed ? AppColors.error.withValues(alpha: 0.5) : AppColors.border,
                                  width: 1,
                                ),
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(16.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.center,
                                      children: [
                                        Icon(
                                          isFailed ? Icons.sync_problem_rounded : Icons.hourglass_empty_rounded,
                                          color: isFailed ? AppColors.error : Colors.amber,
                                          size: 24,
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                activityType.replaceAll('_', ' ').toUpperCase(),
                                                style: AppTypography.title.copyWith(fontSize: 14, fontWeight: FontWeight.bold),
                                              ),
                                              const SizedBox(height: 4),
                                              Text(
                                                'Captured: $capturedAt',
                                                style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, fontSize: 11),
                                              ),
                                            ],
                                          ),
                                        ),
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.end,
                                          children: [
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                              decoration: BoxDecoration(
                                                color: isFailed ? AppColors.error.withValues(alpha: 0.15) : Colors.amber.withValues(alpha: 0.15),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Text(
                                                isFailed ? 'FAILED' : 'PENDING',
                                                style: TextStyle(
                                                  color: isFailed ? AppColors.error : Colors.amber,
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              'Retries: $retryCount/5',
                                              style: TextStyle(
                                                color: retryCount >= 5 ? AppColors.error : AppColors.textTertiary,
                                                fontSize: 10,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                    if (isFailed && errorMsg != null && errorMsg.isNotEmpty) ...[
                                      const SizedBox(height: 12),
                                      Container(
                                        width: double.infinity,
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: AppColors.background,
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(color: AppColors.error.withValues(alpha: 0.2)),
                                        ),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                const Icon(Icons.warning_amber_rounded, size: 14, color: AppColors.error),
                                                const SizedBox(width: 6),
                                                Text(
                                                  '⚠ Validation Error:',
                                                  style: TextStyle(
                                                    color: AppColors.error,
                                                    fontSize: 11,
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            const SizedBox(height: 6),
                                            Text(
                                              errorMsg,
                                              style: const TextStyle(
                                                color: Colors.redAccent,
                                                fontSize: 11,
                                                fontFamily: 'monospace',
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildSyncHeader() {
    final pendingCount = _pendingActivities.where((x) => x['sync_status'] == 'pending').length;
    final failedCount = _pendingActivities.where((x) => x['sync_status'] == 'failed').length;

    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: const BoxDecoration(
        color: AppColors.surfaceLight,
        border: Border(bottom: BorderSide(color: AppColors.border, width: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Queue Items: ${_pendingActivities.length}',
                    style: AppTypography.title.copyWith(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.amber.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '🟡 Pending: $pendingCount',
                          style: const TextStyle(color: Colors.amber, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.error.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '🔴 Failed: $failedCount',
                          style: const TextStyle(color: AppColors.error, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'Last Sync:',
                    style: AppTypography.caption.copyWith(color: AppColors.textTertiary),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _lastSyncTime ?? 'Never',
                    style: AppTypography.caption.copyWith(fontWeight: FontWeight.bold, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ],
          ),
          if (_syncMessage != null) ...[
            const SizedBox(height: 10),
            Text(
              _syncMessage!,
              style: TextStyle(
                color: _syncMessage!.contains('failed') || _syncMessage!.contains('Failed') ? Colors.red : Colors.green,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _isSyncing || _pendingActivities.isEmpty
                      ? null
                      : () => _triggerSync(forceAll: true),
                  icon: _isSyncing
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.sync_rounded, size: 16),
                  label: const Text('Retry All', style: TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _isSyncing || failedCount == 0
                      ? null
                      : () => _triggerSync(failedOnly: true),
                  icon: const Icon(Icons.sync_problem_rounded, size: 16),
                  label: const Text('Retry Failed', style: TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.error,
                    side: BorderSide(color: failedCount > 0 ? AppColors.error : AppColors.border),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
