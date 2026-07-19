// =============================================================================
// VeriField Nexus — Bottom Navigation Shell
// =============================================================================
// Main app shell with animated bottom navigation bar.
// Wraps all main screens (Home, Properties, Profile).
// =============================================================================

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';
import '../../core/utils/refresh_event_bus.dart';
import '../../services/api_service.dart';
import 'shared_widgets.dart';

/// Shell widget providing bottom navigation across main app sections.
class VFShell extends StatefulWidget {
  final Widget child;

  const VFShell({super.key, required this.child});

  @override
  State<VFShell> createState() => _VFShellState();
}

class _VFShellState extends State<VFShell> {
  Timer? _notificationTimer;
  final Set<String> _seenAuditIds = {};
  bool _isFirstFetch = true;
  String? _myUserId;

  @override
  void initState() {
    super.initState();
    _startNotificationCheck();
  }

  @override
  void dispose() {
    _notificationTimer?.cancel();
    super.dispose();
  }

  void _startNotificationCheck() {
    // Check for new audit tasks periodically (every 10 seconds)
    _notificationTimer = Timer.periodic(const Duration(seconds: 10), (timer) async {
      if (!mounted) return;
      
      try {
        // Retrieve my user ID if not cached yet
        if (_myUserId == null) {
          try {
            final user = await ApiService.get('/auth/me');
            _myUserId = user['id'] as String?;
          } catch (_) {
            return; // Exit check if we are not authenticated yet
          }
        }

        if (_myUserId == null) return;

        // Query the audits list from the new verification domain
        final response = await ApiService.get('/verification/tasks');
        final audits = (response is List) ? response as List<dynamic> : [];
        
        bool hasNewAudit = false;

        for (var audit in audits) {
          final id = audit['id'] as String?;
          final assignedAgent = audit['verifier_id'] as String?;
          final status = audit['status'] ?? 'ASSIGNED';
          
          if (id == null || assignedAgent != _myUserId) continue;
          
          if (!_seenAuditIds.contains(id)) {
            _seenAuditIds.add(id);
            
            // Only notify on subsequent fetches so we don't spam on launch
            if (!_isFirstFetch) {
              if (status == 'ASSIGNED' || status == 'IN_PROGRESS') {
                hasNewAudit = true;
              }
            }
          }
        }

        if (_isFirstFetch) {
          _isFirstFetch = false;
        } else if (hasNewAudit && mounted) {
          // Trigger floating toast notification in active context!
          VFNotification.showSuccess(
            context, 
            'New Audit Task Assigned! 🛡️\nCheck your active assignments roster.',
          );
          // Auto-trigger audits screen UI update
          RefreshEventBus.triggerAuditRefresh();
        }
      } catch (_) {
        // Ignore network or auth errors during background check
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: widget.child,
      // --- Floating Action Button for quick activity creation ---
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final result = await context.push(AppRoutes.newActivity);
          if (result == true) {
            RefreshEventBus.triggerActivityRefresh();
            if (context.mounted) {
              context.pushReplacement(AppRoutes.home);
            }
          }
        },
        icon: const Icon(Icons.energy_savings_leaf_rounded),
        label: const Text('Register Installation'),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textInverse,
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,

      // --- Bottom Navigation Bar ---
      bottomNavigationBar: _buildBottomNav(context),
    );
  }

  Widget _buildBottomNav(BuildContext context) {
    // Determine current tab index from route
    final location = GoRouterState.of(context).matchedLocation;
    int currentIndex = 0;
    if (location.startsWith('/audits')) currentIndex = 1;
    else if (location.startsWith('/sensors')) currentIndex = 2;
    else if (location.startsWith('/community')) currentIndex = 3;
    else if (location.startsWith('/profile')) currentIndex = 4;

    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.border, width: 0.5)),
      ),
      child: NavigationBar(
        backgroundColor: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: AppColors.primary.withValues(alpha: 0.15),
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              context.go(AppRoutes.home);
              break;
            case 1:
              context.go(AppRoutes.audits);
              break;
            case 2:
              context.go(AppRoutes.sensors);
              break;
            case 3:
              context.go(AppRoutes.community);
              break;
            case 4:
              context.go(AppRoutes.profile);
              break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.layers_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.layers_rounded, color: AppColors.primary),
            label: 'Activities',
          ),
          NavigationDestination(
            icon: Icon(Icons.verified_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.verified_rounded, color: AppColors.primary),
            label: 'Audits',
          ),
          NavigationDestination(
            icon: Icon(Icons.hub_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.hub_rounded, color: AppColors.primary),
            label: 'Sensors',
          ),
          NavigationDestination(
            icon: Icon(Icons.public_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.public_rounded, color: AppColors.primary),
            label: 'Community',
          ),
          NavigationDestination(
            icon: Icon(Icons.badge_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.badge_rounded, color: AppColors.primary),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
