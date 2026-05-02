// =============================================================================
// VeriField Nexus — Application Entry Point
// =============================================================================
// Initializes Supabase, sets up auto-sync, and launches the app
// with the premium light theme and GoRouter navigation.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'core/theme/app_theme.dart';
import 'core/config/supabase_config.dart';
import 'core/router/app_router.dart';
import 'services/sync_service.dart';

void main() async {
  // Ensure Flutter is initialized before async operations
  WidgetsFlutterBinding.ensureInitialized();

  // Lock orientation to portrait (field app best used in portrait)
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Set system UI overlay style for premium light theme
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    systemNavigationBarColor: Color(0xFFF8FAFC),
    systemNavigationBarIconBrightness: Brightness.dark,
  ));

  // Initialize Supabase client
  await SupabaseConfig.initialize();

  // Start auto-sync listener (syncs when connectivity is restored)
  SyncService.startAutoSync();

  runApp(const VeriFieldNexusApp());
}

/// Root application widget.
class VeriFieldNexusApp extends StatelessWidget {
  const VeriFieldNexusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      // App metadata
      title: 'VeriField Nexus',
      debugShowCheckedModeBanner: false,

      // Premium light theme (only theme — light mode default)
      theme: AppTheme.darkTheme, // We updated the colors inside this theme to be light!

      // GoRouter for navigation with auth guard
      routerConfig: appRouter,
    );
  }
}
