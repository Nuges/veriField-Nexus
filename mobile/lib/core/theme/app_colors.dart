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

  // --- Primary Brand Colors (VeriField Branded Emerald Green) ---
  static const Color primary = Color(0xFF00B47A);
  static const Color primaryDark = Color(0xFF009665);
  static const Color primaryLight = Color(0xFF33C395);

  // --- Surface Colors (Premium Technical Slate Dark Theme) ---
  static const Color background = Color(0xFF090F10); // Technical dark green-tint slate
  static const Color surface = Color(0xFF0E1617);    // Dark slate surface
  static const Color surfaceLight = Color(0xFF141F20); // Dark slate card background
  static const Color surfaceHover = Color(0xFF1E2E2F); // Slightly lighter for active states

  // --- Text Colors ---
  static const Color textPrimary = Color(0xFFF8FAF9);  // Technical off-white
  static const Color textSecondary = Color(0xFF8E9E9B); // Secondary technical slate
  static const Color textTertiary = Color(0xFF5F6F6C);  // Muted tech slate
  static const Color textInverse = Color(0xFF090F10);   // Dark inverse

  // --- Trust Score Colors ---
  static const Color trustHigh = Color(0xFF00B47A);    // Branded Green — Verified
  static const Color trustMedium = Color(0xFFF59E0B);  // Amber — Needs Review
  static const Color trustLow = Color(0xFFEF4444);     // Red — Flagged

  // --- Accent Colors ---
  static const Color accent = Color(0xFF3B82F6);       // Blue
  static const Color accentPurple = Color(0xFF8B5CF6);  // Purple
  static const Color warning = Color(0xFFF59E0B);       // Amber
  static const Color error = Color(0xFFEF4444);         // Red
  static const Color success = Color(0xFF00B47A);       // Green
  static const Color info = Color(0xFF06B6D4);          // Cyan

  // --- Border Colors ---
  static const Color border = Color(0xFF213233);       // Dark border with brand hue
  static const Color borderLight = Color(0xFF2A3D3E);  // Slightly lighter border
  static const Color borderFocus = Color(0xFF00B47A);  // Branded Green

  // --- Gradient Presets ---
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, primaryDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [surface, surfaceLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accentGradient = LinearGradient(
    colors: [accent, accentPurple],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
