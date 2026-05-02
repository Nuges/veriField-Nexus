import 'package:flutter/material.dart';
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

  @override
  void initState() {
    super.initState();
    _loadPendingActivities();
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

  Future<void> _triggerSync() async {
    setState(() {
      _isSyncing = true;
      _syncMessage = 'Syncing...';
    });

    try {
      final result = await SyncService.syncPendingActivities();
      setState(() {
        _syncMessage = result.message;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.message)),
        );
      }
      await _loadPendingActivities();
    } catch (e) {
      setState(() {
        _syncMessage = 'Sync failed: $e';
      });
    } finally {
      setState(() {
        _isSyncing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Sync Queue', style: AppTypography.h3),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isSyncing ? null : _loadPendingActivities,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                _buildSyncHeader(),
                Expanded(
                  child: _pendingActivities.isEmpty
                      ? const Center(
                          child: Text('No pending items. You are fully synced!'),
                        )
                      : ListView.builder(
                          itemCount: _pendingActivities.length,
                          itemBuilder: (context, index) {
                            final item = _pendingActivities[index];
                            return ListTile(
                              leading: const Icon(Icons.cloud_upload_outlined, color: AppColors.primary),
                              title: Text(item['activity_type'] ?? 'Activity'),
                              subtitle: Text('Recorded: ${item['recorded_at']}'),
                              trailing: const Icon(Icons.pending_actions),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildSyncHeader() {
    return Container(
      padding: const EdgeInsets.all(16.0),
      color: AppColors.backgroundAlt,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Pending Items: ${_pendingActivities.length}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              if (_syncMessage != null)
                Text(
                  _syncMessage!,
                  style: TextStyle(
                    color: _syncMessage!.contains('failed') ? Colors.red : Colors.green,
                    fontSize: 12,
                  ),
                ),
            ],
          ),
          ElevatedButton.icon(
            onPressed: _isSyncing || _pendingActivities.isEmpty ? null : _triggerSync,
            icon: _isSyncing
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.sync),
            label: const Text('Sync Now'),
          ),
        ],
      ),
    );
  }
}
