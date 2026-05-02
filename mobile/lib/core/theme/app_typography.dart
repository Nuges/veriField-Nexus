// =============================================================================
// VeriField Nexus — Typography Scale
// =============================================================================
// Uses Google Fonts (Inter + Outfit) for a premium, modern feel.
// Scales: display, heading, title, body, caption
// =============================================================================

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

/// Typography scale for VeriField Nexus.
/// Outfit is used for display/heading text, Inter for body/UI text.
class AppTypography {
  AppTypography._();

  // --- Display (Hero text, splash screens) ---
  static TextStyle display = GoogleFonts.outfit(
    fontSize: 32,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.5,
  );

  // --- Heading (Section headers) ---
  static TextStyle heading = GoogleFonts.outfit(
    fontSize: 24,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: -0.3,
  );

  // --- Title (Card titles, app bar) ---
  static TextStyle title = GoogleFonts.inter(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  // --- Subtitle ---
  static TextStyle subtitle = GoogleFonts.inter(
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
  );

  // --- Body (Main content text) ---
  static TextStyle body = GoogleFonts.inter(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    color: AppColors.textPrimary,
    height: 1.5,
  );

  // --- Body Small ---
  static TextStyle bodySmall = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
    height: 1.5,
  );

  // --- Caption (Labels, metadata) ---
  static TextStyle caption = GoogleFonts.inter(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: AppColors.textTertiary,
  );

  // --- Button Text ---
  static TextStyle button = GoogleFonts.inter(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.3,
  );

  // --- Numeric (Scores, stats) ---
  static TextStyle numeric = GoogleFonts.outfit(
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: AppColors.primary,
  );

  // --- Numeric Small ---
  static TextStyle numericSmall = GoogleFonts.outfit(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: AppColors.primary,
  );
}
