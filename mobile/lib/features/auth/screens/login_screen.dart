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
import '../../../services/api_service.dart';

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
  bool _isServerChecking = false;
  bool? _isServerReachable;

  @override
  void initState() {
    super.initState();
    _checkServerConnection();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _checkServerConnection() async {
    setState(() {
      _isServerChecking = true;
    });
    final reachable = await ApiService.checkServerConnection();
    if (mounted) {
      setState(() {
        _isServerReachable = reachable;
        _isServerChecking = false;
      });
    }
  }

  /// Handle login form submission.
  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final email = _emailController.text.trim();
    final password = _passwordController.text;

    debugPrint('[LoginScreen] Starting backend-first login flow for $email');

    try {
      // 1. TRY backend login first
      try {
        debugPrint('[LoginScreen] Step 1: Querying FastAPI backend /auth/login');
        final response = await ApiService.login(email, password);
        final token = response['access_token'] as String?;
        if (token != null) {
          debugPrint('[LoginScreen] Backend login succeeded. Persisting customToken.');
          await ApiService.setCustomToken(token);
          
          // Also try to set the session on Supabase client if possible (best effort)
          try {
            await SupabaseConfig.client.auth.setSession(token);
            debugPrint('[LoginScreen] Supabase setSession succeeded with backend token');
          } catch (se) {
            debugPrint('[LoginScreen] Supabase setSession failed (expected for local DB tokens): $se');
          }

          if (mounted) {
            debugPrint('[LoginScreen] Navigating to home');
            context.go(AppRoutes.home);
            return;
          }
        } else {
          debugPrint('[LoginScreen] Backend login response did not contain access_token');
        }
      } catch (backendError) {
        debugPrint('[LoginScreen] Backend login failed: $backendError');
        // If the backend is completely unreachable, make sure we run the connection check
        _checkServerConnection();
      }

      // 2. TRY Supabase login as fallback
      debugPrint('[LoginScreen] Step 2: Querying Supabase Auth directly');
      await SupabaseConfig.client.auth.signInWithPassword(
        email: email,
        password: password,
      );
      debugPrint('[LoginScreen] Supabase login succeeded.');

      if (mounted) {
        debugPrint('[LoginScreen] Navigating to home');
        context.go(AppRoutes.home);
      }
    } catch (e) {
      debugPrint('[LoginScreen] Both backend and Supabase login failed: $e');
      setState(() {
        _errorMessage = 'Invalid credentials. Please check your server connection and try again.';
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
          // Cannot Connect to Server Warning Banner
          if (_isServerReachable == false)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              margin: const EdgeInsets.only(bottom: AppSpacing.base),
              decoration: BoxDecoration(
                color: AppColors.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.cloud_off_rounded, color: AppColors.error, size: 20),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          'Cannot connect to server',
                          style: AppTypography.bodySmall.copyWith(color: AppColors.error, fontWeight: FontWeight.bold),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.refresh_rounded, color: AppColors.error, size: 20),
                        onPressed: _checkServerConnection,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Server may be waking up. Tap refresh to retry.',
                    style: AppTypography.bodySmall.copyWith(color: AppColors.error.withValues(alpha: 0.7), fontSize: 11),
                  ),
                ],
              ),
            ).animate().fadeIn(),

          if (_isServerChecking)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              margin: const EdgeInsets.only(bottom: AppSpacing.base),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Connecting to server... This may take up to 60 seconds on first launch.',
                      style: AppTypography.bodySmall.copyWith(color: AppColors.primary, fontSize: 11),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(),

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

          // Server Connection Status widget
          const SizedBox(height: AppSpacing.lg),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
            decoration: BoxDecoration(
              color: Colors.white10,
              borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SERVER IP & PORT:',
                        style: AppTypography.bodySmall.copyWith(fontSize: 9, color: AppColors.textTertiary, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        ApiService.apiBaseUrl,
                        style: AppTypography.bodySmall.copyWith(fontSize: 11, fontFamily: 'monospace', color: AppColors.textSecondary),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                TextButton.icon(
                  onPressed: _isServerChecking ? null : _checkServerConnection,
                  icon: _isServerChecking
                      ? const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(strokeWidth: 1.5, color: AppColors.primary),
                        )
                      : Icon(
                          _isServerReachable == true ? Icons.cloud_done_rounded : Icons.cloud_sync_rounded,
                          size: 14,
                          color: _isServerReachable == true ? AppColors.primary : AppColors.textSecondary,
                        ),
                  label: Text(
                    _isServerChecking
                        ? 'Checking...'
                        : (_isServerReachable == true ? 'Connected' : 'Test Connection'),
                    style: AppTypography.bodySmall.copyWith(
                      fontSize: 10,
                      color: _isServerReachable == true ? AppColors.primary : AppColors.textSecondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                  ),
                ),
              ],
            ),
          ),

          // Sign up link
          const SizedBox(height: AppSpacing.xl),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                "Don't have an account? ",
                style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
              ),
              GestureDetector(
                onTap: () => context.push(AppRoutes.register),
                child: Text(
                  "Sign Up",
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ).animate().fadeIn(delay: 800.ms),
        ],
      ),
    );
  }
}
