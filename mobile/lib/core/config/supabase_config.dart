// =============================================================================
// VeriField Nexus — Supabase Configuration
// =============================================================================
// Initialize Supabase client for auth and storage.
// Replace placeholder values with your actual Supabase project credentials.
// =============================================================================

import 'package:supabase_flutter/supabase_flutter.dart';

/// Supabase configuration constants.
/// In production, use dart-define or a .env solution for these values.
class SupabaseConfig {
  SupabaseConfig._();

  static const String url = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: 'https://your-supabase-project.supabase.co',
  );

  static const String anonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: 'YOUR_SUPABASE_ANON_KEY_PLACEHOLDER',
  );

  /// Initialize the Supabase client. Call this in main() before runApp().
  static Future<void> initialize() async {
    await Supabase.initialize(
      url: url,
      anonKey: anonKey,
    );
  }

  /// Get the Supabase client singleton.
  static SupabaseClient get client => Supabase.instance.client;

  /// Get the current auth session.
  static Session? get currentSession => client.auth.currentSession;

  /// Get the current user.
  static User? get currentUser => client.auth.currentUser;

  /// Check if user is authenticated.
  static bool get isAuthenticated => currentSession != null;
}
