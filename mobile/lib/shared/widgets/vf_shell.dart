// =============================================================================
// VeriField Nexus — Bottom Navigation Shell
// =============================================================================
// Main app shell with animated bottom navigation bar.
// Wraps all main screens (Home, Properties, Profile).
// =============================================================================

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';

/// Shell widget providing bottom navigation across main app sections.
class VFShell extends StatelessWidget {
  final Widget child;

  const VFShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      // --- Floating Action Button for quick activity creation ---
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push(AppRoutes.newActivity),
        icon: const Icon(Icons.add_a_photo_rounded),
        label: const Text('Log Activity'),
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
            icon: Icon(Icons.history_rounded, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.history_rounded, color: AppColors.primary),
            label: 'Activities',
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.fact_check, color: AppColors.primary),
            label: 'Audits',
          ),
          NavigationDestination(
            icon: Icon(Icons.sensors_rounded, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.sensors, color: AppColors.primary),
            label: 'Sensors',
          ),
          NavigationDestination(
            icon: Icon(Icons.groups_outlined, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.groups_rounded, color: AppColors.primary),
            label: 'Community',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded, color: AppColors.textTertiary),
            selectedIcon: Icon(Icons.person_rounded, color: AppColors.primary),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
