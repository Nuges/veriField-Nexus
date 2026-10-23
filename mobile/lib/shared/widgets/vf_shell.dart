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
import '../../core/utils/field_access.dart';
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
  String? _role;

  @override
  void initState() {
    super.initState();
    _loadRole();
    _startNotificationCheck();
  }

  @override
  void dispose() {
    _notificationTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadRole() async {
    var user = ApiService.currentUser;
    try { user = await ApiService.get('/auth/me'); } catch (_) {}
    if (mounted) setState(() { _role = user?['role'] as String?; _myUserId = user?['id'] as String?; });
  }

  void _startNotificationCheck() {
    // Check for new audit tasks periodically (every 10 seconds)
    _notificationTimer = Timer.periodic(const Duration(seconds: 10), (timer) async {
      if (!mounted || !FieldAccess.canReadAudits(_role)) return;
      
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
        final audits = (response['tasks'] ?? response['audits'] ?? response['data'] ?? []) as List;
        
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
      floatingActionButton: FieldAccess.canCapture(_role) ? FloatingActionButton.extended(
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
        label: const Text('Capture data'),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textInverse,
      ) : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,

      // --- Bottom Navigation Bar ---
      bottomNavigationBar: _buildBottomNav(context),
    );
  }

  Widget _buildBottomNav(BuildContext context) {
    final destinations = <({String path, String label, IconData icon})>[
      (path: AppRoutes.home, label: 'Field records', icon: Icons.layers_outlined),
      if (FieldAccess.canReadAudits(_role)) (path: AppRoutes.audits, label: 'Audits', icon: Icons.verified_outlined),
      if (FieldAccess.canReadSensors(_role)) (path: AppRoutes.sensors, label: 'Sensors', icon: Icons.hub_outlined),
      (path: AppRoutes.community, label: 'Community', icon: Icons.public_outlined),
      (path: AppRoutes.profile, label: 'Profile', icon: Icons.badge_outlined),
    ];
    final location = GoRouterState.of(context).matchedLocation;
    final index = destinations.indexWhere((d) => location.startsWith(d.path));
    return NavigationBar(
      selectedIndex: index < 0 ? 0 : index,
      onDestinationSelected: (index) => context.go(destinations[index].path),
      destinations: destinations.map((d) => NavigationDestination(icon: Icon(d.icon), label: d.label)).toList(),
    );
  }
}
