// =============================================================================
// VeriField Nexus — Activity Form Screen
// =============================================================================
// Core screen for logging new field activities. Includes:
// - Activity type selection
// - Required photo capture
// - Automatic GPS capture
// - Optional property assignment
// - Offline-first submission
// =============================================================================

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/camera_service.dart';
import '../../../services/location_service.dart';
import '../../../services/sync_service.dart';
import '../../../services/local_db_service.dart';
import '../../../services/api_service.dart';
import '../../../services/device_service.dart';
import 'dart:convert';

class ActivityFormScreen extends StatefulWidget {
  const ActivityFormScreen({super.key});

  @override
  State<ActivityFormScreen> createState() => _ActivityFormScreenState();
}

class _ActivityFormScreenState extends State<ActivityFormScreen> {
  final _descriptionController = TextEditingController();
  final _customTypeController = TextEditingController();
  final _uuid = const Uuid();

  // Form state
  String _selectedType = 'cooking';
  File? _capturedImage;
  Map<String, double>? _locationData;
  bool _isSubmitting = false;
  bool _isCapturingLocation = false;
  String? _errorMessage;

  // Smart Context Detection state
  bool _isDetectingContext = false;
  Map<String, dynamic>? _nearbyAsset;
  bool _isNewInstallation = true;

  // Security prompts to enforce live, varied captures
  final List<String> _securityPrompts = [
    'Take a wide-angle shot',
    'Move closer to the asset',
    'Take the photo from a different angle',
    'Ensure background context is visible',
    'Show the asset clearly in focus',
  ];

