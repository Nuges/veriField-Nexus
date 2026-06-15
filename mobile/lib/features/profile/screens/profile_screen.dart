// =============================================================================
// VeriField Nexus — Profile Screen
// =============================================================================
// User profile with stats, sync status, edit profile details, 
// password updates, and GDPR compliance controls.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/config/supabase_config.dart';
import '../../../core/router/app_router.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';
import '../../../services/local_db_service.dart';
import '../../../services/camera_service.dart';

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

  void _showEditProfileModal() {
    final nameController = TextEditingController(text: _user?['full_name'] ?? '');
    String selectedAvatar = _user?['avatar_url'] ?? '';
    bool isSaving = false;
    bool isUploading = false;
    bool showCustomUrl = false;
    final customUrlController = TextEditingController(text: selectedAvatar);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            Future<void> pickAndUploadPhoto(bool fromCamera) async {
              setModalState(() {
                isUploading = true;
              });
              try {
                final XFile? file = fromCamera 
                    ? await CameraService.capturePhoto() 
                    : await CameraService.pickFromGallery();
                if (file == null) {
                  setModalState(() {
                    isUploading = false;
                  });
                  return;
                }
                
                final res = await ApiService.uploadAvatar(file);
                final uploadedUrl = res['avatar_url'] as String;
                
                setModalState(() {
                  selectedAvatar = uploadedUrl;
                  customUrlController.text = uploadedUrl;
                });
                
                if (context.mounted) {
                  VFNotification.showSuccess(context, 'Custom photo uploaded. Remember to save!');
                }
              } catch (e) {
                if (context.mounted) {
                  VFNotification.showError(context, 'Failed to upload photo: ${e.toString().replaceAll('ApiException(400): ', '')}');
                }
              } finally {
                setModalState(() {
                  isUploading = false;
                });
              }
            }

            void showImageSourceSelection() {
              showModalBottomSheet(
                context: context,
                backgroundColor: AppColors.surface,
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                ),
                builder: (context) {
                  return SafeArea(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ListTile(
                          leading: const Icon(Icons.camera_alt_rounded, color: AppColors.primary),
                          title: const Text('Take a Photo', style: TextStyle(color: Colors.white)),
                          onTap: () {
                            Navigator.pop(context);
                            pickAndUploadPhoto(true);
                          },
                        ),
                        ListTile(
                          leading: const Icon(Icons.image_rounded, color: AppColors.primary),
                          title: const Text('Choose from Gallery', style: TextStyle(color: Colors.white)),
                          onTap: () {
                            Navigator.pop(context);
                            pickAndUploadPhoto(false);
                          },
                        ),
                      ],
                    ),
                  );
                },
              );
            }

            final hasAvatar = selectedAvatar.isNotEmpty;

            return Padding(
              padding: EdgeInsets.only(
                left: AppSpacing.xl,
                right: AppSpacing.xl,
                top: AppSpacing.xl,
                bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.xl,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Edit Profile', style: AppTypography.heading),
                    const SizedBox(height: AppSpacing.md),
                    
                    Text('Choose Profile Avatar', style: AppTypography.bodySmall),
                    const SizedBox(height: AppSpacing.sm),
                    
                    Row(
                      children: [
                        GestureDetector(
                          onTap: isUploading ? null : showImageSourceSelection,
                          child: Container(
                            width: 60,
                            height: 60,
                            decoration: BoxDecoration(
                              gradient: AppColors.primaryGradient,
                              borderRadius: BorderRadius.circular(16),
                              image: hasAvatar
                                  ? DecorationImage(image: NetworkImage(selectedAvatar), fit: BoxFit.cover)
                                  : null,
                            ),
                            child: isUploading
                                ? const Center(
                                    child: SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    ),
                                  )
                                : hasAvatar
                                    ? Align(
                                        alignment: Alignment.bottomRight,
                                        child: Container(
                                          padding: const EdgeInsets.all(2),
                                          decoration: const BoxDecoration(
                                            color: AppColors.primary,
                                            shape: BoxShape.circle,
                                          ),
                                          child: const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 10),
                                        ),
                                      )
                                    : const Icon(Icons.add_a_photo_rounded, color: Colors.white38, size: 24),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: [
                                'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&h=150&q=80',
                                'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                                'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150&q=80',
                                'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80',
                                'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=150&h=150&q=80',
                                'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150&q=80',
                              ].map((url) {
                                final isSelected = selectedAvatar == url;
                                return GestureDetector(
                                  onTap: () {
                                    setModalState(() {
                                      selectedAvatar = url;
                                      customUrlController.text = url;
                                    });
                                  },
                                  child: Container(
                                    margin: const EdgeInsets.only(right: 8),
                                    width: 44,
                                    height: 44,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: isSelected ? AppColors.primary : AppColors.border,
                                        width: isSelected ? 2 : 1,
                                      ),
                                      image: DecorationImage(image: NetworkImage(url), fit: BoxFit.cover),
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    
                    GestureDetector(
                      onTap: isUploading ? null : showImageSourceSelection,
                      child: Text(
                        'Upload Custom Photo...',
                        style: AppTypography.caption.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    
                    GestureDetector(
                      onTap: () {
                        setModalState(() {
                          showCustomUrl = !showCustomUrl;
                        });
                      },
                      child: Text(
                        showCustomUrl ? 'Use preset selections' : 'Provide custom picture URL...',
                        style: AppTypography.caption.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
                      ),
                    ),
                    if (showCustomUrl) ...[
                      const SizedBox(height: AppSpacing.sm),
                      VFTextField(
                        label: 'Custom Photo URL',
                        hint: 'https://example.com/photo.jpg',
                        controller: customUrlController,
                        onChanged: (val) {
                          setModalState(() {
                            selectedAvatar = val;
                          });
                        },
                      ),
                    ],
                    const SizedBox(height: AppSpacing.md),
                    
                    VFTextField(
                      label: 'Full Name',
                      hint: 'Enter your full name',
                      controller: nameController,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    SizedBox(
                      width: double.infinity,
                      child: VFButton(
                        label: 'Save Profile Details',
                        isLoading: isSaving,
                        onPressed: () async {
                          if (nameController.text.trim().isEmpty) {
                            VFNotification.showError(context, 'Full Name is required.');
                            return;
                          }
                          setModalState(() => isSaving = true);
                          try {
                            await ApiService.put('/auth/profile', body: {
                              'full_name': nameController.text.trim(),
                              'avatar_url': selectedAvatar,
                            });
                            await _loadProfile();
                            if (context.mounted) {
                              VFNotification.showSuccess(context, 'Profile updated successfully.');
                              Navigator.pop(context);
                            }
                          } catch (e) {
                            if (context.mounted) {
                              VFNotification.showError(context, 'Update failed: ${e.toString().replaceAll('ApiException(400): ', '')}');
                            }
                          } finally {
                            setModalState(() => isSaving = false);
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showChangePasswordModal() {
    final passwordController = TextEditingController();
    final confirmController = TextEditingController();
    bool isSaving = false;
    bool showPassword = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: AppSpacing.xl,
                right: AppSpacing.xl,
                top: AppSpacing.xl,
                bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.xl,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Change Password', style: AppTypography.heading),
                    const SizedBox(height: AppSpacing.md),
                    
                    VFTextField(
                      label: 'New Password',
                      hint: 'Minimum 8 characters',
                      controller: passwordController,
                      obscureText: !showPassword,
                      suffixIcon: IconButton(
                        icon: Icon(showPassword ? Icons.visibility_off_rounded : Icons.visibility_rounded, color: AppColors.textSecondary),
                        onPressed: () {
                          setModalState(() {
                            showPassword = !showPassword;
                          });
                        },
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    
                    VFTextField(
                      label: 'Confirm New Password',
                      hint: 'Repeat new password',
                      controller: confirmController,
                      obscureText: !showPassword,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    
                    SizedBox(
                      width: double.infinity,
                      child: VFButton(
                        label: 'Update Security Password',
                        isLoading: isSaving,
                        onPressed: () async {
                          final pass = passwordController.text;
                          final conf = confirmController.text;
                          if (pass.length < 8) {
                            VFNotification.showError(context, 'Password must be at least 8 characters.');
                            return;
                          }
                          if (pass != conf) {
                            VFNotification.showError(context, 'Passwords do not match.');
                            return;
                          }
                          setModalState(() => isSaving = true);
                          try {
                            await ApiService.post('/auth/change-password', body: {
                              'new_password': pass,
                            });
                            if (context.mounted) {
                              VFNotification.showSuccess(context, 'Password updated successfully.');
                              Navigator.pop(context);
                            }
                          } catch (e) {
                            if (context.mounted) {
                              VFNotification.showError(context, 'Password change failed: ${e.toString()}');
                            }
                          } finally {
                            setModalState(() => isSaving = false);
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _logout() async {
    await SupabaseConfig.client.auth.signOut();
    if (mounted) context.go(AppRoutes.login);
  }

  Future<void> _deleteAccount() async {
    final bool? confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Account?'),
        content: const Text(
          'Warning: This action will permanently erase your profile and credentials from the secure ledger.\n\nThis action is irreversible.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete Permanently'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      setState(() => _isLoading = true);
      try {
        await ApiService.delete('/auth/me');
        await SupabaseConfig.client.auth.signOut();
        if (mounted) {
          VFNotification.showSuccess(context, 'Account deleted successfully.');
          context.go(AppRoutes.login);
        }
      } catch (e) {
        if (mounted) {
          setState(() => _isLoading = false);
          VFNotification.showError(context, 'Failed to delete account. Please try again.');
        }
      }
    }
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
                  // Avatar + Name (Glassmorphic Container card)
                  VFCard(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      child: _buildProfileHeader(),
                    ),
                  ).animate().fadeIn(delay: 100.ms),
                  const SizedBox(height: AppSpacing.xl),

                  // Stats row with custom icons
                  _buildStats(),
                  const SizedBox(height: AppSpacing.xl),

                  // Account Settings Card (Interactive Profile & Password Editors)
                  VFCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.manage_accounts_rounded, color: AppColors.primary),
                            const SizedBox(width: AppSpacing.md),
                            Text(
                              'Account Settings',
                              style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        const Divider(height: 1, thickness: 0.5),
                        const SizedBox(height: AppSpacing.md),
                        
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.edit_rounded, color: AppColors.primary),
                          title: Text('Edit Profile Details', style: AppTypography.bodySmall),
                          trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
                          onTap: _showEditProfileModal,
                        ),
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.lock_reset_rounded, color: AppColors.primary),
                          title: Text('Change Password', style: AppTypography.bodySmall),
                          trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
                          onTap: _showChangePasswordModal,
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 250.ms),
                  const SizedBox(height: AppSpacing.xl),

                  // Nexus Security Engine Verification Card (Thematic MRV Ledger style)
                  VFCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.security_rounded, color: AppColors.primary),
                            const SizedBox(width: AppSpacing.md),
                            Text(
                              'Nexus Security Engine',
                              style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        const Divider(height: 1, thickness: 0.5),
                        const SizedBox(height: AppSpacing.md),
                        _buildSecurityRow('Verification Status', 'ACTIVE / VERIFIED', AppColors.primary),
                        const SizedBox(height: AppSpacing.sm),
                        _buildSecurityRow('Cryptographic Key', 'ECC-P256 (SHA-256)', AppColors.textSecondary),
                        const SizedBox(height: AppSpacing.sm),
                        _buildSecurityRow('Platform Sandbox', 'HARDWARE SECURED', AppColors.textSecondary),
                      ],
                    ),
                  ).animate().fadeIn(delay: 300.ms),
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

                  // Settings & Privacy (GDPR Compliance Card)
                  VFCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.settings_rounded, color: AppColors.primary),
                            const SizedBox(width: AppSpacing.md),
                            Text(
                              'Settings & Legal',
                              style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        const Divider(height: 1, thickness: 0.5),
                        const SizedBox(height: AppSpacing.md),
                        
                        // Privacy Policy Tile
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.privacy_tip_outlined, color: AppColors.primary),
                          title: Text('Privacy Policy', style: AppTypography.bodySmall),
                          trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
                          onTap: () {
                            showModalBottomSheet(
                              context: context,
                              backgroundColor: AppColors.surface,
                              shape: const RoundedRectangleBorder(
                                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                              ),
                              builder: (context) => Container(
                                padding: const EdgeInsets.all(AppSpacing.xl),
                                child: SingleChildScrollView(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Privacy & Data Protection', style: AppTypography.heading),
                                      const SizedBox(height: AppSpacing.md),
                                      const Text(
                                        'VeriField Nexus is committed to protecting your geospatial verification data. All recorded latitude and longitude values, clean cookstove household registrations, and attestation logs are encrypted locally and cryptographically signed before being saved to the ledger.\n\nYou have full authority to manage your data, including requesting permanent account erasure via the profile controls.',
                                        style: TextStyle(height: 1.5, color: Colors.white70),
                                      ),
                                      const SizedBox(height: AppSpacing.lg),
                                      SizedBox(
                                        width: double.infinity,
                                        child: VFButton(
                                          label: 'Close',
                                          onPressed: () => Navigator.pop(context),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                        
                        // Delete Account Tile
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.delete_forever_outlined, color: AppColors.error),
                          title: Text('Delete Account', style: AppTypography.bodySmall.copyWith(color: AppColors.error)),
                          trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.error),
                          onTap: _deleteAccount,
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 450.ms),
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
    final hasAvatar = _user?['avatar_url'] != null && _user!['avatar_url'].toString().isNotEmpty;
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: AppColors.primaryGradient,
            borderRadius: BorderRadius.circular(20),
            image: hasAvatar
                ? DecorationImage(
                    image: NetworkImage(_user!['avatar_url'].toString()),
                    fit: BoxFit.cover,
                  )
                : null,
          ),
          child: hasAvatar
              ? null
              : Center(
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
        Expanded(
          child: _statCard(
            'Pending Sync',
            '$_pendingCount',
            AppColors.warning,
            Icons.cloud_sync_rounded,
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: _statCard(
            'Verification Role',
            _user?['role'] == 'admin' ? 'Admin' : 'Field Agent',
            AppColors.accent,
            Icons.admin_panel_settings_rounded,
          ),
        ),
      ],
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _statCard(String label, String value, Color color, IconData icon) {
    return VFCard(
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: AppSpacing.sm),
          Text(value, style: AppTypography.title.copyWith(color: color, fontSize: 16)),
          const SizedBox(height: 4),
          Text(
            label,
            style: AppTypography.caption,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildSecurityRow(String label, String value, Color valueColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTypography.caption),
        Text(
          value,
          style: AppTypography.caption.copyWith(
            color: valueColor,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}
