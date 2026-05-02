// =============================================================================
// VeriField Nexus — Register Screen
// =============================================================================
// User registration with email/phone and profile information.
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

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _orgController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _orgController.dispose();
    super.dispose();
  }

  /// Handle registration form submission.
  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() { _isLoading = true; _errorMessage = null; });

    try {
      // Register via backend API (creates Supabase Auth + local user)
      await ApiService.post('/auth/register', body: {
        'email': _emailController.text.trim(),
        'phone': _phoneController.text.trim().isNotEmpty ? _phoneController.text.trim() : null,
        'full_name': _nameController.text.trim(),
        'password': _passwordController.text,
        'organization': _orgController.text.trim().isNotEmpty ? _orgController.text.trim() : null,
      });

      // Auto-login after registration
      await SupabaseConfig.client.auth.signInWithPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      if (mounted) context.go(AppRoutes.home);
    } catch (e) {
      setState(() { _errorMessage = e.toString(); });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Create Account', style: AppTypography.display)
                  .animate().fadeIn().slideX(begin: -0.1),
              const SizedBox(height: AppSpacing.sm),
              Text('Join VeriField Nexus to start verifying climate activities',
                  style: AppTypography.subtitle)
                  .animate().fadeIn(delay: 200.ms),
              const SizedBox(height: AppSpacing.xxl),

              // Error display
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
                  child: Text(_errorMessage!, style: AppTypography.bodySmall.copyWith(color: AppColors.error)),
                ),

              // Registration form
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    VFTextField(
                      label: 'Full Name',
                      hint: 'Enter your full name',
                      controller: _nameController,
                      prefixIcon: const Icon(Icons.person_outline, color: AppColors.textTertiary),
                      validator: (v) => v == null || v.isEmpty ? 'Name is required' : null,
                    ).animate().fadeIn(delay: 300.ms),
                    const SizedBox(height: AppSpacing.base),

                    VFTextField(
                      label: 'Email',
                      hint: 'Enter your email address',
                      controller: _emailController,
                      keyboardType: TextInputType.emailAddress,
                      prefixIcon: const Icon(Icons.email_outlined, color: AppColors.textTertiary),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Email is required';
                        if (!v.contains('@')) return 'Enter a valid email';
                        return null;
                      },
                    ).animate().fadeIn(delay: 400.ms),
                    const SizedBox(height: AppSpacing.base),

                    VFTextField(
                      label: 'Phone (Optional)',
                      hint: '+234...',
                      controller: _phoneController,
                      keyboardType: TextInputType.phone,
                      prefixIcon: const Icon(Icons.phone_outlined, color: AppColors.textTertiary),
                    ).animate().fadeIn(delay: 500.ms),
                    const SizedBox(height: AppSpacing.base),

                    VFTextField(
                      label: 'Organization (Optional)',
                      hint: 'Your organization name',
                      controller: _orgController,
                      prefixIcon: const Icon(Icons.business_outlined, color: AppColors.textTertiary),
                    ).animate().fadeIn(delay: 600.ms),
                    const SizedBox(height: AppSpacing.base),

                    VFTextField(
                      label: 'Password',
                      hint: 'Min 8 characters',
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      prefixIcon: const Icon(Icons.lock_outline, color: AppColors.textTertiary),
                      suffixIcon: IconButton(
                        icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility, color: AppColors.textTertiary),
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Password is required';
                        if (v.length < 8) return 'Min 8 characters';
                        return null;
                      },
                    ).animate().fadeIn(delay: 700.ms),
                    const SizedBox(height: AppSpacing.xl),

                    SizedBox(
                      width: double.infinity,
                      child: VFButton(
                        label: 'Create Account',
                        onPressed: _handleRegister,
                        isLoading: _isLoading,
                        icon: Icons.person_add_rounded,
                      ),
                    ).animate().fadeIn(delay: 800.ms),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
