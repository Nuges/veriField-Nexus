// =============================================================================
// VeriField Nexus — Login Screen
// =============================================================================
// Premium dark-themed login screen with email/phone authentication.
// Uses Supabase Auth with glassmorphic card design.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/config/supabase_config.dart';
import '../../../core/router/app_router.dart';
import '../../../shared/widgets/shared_widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// Handle login form submission.
  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await SupabaseConfig.client.auth.signInWithPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      if (mounted) {
        context.go(AppRoutes.home);
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Invalid credentials. Please try again.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: AppSpacing.massive),

              // --- Logo & Title ---
              _buildHeader(),

              const SizedBox(height: AppSpacing.xxxl),

              // --- Login Form ---
              _buildLoginForm(),

              const SizedBox(height: AppSpacing.xl),

              // --- Register Link ---
              _buildRegisterLink(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // App icon
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            gradient: AppColors.primaryGradient,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(Icons.verified_rounded, color: Colors.white, size: 32),
        ).animate().fadeIn(duration: 500.ms).scale(begin: const Offset(0.8, 0.8)),

        const SizedBox(height: AppSpacing.xl),

        Text('Welcome back', style: AppTypography.display)
            .animate().fadeIn(delay: 200.ms).slideX(begin: -0.1),

        const SizedBox(height: AppSpacing.sm),

        Text(
          'Sign in to continue verifying field data',
          style: AppTypography.subtitle,
        ).animate().fadeIn(delay: 400.ms).slideX(begin: -0.1),
      ],
    );
  }

  Widget _buildLoginForm() {
    return Form(
      key: _formKey,
      child: Column(
        children: [
          // Error message
          if (_errorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              margin: const EdgeInsets.only(bottom: AppSpacing.base),
              decoration: BoxDecoration(
                color: AppColors.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
              ),
              child: Text(
                _errorMessage!,
                style: AppTypography.bodySmall.copyWith(color: AppColors.error),
              ),
            ),

          // Email field
          VFTextField(
            label: 'Email',
            hint: 'Enter your email address',
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            prefixIcon: const Icon(Icons.email_outlined, color: AppColors.textTertiary),
            validator: (value) {
              if (value == null || value.isEmpty) return 'Email is required';
              if (!value.contains('@')) return 'Enter a valid email';
              return null;
            },
          ).animate().fadeIn(delay: 500.ms),

          const SizedBox(height: AppSpacing.base),

          // Password field
          VFTextField(
            label: 'Password',
            hint: 'Enter your password',
            controller: _passwordController,
            obscureText: _obscurePassword,
            prefixIcon: const Icon(Icons.lock_outline_rounded, color: AppColors.textTertiary),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                color: AppColors.textTertiary,
              ),
              onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) return 'Password is required';
              if (value.length < 8) return 'Password must be at least 8 characters';
              return null;
            },
          ).animate().fadeIn(delay: 600.ms),

          const SizedBox(height: AppSpacing.xl),

          // Login button
          SizedBox(
            width: double.infinity,
            child: VFButton(
              label: 'Sign In',
              onPressed: _handleLogin,
              isLoading: _isLoading,
              icon: Icons.login_rounded,
            ),
          ).animate().fadeIn(delay: 700.ms),
        ],
      ),
    );
  }

  Widget _buildRegisterLink() {
    return Center(
      child: TextButton(
        onPressed: () => context.push(AppRoutes.register),
        child: RichText(
          text: TextSpan(
            text: "Don't have an account? ",
            style: AppTypography.bodySmall,
            children: [
              TextSpan(
                text: 'Sign up',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 800.ms);
  }
}
