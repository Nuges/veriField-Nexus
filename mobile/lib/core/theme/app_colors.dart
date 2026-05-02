// =============================================================================
// VeriField Nexus — App Color Palette
// =============================================================================
// Premium dark theme color system designed for climate/sustainability apps.
// All colors are semantically named for consistency across the app.
// =============================================================================

import 'package:flutter/material.dart';

/// Centralized color palette for VeriField Nexus.
/// Use these constants instead of raw Color values throughout the app.
class AppColors {
  AppColors._(); // Prevent instantiation

  // --- Primary Brand Colors (Emerald Green = Climate/Sustainability) ---
  static const Color primary = Color(0xFF10B981);
  static const Color primaryDark = Color(0xFF059669);
  static const Color primaryLight = Color(0xFF34D399);

  // --- Surface Colors (Clean Off-White palette) ---
  static const Color background = Color(0xFFF8FAFC); // Slate 50
  static const Color surface = Color(0xFFFFFFFF);    // White
  static const Color surfaceLight = Color(0xFFF1F5F9); // Slate 100
  static const Color surfaceHover = Color(0xFFE2E8F0); // Slate 200

  // --- Text Colors ---
  static const Color textPrimary = Color(0xFF1E293B);  // Slate 800
  static const Color textSecondary = Color(0xFF475569); // Slate 600
  static const Color textTertiary = Color(0xFF64748B); // Slate 500
  static const Color textInverse = Color(0xFFFFFFFF);  // White

  // --- Trust Score Colors ---
  static const Color trustHigh = Color(0xFF10B981);    // Green — Verified
  static const Color trustMedium = Color(0xFFF59E0B);  // Amber — Needs Review
  static const Color trustLow = Color(0xFFEF4444);     // Red — Flagged

  // --- Accent Colors ---
  static const Color accent = Color(0xFF3B82F6);       // Blue
  static const Color accentPurple = Color(0xFF8B5CF6);  // Purple
  static const Color warning = Color(0xFFF59E0B);       // Amber
  static const Color error = Color(0xFFEF4444);         // Red
  static const Color success = Color(0xFF10B981);       // Green
  static const Color info = Color(0xFF06B6D4);          // Cyan

  // --- Border Colors ---
  static const Color border = Color(0xFFE2E8F0); // Slate 200
  static const Color borderLight = Color(0xFFCBD5E1); // Slate 300
  static const Color borderFocus = Color(0xFF10B981); // Emerald 500

  // --- Gradient Presets ---
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, primaryDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFFFFFFFF), Color(0xFFF8FAFC)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accentGradient = LinearGradient(
    colors: [accent, accentPurple],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
