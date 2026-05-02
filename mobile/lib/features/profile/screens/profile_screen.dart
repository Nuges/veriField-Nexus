// =============================================================================
// VeriField Nexus — Profile Screen
// =============================================================================
// User profile with stats, sync status, and app settings.
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
import '../../../services/local_db_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _user;
  int _pendingCount = 0;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    _pendingCount = await LocalDbService.getPendingCount();
    try {
      _user = await ApiService.get('/auth/me');
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _logout() async {
    await SupabaseConfig.client.auth.signOut();
    if (mounted) context.go(AppRoutes.login);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                children: [
                  // Avatar + Name
                  _buildProfileHeader(),
                  const SizedBox(height: AppSpacing.xl),

                  // Stats
                  _buildStats(),
                  const SizedBox(height: AppSpacing.xl),

                  // Sync status
                  VFCard(
                    child: Row(
                      children: [
                        Icon(
                          _pendingCount > 0 ? Icons.sync_rounded : Icons.cloud_done_rounded,
                          color: _pendingCount > 0 ? AppColors.warning : AppColors.primary,
                        ),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Sync Status', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
                              Text(
                                _pendingCount > 0
                                    ? '$_pendingCount activities pending sync'
                                    : 'All data synced',
                                style: AppTypography.caption,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms),
                  const SizedBox(height: AppSpacing.xl),

                  // Logout
                  SizedBox(
                    width: double.infinity,
                    child: VFButton(
                      label: 'Sign Out',
                      onPressed: _logout,
                      isOutlined: true,
                      color: AppColors.error,
                      icon: Icons.logout_rounded,
                    ),
                  ).animate().fadeIn(delay: 500.ms),
                ],
              ),
            ),
    );
  }

  Widget _buildProfileHeader() {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: AppColors.primaryGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Center(
            child: Text(
              (_user?['full_name'] ?? 'U').toString().substring(0, 1).toUpperCase(),
              style: AppTypography.display.copyWith(color: Colors.white),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.base),
        Text(_user?['full_name'] ?? 'User', style: AppTypography.heading),
        const SizedBox(height: 4),
        Text(_user?['email'] ?? '', style: AppTypography.bodySmall),
        if (_user?['organization'] != null) ...[
          const SizedBox(height: 4),
          Text(_user!['organization'], style: AppTypography.caption),
        ],
        const SizedBox(height: AppSpacing.sm),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            (_user?['role'] ?? 'field_agent').toString().toUpperCase().replaceAll('_', ' '),
            style: AppTypography.caption.copyWith(color: AppColors.primary, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    ).animate().fadeIn().scale(begin: const Offset(0.95, 0.95));
  }

  Widget _buildStats() {
    return Row(
      children: [
        Expanded(child: _statCard('Pending', '$_pendingCount', AppColors.warning)),
        const SizedBox(width: AppSpacing.md),
        Expanded(child: _statCard('Role', _user?['role'] == 'admin' ? 'Admin' : 'Agent', AppColors.accent)),
      ],
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _statCard(String label, String value, Color color) {
    return VFCard(
      child: Column(
        children: [
          Text(value, style: AppTypography.numericSmall.copyWith(color: color)),
          const SizedBox(height: 4),
          Text(label, style: AppTypography.caption),
        ],
      ),
    );
  }
}
