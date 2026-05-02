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

  // TODO: Replace with your actual Supabase project URL
  static const String url = 'https://rxlfxrbyhagyofzfwzoa.supabase.co';

  // TODO: Replace with your actual Supabase anon key
  static const String anonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ4bGZ4cmJ5aGFneW9memZ3em9hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc1MzQ0MTcsImV4cCI6MjA5MzExMDQxN30.KRy4CNbJ1VE-ow2IzTRrZfbTinIJWpph-HZ4q6Pu_Uw';

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
