// =============================================================================
// VeriField Nexus — Shared Widgets
// =============================================================================
// Reusable UI components used across multiple features.
// Follows the app's design system for consistency.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/constants/app_spacing.dart';

// =============================================================================
// VFButton — Primary action button with loading state
// =============================================================================
class VFButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isOutlined;
  final IconData? icon;
  final Color? color;

  const VFButton({
    super.key,
    required this.label,
    this.onPressed,
    this.isLoading = false,
    this.isOutlined = false,
    this.icon,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final bgColor = color ?? AppColors.primary;

    if (isOutlined) {
      return OutlinedButton(
        onPressed: isLoading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: bgColor),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
          ),
        ),
        child: _buildContent(bgColor),
      );
    }

    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: bgColor,
        foregroundColor: AppColors.textInverse,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        ),
        elevation: 0,
      ),
      child: _buildContent(isOutlined ? bgColor : AppColors.textInverse),
    );
  }

  Widget _buildContent(Color contentColor) {
    if (isLoading) {
      return SizedBox(
        height: 20,
        width: 20,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: contentColor,
        ),
      );
    }

    if (icon != null) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 20, color: contentColor),
          const SizedBox(width: 8),
          Text(label, style: AppTypography.button.copyWith(color: contentColor)),
        ],
      );
    }

    return Text(label, style: AppTypography.button.copyWith(color: contentColor));
  }
}

// =============================================================================
// VFCard — Styled card with subtle border and optional gradient
// =============================================================================
class VFCard extends StatelessWidget {
  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry? padding;
  final Gradient? gradient;

  const VFCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding,
    this.gradient,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: padding ?? const EdgeInsets.all(AppSpacing.base),
        decoration: BoxDecoration(
          color: gradient == null ? AppColors.surface : null,
          gradient: gradient,
          borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
          border: Border.all(color: AppColors.border, width: 1),
        ),
        child: child,
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.05, end: 0);
  }
}

// =============================================================================
// VFTextField — Styled text input field
// =============================================================================
class VFTextField extends StatelessWidget {
  final String label;
  final String? hint;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final String? Function(String?)? validator;
  final int maxLines;

  const VFTextField({
    super.key,
    required this.label,
    this.hint,
    this.controller,
    this.obscureText = false,
    this.keyboardType,
    this.prefixIcon,
    this.suffixIcon,
    this.validator,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTypography.bodySmall),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          maxLines: maxLines,
          validator: validator,
          style: AppTypography.body,
          decoration: InputDecoration(
            hintText: hint,
            prefixIcon: prefixIcon,
            suffixIcon: suffixIcon,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// TrustScoreGauge — Circular trust score visualization
// =============================================================================
class TrustScoreGauge extends StatelessWidget {
  final double? score;
  final double size;

  const TrustScoreGauge({super.key, this.score, this.size = 60});

  @override
  Widget build(BuildContext context) {
    final displayScore = score ?? 0;
    final color = _getColor(displayScore);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          // Background circle
          CircularProgressIndicator(
            value: 1,
            strokeWidth: 4,
            color: AppColors.surface,
          ),
          // Score arc
          CircularProgressIndicator(
            value: displayScore / 100,
            strokeWidth: 4,
            color: color,
            strokeCap: StrokeCap.round,
          ),
          // Score text
          Center(
            child: Text(
              score != null ? '${displayScore.toInt()}' : '—',
              style: AppTypography.numericSmall.copyWith(
                color: color,
                fontSize: size * 0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getColor(double score) {
    if (score >= 80) return AppColors.trustHigh;
    if (score >= 50) return AppColors.trustMedium;
    return AppColors.trustLow;
  }
}

// =============================================================================
// VFEmptyState — Empty state placeholder
// =============================================================================
class VFEmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget? action;

  const VFEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64, color: AppColors.textTertiary),
            const SizedBox(height: AppSpacing.base),
            Text(title, style: AppTypography.title, textAlign: TextAlign.center),
            const SizedBox(height: AppSpacing.sm),
            Text(subtitle, style: AppTypography.bodySmall, textAlign: TextAlign.center),
            if (action != null) ...[
              const SizedBox(height: AppSpacing.xl),
              action!,
            ],
          ],
        ),
      ),
    ).animate().fadeIn(duration: 500.ms);
  }
}

// =============================================================================
// SyncStatusBanner — Shows offline/syncing status
// =============================================================================
class SyncStatusBanner extends StatelessWidget {
  final bool isOnline;
  final int pendingCount;

  const SyncStatusBanner({
    super.key,
    required this.isOnline,
    required this.pendingCount,
  });

  @override
  Widget build(BuildContext context) {
    if (isOnline && pendingCount == 0) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.base,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: isOnline ? AppColors.warning.withValues(alpha: 0.15) : AppColors.error.withValues(alpha: 0.15),
        border: Border(
          bottom: BorderSide(
            color: isOnline ? AppColors.warning : AppColors.error,
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(
            isOnline ? Icons.sync_rounded : Icons.cloud_off_rounded,
            size: 16,
            color: isOnline ? AppColors.warning : AppColors.error,
          ),
          const SizedBox(width: 8),
          Text(
            isOnline
                ? '$pendingCount activities pending sync'
                : 'You are offline. Data saved locally.',
            style: AppTypography.caption.copyWith(
              color: isOnline ? AppColors.warning : AppColors.error,
            ),
          ),
        ],
      ),
    ).animate().fadeIn().slideY(begin: -0.5, end: 0);
  }
}
