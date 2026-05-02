// =============================================================================
// VeriField Nexus — App Router Configuration
// =============================================================================
// GoRouter setup with authentication guard and route definitions.
// Routes: splash → auth → home → activities → properties → profile
// =============================================================================

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../config/supabase_config.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/activities/screens/activity_form_screen.dart';
import '../../features/activities/screens/activity_detail_screen.dart';
import '../../features/activities/screens/activity_history_screen.dart';
import '../../features/properties/screens/property_list_screen.dart';
import '../../features/properties/screens/property_form_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/audits/screens/audit_list_screen.dart';
import '../../features/sensors/screens/sensor_connect_screen.dart';
import '../../features/community/screens/community_feed_screen.dart';
import '../../features/sync/screens/sync_queue_screen.dart';
import '../../shared/widgets/vf_shell.dart';

/// Route path constants for type-safe navigation.
class AppRoutes {
  static const String login = '/login';
  static const String register = '/register';
  static const String home = '/home';
  static const String newActivity = '/home/new-activity';
  static const String activityDetail = '/home/activity/:id';
  static const String properties = '/properties';
  static const String newProperty = '/properties/new';
  static const String audits = '/audits';
  static const String sensors = '/sensors';
  static const String community = '/community';
  static const String profile = '/profile';
  static const String syncQueue = '/sync';
}

/// Creates the GoRouter instance with auth guard and nested navigation.
final GoRouter appRouter = GoRouter(
  initialLocation: AppRoutes.home,
  debugLogDiagnostics: true,

  // --- Auth Guard: Redirect unauthenticated users to login ---
  redirect: (context, state) {
    final isLoggedIn = SupabaseConfig.isAuthenticated;
    final isAuthRoute = state.matchedLocation == AppRoutes.login ||
        state.matchedLocation == AppRoutes.register;

    // Not logged in and not on auth page → go to login
    if (!isLoggedIn && !isAuthRoute) {
      return AppRoutes.login;
    }

    // Logged in and on auth page → go to home
    if (isLoggedIn && isAuthRoute) {
      return AppRoutes.home;
    }

    return null; // No redirect needed
  },

  routes: [
    // --- Auth Routes (no shell) ---
    GoRoute(
      path: AppRoutes.login,
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: AppRoutes.register,
      builder: (context, state) => const RegisterScreen(),
    ),

    // --- Main App Shell (bottom navigation) ---
    ShellRoute(
      builder: (context, state, child) => VFShell(child: child),
      routes: [
        // Home / Activity History
        GoRoute(
          path: AppRoutes.home,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: ActivityHistoryScreen(),
          ),
          routes: [
            GoRoute(
              path: 'new-activity',
              builder: (context, state) => const ActivityFormScreen(),
            ),
            GoRoute(
              path: 'activity/:id',
              builder: (context, state) => ActivityDetailScreen(
                activityId: state.pathParameters['id']!,
              ),
            ),
          ],
        ),

        // Properties
        GoRoute(
          path: AppRoutes.properties,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: PropertyListScreen(),
          ),
          routes: [
            GoRoute(
              path: 'new',
              builder: (context, state) => const PropertyFormScreen(),
            ),
          ],
        ),

        // Audits
        GoRoute(
          path: AppRoutes.audits,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: AuditListScreen(),
          ),
        ),

        // Sensors
        GoRoute(
          path: AppRoutes.sensors,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: SensorConnectScreen(),
          ),
        ),

        // Community
        GoRoute(
          path: AppRoutes.community,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: CommunityFeedScreen(),
          ),
        ),

        // Profile
        GoRoute(
          path: AppRoutes.profile,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: ProfileScreen(),
          ),
        ),

        // Sync
        GoRoute(
          path: AppRoutes.syncQueue,
          pageBuilder: (context, state) => const NoTransitionPage(
            child: SyncQueueScreen(),
          ),
        ),
      ],
    ),
  ],
);
