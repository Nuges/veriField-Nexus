// =============================================================================
// VeriField Nexus — Activity Registration Form (Dynamic Form Engine)
// =============================================================================
// Progressive step-by-step form:
//   Step 0: Activity type selection (Clean Cooking / Hybrid Energy)
//   Step 1: Dynamic detail fields for the selected type
//   Step 2: Photo capture + GPS lock
//   Step 3: Review & submit
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
import '../../../core/config/supabase_config.dart';
import '../../../services/camera_service.dart';
import '../../../services/location_service.dart';
import '../../../services/sync_service.dart';
import '../../../services/local_db_service.dart';
import '../../../services/api_service.dart';
import '../../../services/device_service.dart';
import '../models/activity_type_config.dart';
import 'dart:convert';

class ActivityFormScreen extends StatefulWidget {
  const ActivityFormScreen({super.key});

  @override
  State<ActivityFormScreen> createState() => _ActivityFormScreenState();
}

class _ActivityFormScreenState extends State<ActivityFormScreen> {
  final _uuid = const Uuid();
  int _currentStep = 0;

  // Activity type — selected in step 0
  String? _selectedTypeId;
  ActivityTypeConfig? _selectedConfig;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _captureLocation());
  }

  // Step 2: Dynamic field values
  final Map<String, dynamic> _fieldValues = {};
  final Map<String, TextEditingController> _textControllers = {};

  // Step 3: Photo + GPS
  final Map<String, File> _capturedImages = {};
  final Map<String, Map<String, dynamic>> _capturedImagesMetadata = {};
  Map<String, double>? _locationData;
  bool _isCapturingLocation = false;

  // GPS duplicate check
  Map<String, dynamic>? _duplicateCheckResult;
  bool _isCheckingDuplicate = false;
  String? _overrideReason;
  final _overrideController = TextEditingController();
  final _descriptionController = TextEditingController();

  // Submission
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    for (final c in _textControllers.values) {
      c.dispose();
    }
    _overrideController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  // =========================================================================
  // Step Navigation
  // =========================================================================

  bool get _canProceed {
    switch (_currentStep) {
      case 0:
        return _selectedTypeId != null && _selectedConfig != null;
      case 1:
        return _validateDynamicFields();
      case 2:
        if (_locationData == null) return false;
        if (_selectedConfig == null) return false;
        for (final p in _selectedConfig!.photos) {
          if (p.required && !_capturedImages.containsKey(p.key)) {
            return false;
          }
        }
        return true;
      default:
        return true;
    }
  }

  Future<void> _nextStep() async {
    if (!_canProceed) return;
    if (_currentStep == 2) {
      // After photo/GPS step, run duplicate check if not done
      if (_duplicateCheckResult == null && _locationData != null) {
        await _runDuplicateCheck();
      }
    }
    if (mounted) {
      setState(() => _currentStep++);
    }
  }

  void _prevStep() {
    if (_currentStep > 0) setState(() => _currentStep--);
  }

  // =========================================================================
  // Dynamic Field Validation
  // =========================================================================

  bool _validateDynamicFields() {
    if (_selectedConfig == null) return false;
    for (final field in _selectedConfig!.fields) {
      if (field.required) {
        final val = _fieldValues[field.key];
        if (val == null || (val is String && val.isEmpty)) return false;
      }
    }
    return true;
  }

  TextEditingController _controllerFor(String key) {
    return _textControllers.putIfAbsent(key, () => TextEditingController());
  }

  // =========================================================================
  // GPS + Duplicate Check
  // =========================================================================

  Future<void> _captureLocation() async {
    setState(() => _isCapturingLocation = true);
    _locationData = await LocationService.getLocationData();
    if (mounted) setState(() => _isCapturingLocation = false);
  }

  Future<void> _runDuplicateCheck() async {
    if (_locationData == null || _selectedTypeId == null) return;
    setState(() => _isCheckingDuplicate = true);
    try {
      final result = await ApiService.post('/installations/check-duplicate', body: {
        'latitude': _locationData!['latitude'],
        'longitude': _locationData!['longitude'],
        'activity_type': _selectedTypeId,
      });
      _duplicateCheckResult = result;
    } catch (_) {
      // Offline or error — skip duplicate check
      _duplicateCheckResult = {'duplicate_flag': false, 'environment_type': 'RURAL', 'radius_used_m': 30};
    }
    if (mounted) setState(() => _isCheckingDuplicate = false);
  }

  // =========================================================================
  // Photo Capture
  // =========================================================================

  Future<void> _capturePhoto(PhotoFieldDef photo) async {
    final proceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Row(children: [
          const Icon(Icons.camera_alt_rounded, color: AppColors.primary),
          const SizedBox(width: AppSpacing.sm),
          Text(photo.label, style: AppTypography.title),
        ]),
        content: Text('${photo.prompt}\n\nThis is required for audit-grade MRV verification.', style: AppTypography.bodySmall),
        actions: [
          TextButton(onPressed: () => ctx.pop(false), child: const Text('Cancel')),
          VFButton(label: 'Open Camera', icon: Icons.camera_alt_rounded, onPressed: () => ctx.pop(true)),
        ],
      ),
    );
    if (proceed != true) return;
    final file = await CameraService.capturePhoto();
    if (file != null && mounted) {
      final location = await LocationService.getLocationData();
      final timestamp = DateTime.now().toUtc().toIso8601String();
      final deviceId = await DeviceService.getDeviceSignature();
      final uploaderId = SupabaseConfig.client.auth.currentUser?.id ?? 'agent';
      final hash = await CameraService.generateImageHash(file);
      
      setState(() {
        _capturedImages[photo.key] = file;
        _capturedImagesMetadata[photo.key] = {
          'timestamp': timestamp,
          'latitude': location?['latitude'] ?? _locationData?['latitude'],
          'longitude': location?['longitude'] ?? _locationData?['longitude'],
          'device_id': deviceId,
          'uploader_id': uploaderId,
          'hash': hash,
        };
      });
    }
  }

  // =========================================================================
  // Submission
  // =========================================================================

  Future<void> _submitInstallation() async {
    if (_selectedConfig == null || _locationData == null || _isCheckingDuplicate) return;

    // Check if duplicate override needs reason
    final isDuplicate = _duplicateCheckResult?['duplicate_flag'] == true;
    if (isDuplicate && (_overrideReason == null || _overrideReason!.isEmpty)) {
      setState(() => _errorMessage = 'Please provide an override reason for the nearby duplicate.');
      return;
    }

    // Determine primary key based on activity type
    final primaryKey = _selectedTypeId == 'HYBRID_ENERGY' ? 'solar_installation' : 'stove_installation';
    final primaryImage = _capturedImages[primaryKey];
    if (primaryImage == null) {
      setState(() => _errorMessage = 'Primary installation photo is required.');
      return;
    }

    setState(() { _isSubmitting = true; _errorMessage = null; });

    final clientId = _uuid.v4();
    final capturedAt = DateTime.now().toUtc().toIso8601String();
    final deviceSignature = await DeviceService.getDeviceSignature();

    final activityData = Map<String, dynamic>.from(_fieldValues);
    activityData['device_signature'] = deviceSignature;
    activityData['image_metadata'] = _capturedImagesMetadata;

    try {
      final isOnline = await SyncService.isOnline();

      if (isOnline) {
        // Atomic Uploads: Upload primary image first
        final primaryName = '${clientId}_primary.jpg';
        final primaryUrl = await SyncService.uploadImage(primaryImage, primaryName);
        if (primaryUrl == null) {
          throw Exception('Failed to upload primary installation image');
        }
        
        final Map<String, String> uploadedUrls = {
          '${primaryKey}_image_url': primaryUrl,
        };

        // Upload additional images
        for (final key in _capturedImages.keys) {
          if (key != primaryKey) {
            final file = _capturedImages[key]!;
            final fileName = '${clientId}_$key.jpg';
            final url = await SyncService.uploadImage(file, fileName);
            if (url == null) {
              throw Exception('Failed to upload $key image');
            }
            uploadedUrls['${key}_image_url'] = url;
          }
        }

        // Add all URLs to activityData
        activityData.addAll(uploadedUrls);

        await ApiService.post('/installations', body: {
          'activity_type': _selectedTypeId,
          'activity_data': activityData,
          'description': _descriptionController.text,
          'image_url': primaryUrl,
          'image_hash': _capturedImagesMetadata[primaryKey]?['hash'] ?? '',
          'latitude': _locationData!['latitude'],
          'longitude': _locationData!['longitude'],
          'gps_accuracy': _locationData!['accuracy'],
          'environment_type': _duplicateCheckResult?['environment_type'],
          'radius_used_m': _duplicateCheckResult?['radius_used_m'],
          'duplicate_flag': isDuplicate,
          'override_reason': _overrideReason,
          'captured_at': capturedAt,
          'client_id': clientId,
        });

        if (mounted) {
          VFNotification.showSuccess(context, 'Installation registered successfully! ✅');
          context.pop(true);
        }
      } else {
        // Offline Mode: store local file paths inside activity_data
        for (final key in _capturedImages.keys) {
          activityData['${key}_image_path'] = _capturedImages[key]!.path;
        }

        await LocalDbService.savePendingActivity({
          'id': clientId,
          'client_id': clientId,
          'activity_type': _selectedTypeId,
          'activity_data': jsonEncode(activityData),
          'description': _descriptionController.text,
          'image_path': primaryImage.path,
          'image_hash': _capturedImagesMetadata[primaryKey]?['hash'] ?? '',
          'latitude': _locationData!['latitude'],
          'longitude': _locationData!['longitude'],
          'gps_accuracy': _locationData!['accuracy'],
          'captured_at': capturedAt,
          'created_at': capturedAt,
        });
        if (mounted) {
          VFNotification.showSuccess(context, 'Saved offline. Will sync when connected. 📱');
          context.pop(true);
        }
      }
    } catch (e) {
      setState(() => _errorMessage = 'Submission failed: $e');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  // =========================================================================
  // BUILD
  // =========================================================================

  /// Resolve AppBar title based on the selected activity type.
  String get _appBarTitle {
    switch (_selectedTypeId) {
      case 'CLEAN_COOKING':
        return 'Register Cookstove';
      case 'HYBRID_ENERGY':
        return 'Register Energy System';
      default:
        return 'New Activity';
    }
  }

  @override
  Widget build(BuildContext context) {
    final steps = ['Type', 'Details', 'Capture', 'Review'];
    return Scaffold(
      appBar: AppBar(
        title: Text(_appBarTitle),
        leading: IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => context.pop()),
      ),
      body: Column(
        children: [
          // Progress indicator
          _buildProgressBar(steps),
          // Step content
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: _buildCurrentStep(),
            ),
          ),
          // Navigation buttons
          _buildNavButtons(),
        ],
      ),
    );
  }

  Widget _buildProgressBar(List<String> steps) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.md),
      child: Row(
        children: List.generate(steps.length, (i) {
          final isActive = i == _currentStep;
          final isDone = i < _currentStep;
          return Expanded(
            child: Row(children: [
              Container(
                width: 28, height: 28,
                decoration: BoxDecoration(
                  color: isDone ? AppColors.primary : isActive ? AppColors.primary.withValues(alpha: 0.2) : AppColors.border,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Center(child: isDone
                    ? const Icon(Icons.check, size: 16, color: Colors.white)
                    : Text('${i + 1}', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700,
                        color: isActive ? AppColors.primary : AppColors.textTertiary))),
              ),
              if (i < steps.length - 1)
                Expanded(child: Container(height: 2, color: isDone ? AppColors.primary : AppColors.border)),
            ]),
          );
        }),
      ),
    );
  }

  Widget _buildNavButtons() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.border, width: 0.5)),
      ),
      child: Row(children: [
        if (_currentStep > 0)
          Expanded(
            child: VFButton(label: 'Back', onPressed: _prevStep, isOutlined: true, icon: Icons.arrow_back_rounded),
          ),
        if (_currentStep > 0) const SizedBox(width: AppSpacing.md),
        Expanded(
          flex: 2,
          child: _currentStep == 3
              ? VFButton(label: 'Submit', onPressed: _canProceed ? _submitInstallation : null,
                  isLoading: _isSubmitting, icon: Icons.send_rounded)
              : VFButton(label: 'Continue', onPressed: _canProceed ? _nextStep : null,
                  isLoading: _isCheckingDuplicate,
                  icon: Icons.arrow_forward_rounded),
        ),
      ]),
    );
  }

  // =========================================================================
  // STEP BUILDERS
  // =========================================================================

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case 0: return _buildTypeSelection();
      case 1: return _buildDynamicFields();
      case 2: return _buildCaptureStep();
      case 3: return _buildReviewStep();
      default: return const SizedBox();
    }
  }

  // --- Step 0: Activity Type Selection ---
  Widget _buildTypeSelection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Select Activity Type', style: AppTypography.heading).animate().fadeIn(),
        const SizedBox(height: AppSpacing.sm),
        Text('Choose the type of field activity you are registering.',
            style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary)),
        const SizedBox(height: AppSpacing.xl),
        ...activityTypes.asMap().entries.map((entry) {
          final i = entry.key;
          final config = entry.value;
          final isSelected = _selectedTypeId == config.id;
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.base),
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _selectedTypeId = config.id;
                  _selectedConfig = config;
                  // Clear previous field values when switching types
                  _fieldValues.clear();
                  for (final c in _textControllers.values) {
                    c.clear();
                  }
                  // Pre-initialize boolean fields to false to prevent required-field null validation failure
                  for (final field in config.fields) {
                    if (field.type == 'boolean') {
                      _fieldValues[field.key] = false;
                    }
                  }
                });
              },
              child: Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: isSelected ? config.color.withValues(alpha: 0.08) : AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                  border: Border.all(
                    color: isSelected ? AppColors.primary : AppColors.border,
                    width: isSelected ? 2 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    // Icon container
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: config.color.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(config.icon, color: config.color, size: 28),
                    ),
                    const SizedBox(width: AppSpacing.base),
                    // Label, description, methodology
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(config.label, style: AppTypography.title.copyWith(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 2),
                          Text(config.description, style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary)),
                          const SizedBox(height: 4),
                          Text(config.methodology, style: AppTypography.caption.copyWith(color: AppColors.primary)),
                        ],
                      ),
                    ),
                    // Selected checkmark
                    if (isSelected)
                      Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                          color: AppColors.primary,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(Icons.check, size: 16, color: Colors.white),
                      ),
                  ],
                ),
              ),
            ).animate().fadeIn(delay: Duration(milliseconds: 120 * i)).slideX(begin: 0.05),
          );
        }),
      ],
    );
  }

  // --- Step 1: Dynamic Fields ---
  Widget _buildDynamicFields() {
    final config = _selectedConfig!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(config.icon, color: config.color, size: 24),
          const SizedBox(width: AppSpacing.sm),
          Text(config.label, style: AppTypography.heading),
        ]).animate().fadeIn(),
        const SizedBox(height: 4),
        Text(config.methodology, style: AppTypography.caption.copyWith(color: AppColors.primary)),
        const SizedBox(height: AppSpacing.xl),
        ...config.fields.asMap().entries.map((entry) {
          final i = entry.key;
          final field = entry.value;
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.base),
            child: _buildField(field).animate().fadeIn(delay: Duration(milliseconds: 80 * i)),
          );
        }),
        const SizedBox(height: AppSpacing.md),
        const Divider(height: 1, thickness: 0.5),
        const SizedBox(height: AppSpacing.lg),
        VFTextField(
          label: "Reporting Agent's Notes",
          hint: _selectedTypeId == 'HYBRID_ENERGY'
              ? "System condition, site observations, or energy audit notes..."
              : "Stove condition, household reception, or carbon audit notes...",
          controller: _descriptionController,
          maxLines: 4,
        ).animate().fadeIn(delay: Duration(milliseconds: 80 * (config.fields.length + 1))),
      ],
    );
  }

  Widget _buildField(FormFieldDef field) {
    switch (field.type) {
      case 'enum':
        return _buildEnumField(field);
      case 'boolean':
        return _buildBoolField(field);
      case 'int':
      case 'float':
        return _buildNumberField(field);
      case 'text':
        return VFTextField(
          label: '${field.label}${field.required ? " *" : ""}',
          hint: 'Enter ${field.label.toLowerCase()}',
          controller: _controllerFor(field.key),
          maxLines: 3,
          onChanged: (v) => setState(() => _fieldValues[field.key] = v),
        );
      default:
        return VFTextField(
          label: '${field.label}${field.required ? " *" : ""}',
          hint: 'Enter ${field.label.toLowerCase()}',
          controller: _controllerFor(field.key),
          onChanged: (v) => setState(() => _fieldValues[field.key] = v),
        );
    }
  }

  Widget _buildEnumField(FormFieldDef field) {
    final current = _fieldValues[field.key] as String?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('${field.label}${field.required ? " *" : ""}',
            style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm, runSpacing: AppSpacing.sm,
          children: (field.options ?? []).map((opt) {
            final isSelected = current == opt;
            return GestureDetector(
              onTap: () => setState(() => _fieldValues[field.key] = opt),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.primary.withValues(alpha: 0.15) : AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                  border: Border.all(color: isSelected ? AppColors.primary : AppColors.border),
                ),
                child: Text(opt.replaceAll('_', ' ').toUpperCase(),
                    style: AppTypography.caption.copyWith(
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w400,
                      color: isSelected ? AppColors.primary : AppColors.textSecondary,
                    )),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildBoolField(FormFieldDef field) {
    final val = _fieldValues[field.key] as bool? ?? false;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text('${field.label}${field.required ? " *" : ""}',
            style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
        Switch.adaptive(value: val, activeColor: AppColors.primary,
            onChanged: (v) => setState(() => _fieldValues[field.key] = v)),
      ],
    );
  }

  Widget _buildNumberField(FormFieldDef field) {
    return VFTextField(
      label: '${field.label}${field.required ? " *" : ""}',
      hint: 'Enter ${field.label.toLowerCase()}',
      controller: _controllerFor(field.key),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      onChanged: (v) {
        setState(() {
          if (v.isEmpty) { _fieldValues.remove(field.key); return; }
          _fieldValues[field.key] = field.type == 'int' ? int.tryParse(v) ?? 0 : double.tryParse(v) ?? 0.0;
        });
      },
    );
  }

  // --- Step 2: Capture ---
  Widget _buildCaptureStep() {
    final config = _selectedConfig!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Capture Evidence', style: AppTypography.heading).animate().fadeIn(),
        const SizedBox(height: AppSpacing.xl),
        // GPS
        VFCard(child: Row(children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: _locationData != null ? AppColors.primary.withValues(alpha: 0.15) : AppColors.warning.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              _isCapturingLocation ? Icons.gps_not_fixed_rounded
                  : _locationData != null ? Icons.gps_fixed_rounded : Icons.gps_off_rounded,
              color: _locationData != null ? AppColors.primary : AppColors.warning, size: 22,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('GPS Location', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
            Text(_isCapturingLocation ? 'Acquiring...'
                : _locationData != null
                    ? '${_locationData!['latitude']!.toStringAsFixed(5)}, ${_locationData!['longitude']!.toStringAsFixed(5)}'
                    : 'Tap to capture',
                style: AppTypography.caption),
            if (_locationData != null && _locationData!['accuracy'] != null)
              Text('Accuracy: ${_locationData!['accuracy']!.toStringAsFixed(0)}m',
                  style: AppTypography.caption.copyWith(color: AppColors.primary)),
          ])),
          IconButton(icon: const Icon(Icons.my_location_rounded, color: AppColors.primary), onPressed: _captureLocation),
        ])).animate().fadeIn(),
        const SizedBox(height: AppSpacing.xl),
        
        // Dynamic Multi-Photo Cards
        ...config.photos.asMap().entries.map((entry) {
          final idx = entry.key;
          final photoDef = entry.value;
          final file = _capturedImages[photoDef.key];
          final isCaptured = file != null;
          
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('${photoDef.label}${photoDef.required ? " *" : ""}',
                        style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
                    if (isCaptured)
                      const Text('✅ CAPTURED', style: TextStyle(color: AppColors.primary, fontSize: 10, fontWeight: FontWeight.bold))
                    else if (photoDef.required)
                      const Text('* REQUIRED', style: TextStyle(color: AppColors.error, fontSize: 10, fontWeight: FontWeight.bold))
                    else
                      const Text('OPTIONAL', style: TextStyle(color: AppColors.textTertiary, fontSize: 10)),
                  ],
                ),
                const SizedBox(height: AppSpacing.xs),
                GestureDetector(
                  onTap: () => _capturePhoto(photoDef),
                  child: Container(
                    height: 150, width: double.infinity,
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                      border: Border.all(
                        color: isCaptured ? AppColors.primary : AppColors.border,
                        width: isCaptured ? 2 : 1,
                      ),
                    ),
                    child: isCaptured
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(AppSpacing.radiusLg - 1),
                            child: Stack(fit: StackFit.expand, children: [
                              kIsWeb ? Image.network(file.path, fit: BoxFit.cover) : Image.file(file, fit: BoxFit.cover),
                              Positioned(top: 8, right: 8, child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(20)),
                                child: const Icon(Icons.check, color: Colors.white, size: 14),
                              )),
                            ]))
                        : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            const Icon(Icons.camera_alt_rounded, size: 36, color: AppColors.textTertiary),
                            const SizedBox(height: AppSpacing.xs),
                            Text('Tap to capture ${photoDef.label.toLowerCase()}', style: AppTypography.bodySmall),
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: 4),
                              child: Text(
                                photoDef.prompt,
                                style: AppTypography.caption.copyWith(color: AppColors.textTertiary),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ]),
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(delay: Duration(milliseconds: 100 * idx));
        }),
      ],
    );
  }

  // --- Step 3: Review ---
  Widget _buildReviewStep() {
    final isDuplicate = _duplicateCheckResult?['duplicate_flag'] == true;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Review Installation', style: AppTypography.heading).animate().fadeIn(),
        const SizedBox(height: AppSpacing.xl),
        // Duplicate warning
        if (isDuplicate) ...[
          Container(
            padding: const EdgeInsets.all(AppSpacing.base),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
              border: Border.all(color: AppColors.warning.withValues(alpha: 0.4)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.warning_amber_rounded, color: AppColors.warning),
                const SizedBox(width: AppSpacing.sm),
                Text('Similar installation nearby', style: AppTypography.title.copyWith(color: AppColors.warning)),
              ]),
              const SizedBox(height: AppSpacing.sm),
              Text('${_duplicateCheckResult!['nearby_count']} installation(s) found within ${_duplicateCheckResult!['radius_used_m']}m. '
                  'Environment: ${_duplicateCheckResult!['environment_type']}', style: AppTypography.caption),
              const SizedBox(height: AppSpacing.md),
              VFTextField(
                label: 'Override Reason *',
                hint: 'e.g., Different household, new unit',
                controller: _overrideController,
                onChanged: (v) => _overrideReason = v,
              ),
            ]),
          ).animate().fadeIn().shake(hz: 2, offset: const Offset(2, 0)),
          const SizedBox(height: AppSpacing.xl),
        ],
        // Summary
        if (_isCheckingDuplicate) ...[
          const Center(child: CircularProgressIndicator(color: AppColors.primary)),
          const SizedBox(height: AppSpacing.xl),
        ],
        _reviewRow('Type', _selectedConfig?.label ?? 'Unknown'),
        _reviewRow('Notes', _descriptionController.text.isNotEmpty ? _descriptionController.text : 'None'),
        _reviewRow('Environment', _duplicateCheckResult?['environment_type'] ?? 'Detecting...'),
        ..._fieldValues.entries.map((e) => _reviewRow(
          e.key.replaceAll('_', ' ').split(' ').map((w) => '${w[0].toUpperCase()}${w.substring(1)}').join(' '),
          e.value.toString(),
        )),
        _reviewRow('GPS', _locationData != null
            ? '${_locationData!['latitude']!.toStringAsFixed(5)}, ${_locationData!['longitude']!.toStringAsFixed(5)}'
            : 'N/A'),
        ..._selectedConfig!.photos.map((p) {
          final isCaptured = _capturedImages.containsKey(p.key);
          return _reviewRow(
            p.label,
            isCaptured
                ? '✅ Captured'
                : p.required
                    ? '❌ Missing (Required)'
                    : '⚠️ Not Captured (Optional)',
          );
        }),
        if (_errorMessage != null) ...[
          const SizedBox(height: AppSpacing.md),
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
            ),
            child: Text(_errorMessage!, style: AppTypography.bodySmall.copyWith(color: AppColors.error)),
          ),
        ],
      ],
    );
  }

  Widget _reviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 120, child: Text(label, style: AppTypography.caption.copyWith(fontWeight: FontWeight.w600))),
          Expanded(child: Text(value, style: AppTypography.bodySmall)),
        ],
      ),
    );
  }
}
