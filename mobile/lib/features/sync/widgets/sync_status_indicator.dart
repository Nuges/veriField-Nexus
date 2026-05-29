import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
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
      return GestureDetector(
        onTap: () => context.push('/sync'),
        child: Container(
          margin: const EdgeInsets.only(right: 16),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF064E3B).withOpacity(0.15),
            border: Border.all(color: const Color(0xFF059669).withOpacity(0.3)),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF10B981).withOpacity(0.08),
                blurRadius: 8,
                spreadRadius: 1,
              )
            ]
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  color: Color(0xFF10B981),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Color(0xFF10B981),
                      blurRadius: 6,
                      spreadRadius: 2,
                    )
                  ]
                ),
              ).animate(onPlay: (controller) => controller.repeat(reverse: true))
               .scale(begin: const Offset(0.8, 0.8), end: const Offset(1.2, 1.2), duration: 1.seconds),
              const SizedBox(width: 6),
              const Icon(
                Icons.wifi_tethering_rounded,
                color: Color(0xFF34D399),
                size: 14,
              ),
              const SizedBox(width: 4),
              const Text(
                'ONLINE',
                style: TextStyle(
                  color: Color(0xFF34D399),
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return GestureDetector(
      onTap: () => context.push('/sync'),
      child: Container(
        margin: const EdgeInsets.only(right: 16),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFF78350F).withOpacity(0.15),
          border: Border.all(color: const Color(0xFFD97706).withOpacity(0.3)),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFF59E0B).withOpacity(0.08),
              blurRadius: 8,
              spreadRadius: 1,
            )
          ]
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 6,
              height: 6,
              decoration: const BoxDecoration(
                color: Color(0xFFF59E0B),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0xFFF59E0B),
                    blurRadius: 6,
                    spreadRadius: 2,
                  )
                ]
              ),
            ).animate(onPlay: (controller) => controller.repeat(reverse: true))
             .scale(begin: const Offset(0.8, 0.8), end: const Offset(1.2, 1.2), duration: 1.seconds),
            const SizedBox(width: 6),
            const Icon(
              Icons.sync_rounded,
              color: Color(0xFFFBBF24),
              size: 14,
            ).animate(onPlay: (controller) => controller.repeat())
             .rotate(duration: 2.seconds),
            const SizedBox(width: 4),
            Text(
              'SYNCING ($_pendingCount)',
              style: const TextStyle(
                color: Color(0xFFFBBF24),
                fontSize: 9,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
