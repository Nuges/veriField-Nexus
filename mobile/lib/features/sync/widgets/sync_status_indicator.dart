import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../services/local_db_service.dart';
import '../../../core/theme/app_colors.dart';

class SyncStatusIndicator extends StatefulWidget {
  const SyncStatusIndicator({super.key});

  @override
  State<SyncStatusIndicator> createState() => _SyncStatusIndicatorState();
}

class _SyncStatusIndicatorState extends State<SyncStatusIndicator> {
  int _pendingCount = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _checkPendingCount();
    // Poll every 10 seconds to update sync status
    _timer = Timer.periodic(const Duration(seconds: 10), (_) {
      _checkPendingCount();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _checkPendingCount() async {
    try {
      final count = await LocalDbService.getPendingCount();
      if (mounted && _pendingCount != count) {
        setState(() {
          _pendingCount = count;
        });
      }
    } catch (e) {
      debugPrint('Error checking pending count: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_pendingCount == 0) {
      return IconButton(
        icon: const Icon(Icons.cloud_done, color: Colors.green),
        tooltip: 'All data synced',
        onPressed: () => context.push('/sync'),
      );
    }

    return Stack(
      alignment: Alignment.center,
      children: [
        IconButton(
          icon: const Icon(Icons.cloud_upload_outlined, color: Colors.orange),
          tooltip: 'Pending uploads',
          onPressed: () => context.push('/sync'),
        ),
        Positioned(
          right: 8,
          top: 8,
          child: Container(
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(
              color: Colors.red,
              borderRadius: BorderRadius.circular(10),
            ),
            constraints: const BoxConstraints(
              minWidth: 16,
              minHeight: 16,
            ),
            child: Text(
              '$_pendingCount',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ],
    );
  }
}