  // Activity type options
  final List<Map<String, dynamic>> _activityTypes = [
    {'id': 'cooking', 'label': 'Clean Cooking', 'icon': Icons.local_fire_department_rounded, 'color': AppColors.warning},
    {'id': 'farming', 'label': 'Agriculture', 'icon': Icons.grass_rounded, 'color': AppColors.primary},
    {'id': 'energy', 'label': 'Energy Use', 'icon': Icons.bolt_rounded, 'color': AppColors.accent},
    {'id': 'sustainability', 'label': 'Sustainability', 'icon': Icons.eco_rounded, 'color': AppColors.accentPurple},
    {'id': 'other', 'label': 'Other', 'icon': Icons.more_horiz_rounded, 'color': AppColors.textTertiary},
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initCameraFirstFlow();
    });
  }

  Future<void> _initCameraFirstFlow() async {
    await _captureLocation();
    await _capturePhoto();
    await _performSmartContextDetection();
  }

  Future<void> _performSmartContextDetection() async {
    if (_locationData == null) return;
    
    setState(() => _isDetectingContext = true);
    
    try {
      final cached = await LocalDbService.getCachedActivities();
      for (var activity in cached) {
        if (activity['latitude'] != null && activity['longitude'] != null) {
          final latDiff = (_locationData!['latitude']! - (activity['latitude'] as num)).abs();
          final lngDiff = (_locationData!['longitude']! - (activity['longitude'] as num)).abs();
          
          // Approx 30 meters is ~0.0003 degrees
          if (latDiff < 0.0003 && lngDiff < 0.0003) {
            _nearbyAsset = {
              'id': activity['property_id'] ?? 'unknown',
              'name': 'Existing Asset',
              'type': activity['activity_type'] ?? 'cooking',
            };
            _isNewInstallation = false;
            break;
          }
        }
      }
    } catch (e) {
      debugPrint('Error detecting context: $e');
    } finally {
      if (mounted) setState(() => _isDetectingContext = false);
    }
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    super.dispose();
  }

  /// Auto-capture GPS coordinates.
  Future<void> _captureLocation() async {
    setState(() => _isCapturingLocation = true);
    _locationData = await LocationService.getLocationData();
    if (mounted) setState(() => _isCapturingLocation = false);
  }

  /// Open camera to capture photo proof with security prompt.
  Future<void> _capturePhoto() async {
    final String prompt = _securityPrompts[DateTime.now().millisecond % _securityPrompts.length];
    
    // Force acknowledgment of the security prompt
    final bool? proceed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Row(
          children: [
            const Icon(Icons.security_rounded, color: AppColors.warning),
            const SizedBox(width: AppSpacing.sm),
            Text('Security Prompt', style: AppTypography.title),
          ],
        ),
        content: Text(
          'To verify this submission, please:\n\n"$prompt"\n\nThis ensures authenticity and prevents fraud.',
          style: AppTypography.bodySmall,
        ),
        actions: [
          TextButton(
            onPressed: () => context.pop(false),
            child: Text('Cancel', style: AppTypography.bodySmall),
          ),
          VFButton(
            label: 'Open Camera',
            icon: Icons.camera_alt_rounded,
            onPressed: () => context.pop(true),
          ),
        ],
      ),
    );

    if (proceed != true) return;

    final photo = await CameraService.capturePhoto();
    if (photo != null && mounted) {
      setState(() => _capturedImage = photo);
    }
  }

  /// Submit the activity (online or offline).
  Future<void> _submitActivity() async {
    // Validate required fields
    if (_capturedImage == null) {
      setState(() => _errorMessage = 'Photo proof is required');
      return;
    }
    
    // Prevent submission if GPS accuracy is poor
    if (_locationData == null || _locationData!['accuracy'] == null) {
      setState(() => _errorMessage = 'GPS location is required');
      return;
    }
    
    if (_locationData!['accuracy']! > 100) {
      setState(() => _errorMessage = 'GPS accuracy is too poor (${_locationData!['accuracy']!.toStringAsFixed(0)}m). Move outside for a better signal.');
      return;
    }

    setState(() { _isSubmitting = true; _errorMessage = null; });

    final clientId = _uuid.v4();
    final capturedAt = DateTime.now().toUtc().toIso8601String();
    final imageHash = await CameraService.generateImageHash(_capturedImage!);
    final deviceSignature = await DeviceService.getDeviceSignature();

    try {
      final isOnline = await SyncService.isOnline();

      if (isOnline) {
        // Online: Upload image and submit directly
        final imageName = '${clientId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
        final imageUrl = await SyncService.uploadImage(_capturedImage!, imageName);

        final response = await ApiService.post('/activities', body: {
          'activity_type': _selectedType,
          'activity_data': {
            'device_signature': deviceSignature,
            if (_selectedType == 'other' && _customTypeController.text.isNotEmpty)
              'custom_type': _customTypeController.text.trim(),
            if (_isNewInstallation)
              'asset_name': _selectedType == 'other' && _customTypeController.text.isNotEmpty
                  ? _customTypeController.text.trim()
                  : 'New ${_selectedType.toUpperCase()} Installation',
          },
          'property_id': _isNewInstallation ? null : _nearbyAsset?['id'],
          'description': _descriptionController.text.trim().isNotEmpty
              ? _descriptionController.text.trim() : null,
          'image_url': imageUrl,
          'image_hash': imageHash,
          'latitude': _locationData?['latitude'],
          'longitude': _locationData?['longitude'],
          'gps_accuracy': _locationData?['accuracy'],
          'captured_at': capturedAt,
          'client_id': clientId,
        });

        if (mounted) {
          if (response['status'] == 'flagged') {
            await showDialog(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Row(
                  children: [
                    Icon(Icons.warning_amber_rounded, color: AppColors.error),
                    SizedBox(width: 8),
                    Text('Anomaly Detected'),
                  ],
                ),
                content: const Text(
                  'Your submission was flagged by the Trust Engine. Please ensure GPS accuracy and clear photo evidence next time. This activity will require manual review.',
                ),
                actions: [
                  TextButton(
                    onPressed: () => ctx.pop(),
                    child: const Text('Understood'),
                  ),
                ],
              ),
            );
            if (mounted) context.pop();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Activity submitted successfully! ✅')),
            );
            context.pop();
          }
        }
      } else {
        // Offline: Save locally for later sync
        await LocalDbService.savePendingActivity({
          'id': clientId,
          'client_id': clientId,
          'activity_type': _selectedType,
          'property_id': _isNewInstallation ? null : _nearbyAsset?['id'],
          'activity_data': jsonEncode({
            'device_signature': deviceSignature,
            if (_selectedType == 'other' && _customTypeController.text.isNotEmpty)
              'custom_type': _customTypeController.text.trim(),
            if (_isNewInstallation)
              'asset_name': _selectedType == 'other' && _customTypeController.text.isNotEmpty
                  ? _customTypeController.text.trim()
                  : 'New ${_selectedType.toUpperCase()} Installation',
          }),
          'description': _descriptionController.text.trim(),
          'image_path': _capturedImage!.path,
          'image_hash': imageHash,
          'latitude': _locationData?['latitude'],
          'longitude': _locationData?['longitude'],
          'gps_accuracy': _locationData?['accuracy'],
          'captured_at': capturedAt,
          'created_at': capturedAt,
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Saved offline. Will sync when connected. 📱')),
          );
          context.pop();
        }
      }
    } catch (e) {
      setState(() => _errorMessage = 'Submission failed: ${e.toString()}');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Log Activity'),
        leading: IconButton(
          icon: const Icon(Icons.close_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- Smart Context Detection UI ---
            _buildSmartContextUI(),
            const SizedBox(height: AppSpacing.xl),

            // --- Custom Type (if Other) ---
            if (_selectedType == 'other') ...[
              VFTextField(
                label: 'Specify Custom Activity *',
                hint: 'e.g., Water Filter Distribution',
                controller: _customTypeController,
                prefixIcon: const Icon(Icons.edit_note_rounded, color: AppColors.textTertiary),
              ).animate().fadeIn(),
              const SizedBox(height: AppSpacing.xl),
            ],

            // --- Photo Capture ---
            _buildPhotoCapture(),
            const SizedBox(height: AppSpacing.xl),

            // --- GPS Status ---
            _buildGpsStatus(),
            const SizedBox(height: AppSpacing.xl),

            // --- Description ---
            VFTextField(
              label: 'Description (Optional)',
              hint: 'Add notes about this activity...',
              controller: _descriptionController,
              maxLines: 3,
              prefixIcon: const Icon(Icons.notes_rounded, color: AppColors.textTertiary),
            ).animate().fadeIn(delay: 300.ms),
            const SizedBox(height: AppSpacing.xl),

            // --- Error Message ---
            if (_errorMessage != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                margin: const EdgeInsets.only(bottom: AppSpacing.base),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                ),
                child: Text(_errorMessage!, style: AppTypography.bodySmall.copyWith(color: AppColors.error)),
              ),

            // --- Submit Button ---
            SizedBox(
              width: double.infinity,
              child: VFButton(
                label: 'Submit Activity',
                onPressed: _submitActivity,
                isLoading: _isSubmitting,
                icon: Icons.send_rounded,
              ),
            ).animate().fadeIn(delay: 400.ms),
          ],
        ),
      ),
    );
  }

  /// Build the Smart Context Detection UI.
  Widget _buildSmartContextUI() {
    if (_isDetectingContext) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            const SizedBox(
              width: 20, height: 20,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
            ),
            const SizedBox(width: AppSpacing.md),
            Text('Scanning for nearby assets...', style: AppTypography.bodySmall),
          ],
        ),
      );
    }

    if (_nearbyAsset != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.location_on, color: AppColors.primary, size: 20),
                const SizedBox(width: AppSpacing.sm),
                Text('Asset Found Nearby', style: AppTypography.title.copyWith(fontSize: 16)),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text('System detected an existing installation within 30 meters.', style: AppTypography.bodySmall),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => setState(() => _isNewInstallation = false),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: !_isNewInstallation ? AppColors.primary : AppColors.surface,
                      foregroundColor: !_isNewInstallation ? Colors.white : AppColors.textPrimary,
                      side: BorderSide(color: !_isNewInstallation ? AppColors.primary : AppColors.border),
                      elevation: 0,
                    ),
                    child: const Text('Check-in Existing'),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => setState(() => _isNewInstallation = true),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _isNewInstallation ? AppColors.primary : AppColors.surface,
                      foregroundColor: _isNewInstallation ? Colors.white : AppColors.textPrimary,
                      side: BorderSide(color: _isNewInstallation ? AppColors.primary : AppColors.border),
                      elevation: 0,
                    ),
                    child: const Text('Register New'),
                  ),
                ),
              ],
            ),
            if (_isNewInstallation) ...[
              const SizedBox(height: AppSpacing.xl),
              _buildTypeSelector(),
            ]
          ],
        ),
      ).animate().fadeIn();
    }

    // No asset found nearby
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.add_circle_outline, color: AppColors.primary, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Text('Register New Installation', style: AppTypography.title.copyWith(fontSize: 16)),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text('No previous assets found within 30 meters.', style: AppTypography.bodySmall),
          const SizedBox(height: AppSpacing.lg),
          _buildTypeSelector(),
        ],
      ),
    ).animate().fadeIn();
  }

  /// Build the activity type selector chips.
  Widget _buildTypeSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Activity Type', style: AppTypography.bodySmall),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: _activityTypes.map((type) {
            final isSelected = _selectedType == type['id'];
            return GestureDetector(
              onTap: () => setState(() => _selectedType = type['id']),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: isSelected ? (type['color'] as Color).withValues(alpha: 0.15) : AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                  border: Border.all(
                    color: isSelected ? type['color'] as Color : AppColors.border,
                    width: isSelected ? 2 : 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(type['icon'] as IconData, size: 18, color: type['color'] as Color),
                    const SizedBox(width: 8),
                    Text(
                      type['label'] as String,
                      style: AppTypography.bodySmall.copyWith(
                        color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    ).animate().fadeIn(delay: 100.ms);
  }

  /// Build the photo capture section.
  Widget _buildPhotoCapture() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Photo Proof *', style: AppTypography.bodySmall),
        const SizedBox(height: AppSpacing.md),
        GestureDetector(
          onTap: _capturePhoto,
          child: Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
              border: Border.all(
                color: _capturedImage != null ? AppColors.primary : AppColors.border,
                width: _capturedImage != null ? 2 : 1,
              ),
            ),
            child: _capturedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(AppSpacing.radiusLg - 1),
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        kIsWeb ? Image.network(_capturedImage!.path, fit: BoxFit.cover) : Image.file(_capturedImage!, fit: BoxFit.cover),
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: AppColors.primary,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Icon(Icons.check, color: Colors.white, size: 16),
                          ),
                        ),
                        // Retake overlay
                        Positioned(
                          bottom: 8,
                          right: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: Colors.black54,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text('Tap to retake', style: AppTypography.caption.copyWith(color: Colors.white)),
                          ),
                        ),
                      ],
                    ),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.camera_alt_rounded, size: 48, color: AppColors.textTertiary),
                      const SizedBox(height: AppSpacing.sm),
                      Text('Tap to capture photo', style: AppTypography.bodySmall),
                    ],
                  ),
          ),
        ),
      ],
    ).animate().fadeIn(delay: 200.ms);
  }

  /// Build the GPS status indicator.
  Widget _buildGpsStatus() {
    return VFCard(
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _locationData != null
                  ? AppColors.primary.withValues(alpha: 0.15)
                  : AppColors.warning.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              _isCapturingLocation
                  ? Icons.gps_not_fixed_rounded
                  : _locationData != null
                      ? Icons.gps_fixed_rounded
                      : Icons.gps_off_rounded,
              color: _locationData != null ? AppColors.primary : AppColors.warning,
              size: 20,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('GPS Location', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
                Text(
                  _isCapturingLocation
                      ? 'Acquiring location...'
                      : _locationData != null
                          ? '${_locationData!['latitude']!.toStringAsFixed(4)}, ${_locationData!['longitude']!.toStringAsFixed(4)}'
                          : 'Location unavailable',
                  style: AppTypography.caption,
                ),
              ],
            ),
          ),
          if (!_isCapturingLocation)
            IconButton(
              icon: const Icon(Icons.refresh_rounded, color: AppColors.textTertiary),
              onPressed: _captureLocation,
            ),
        ],
      ),
    );
  }
}
