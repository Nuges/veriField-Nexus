// =============================================================================
// VeriField Nexus — Smart Installation Form (Dynamic Form Engine)
// =============================================================================
// Progressive step-by-step form:
//   Step 1: Select activity type (icon grid)
//   Step 2: Dynamic fields based on type
//   Step 3: Photo capture + GPS lock
//   Step 4: Review & submit
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

  // Step 1: Type selection
  String? _selectedTypeId;
  ActivityTypeConfig? _selectedConfig;

  // Step 2: Dynamic field values
  final Map<String, dynamic> _fieldValues = {};
  final Map<String, TextEditingController> _textControllers = {};

  // Step 3: Photo + GPS
  File? _capturedImage;
  Map<String, double>? _locationData;
  bool _isCapturingLocation = false;

  // GPS duplicate check
  Map<String, dynamic>? _duplicateCheckResult;
  bool _isCheckingDuplicate = false;
  String? _overrideReason;
  final _overrideController = TextEditingController();

  // Submission
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    for (final c in _textControllers.values) {
      c.dispose();
    }
    _overrideController.dispose();
    super.dispose();
  }

  // =========================================================================
  // Step Navigation
  // =========================================================================

  bool get _canProceed {
    switch (_currentStep) {
      case 0:
        return _selectedTypeId != null;
      case 1:
        return _validateDynamicFields();
      case 2:
        return _capturedImage != null && _locationData != null;
      default:
        return true;
    }
  }

  void _nextStep() {
    if (!_canProceed) return;
    if (_currentStep == 2) {
      // After photo/GPS step, run duplicate check if not done
      if (_duplicateCheckResult == null && _locationData != null) {
        _runDuplicateCheck();
      }
    }
    setState(() => _currentStep++);
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
      final result = await ApiService.post('/activities/check-duplicate', body: {
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

  Future<void> _capturePhoto() async {
    final prompts = [
      'Take a wide-angle shot of the installation',
      'Capture the asset clearly in focus',
      'Ensure background context is visible',
      'Show the installation from a different angle',
    ];
    final prompt = prompts[DateTime.now().millisecond % prompts.length];

    final proceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Row(children: [
          const Icon(Icons.camera_alt_rounded, color: AppColors.primary),
          const SizedBox(width: AppSpacing.sm),
          Text('Photo Required', style: AppTypography.title),
        ]),
        content: Text('$prompt\n\nThis ensures data authenticity.', style: AppTypography.bodySmall),
        actions: [
          TextButton(onPressed: () => ctx.pop(false), child: const Text('Cancel')),
          VFButton(label: 'Open Camera', icon: Icons.camera_alt_rounded, onPressed: () => ctx.pop(true)),
        ],
      ),
    );
    if (proceed != true) return;
    final photo = await CameraService.capturePhoto();
    if (photo != null && mounted) setState(() => _capturedImage = photo);
  }

  // =========================================================================
  // Submission
  // =========================================================================

  Future<void> _submitInstallation() async {
    if (_capturedImage == null || _locationData == null || _selectedTypeId == null) return;

    // Check if duplicate override needs reason
    final isDuplicate = _duplicateCheckResult?['duplicate_flag'] == true;
    if (isDuplicate && (_overrideReason == null || _overrideReason!.isEmpty)) {
      setState(() => _errorMessage = 'Please provide an override reason for the nearby duplicate.');
      return;
    }

    setState(() { _isSubmitting = true; _errorMessage = null; });

    final clientId = _uuid.v4();
    final capturedAt = DateTime.now().toUtc().toIso8601String();
    final imageHash = await CameraService.generateImageHash(_capturedImage!);
    final deviceSignature = await DeviceService.getDeviceSignature();

    final activityData = Map<String, dynamic>.from(_fieldValues);
    activityData['device_signature'] = deviceSignature;

    try {
      final isOnline = await SyncService.isOnline();

      if (isOnline) {
        final imageName = '${clientId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
        final imageUrl = await SyncService.uploadImage(_capturedImage!, imageName);

        await ApiService.post('/activities', body: {
          'activity_type': _selectedTypeId,
          'activity_data': activityData,
          'image_url': imageUrl,
          'image_hash': imageHash,
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
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Installation registered successfully! ✅')),
          );
          context.pop(true);
        }
      } else {
        await LocalDbService.savePendingActivity({
          'id': clientId,
          'client_id': clientId,
          'activity_type': _selectedTypeId,
          'activity_data': jsonEncode(activityData),
          'image_path': _capturedImage!.path,
          'image_hash': imageHash,
          'latitude': _locationData!['latitude'],
          'longitude': _locationData!['longitude'],
          'gps_accuracy': _locationData!['accuracy'],
          'captured_at': capturedAt,
          'created_at': capturedAt,
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Saved offline. Will sync when connected. 📱')),
          );
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

  @override
  Widget build(BuildContext context) {
    final steps = ['Type', 'Details', 'Capture', 'Review'];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Register Installation'),
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

  // --- Step 1: Type Selection ---
  Widget _buildTypeSelection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('What are you registering?', style: AppTypography.heading).animate().fadeIn(),
        const SizedBox(height: AppSpacing.sm),
        Text('Select the installation type', style: AppTypography.bodySmall).animate().fadeIn(delay: 100.ms),
        const SizedBox(height: AppSpacing.xl),
        ...activityTypes.map((type) {
          final isSelected = _selectedTypeId == type.id;
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: GestureDetector(
              onTap: () => setState(() {
                _selectedTypeId = type.id;
                _selectedConfig = type;
                _fieldValues.clear();
                for (final c in _textControllers.values) { c.clear(); }
              }),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.all(AppSpacing.base),
                decoration: BoxDecoration(
                  color: isSelected ? type.color.withValues(alpha: 0.1) : AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                  border: Border.all(color: isSelected ? type.color : AppColors.border, width: isSelected ? 2 : 1),
                ),
                child: Row(children: [
                  Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(
                      color: type.color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(type.icon, color: type.color, size: 24),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(type.label, style: AppTypography.title.copyWith(fontSize: 15)),
                      const SizedBox(height: 2),
                      Text(type.description, style: AppTypography.caption),
                    ],
                  )),
                  if (isSelected) Icon(Icons.check_circle, color: type.color, size: 24),
                ]),
              ),
            ),
          ).animate().fadeIn(delay: Duration(milliseconds: 50 * activityTypes.indexOf(type)));
        }),
      ],
    );
  }

  // --- Step 2: Dynamic Fields ---
  Widget _buildDynamicFields() {
    if (_selectedConfig == null) return const SizedBox();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(_selectedConfig!.icon, color: _selectedConfig!.color, size: 24),
          const SizedBox(width: AppSpacing.sm),
          Text(_selectedConfig!.label, style: AppTypography.heading),
        ]).animate().fadeIn(),
        const SizedBox(height: 4),
        Text(_selectedConfig!.methodology, style: AppTypography.caption.copyWith(color: AppColors.primary)),
        const SizedBox(height: AppSpacing.xl),
        ..._selectedConfig!.fields.asMap().entries.map((entry) {
          final i = entry.key;
          final field = entry.value;
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.base),
            child: _buildField(field).animate().fadeIn(delay: Duration(milliseconds: 80 * i)),
          );
        }),
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

  // --- Step 3: Capture ---
  Widget _buildCaptureStep() {
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
        // Photo
        Text('Photo Proof *', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: AppSpacing.md),
        GestureDetector(
          onTap: _capturePhoto,
          child: Container(
            height: 200, width: double.infinity,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
              border: Border.all(color: _capturedImage != null ? AppColors.primary : AppColors.border, width: _capturedImage != null ? 2 : 1),
            ),
            child: _capturedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(AppSpacing.radiusLg - 1),
                    child: Stack(fit: StackFit.expand, children: [
                      kIsWeb ? Image.network(_capturedImage!.path, fit: BoxFit.cover) : Image.file(_capturedImage!, fit: BoxFit.cover),
                      Positioned(top: 8, right: 8, child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(20)),
                        child: const Icon(Icons.check, color: Colors.white, size: 16),
                      )),
                    ]))
                : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.camera_alt_rounded, size: 48, color: AppColors.textTertiary),
                    const SizedBox(height: AppSpacing.sm),
                    Text('Tap to capture photo', style: AppTypography.bodySmall),
                  ]),
          ),
        ).animate().fadeIn(delay: 200.ms),
      ],
    );
  }

  // --- Step 4: Review ---
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
        _reviewRow('Type', _selectedConfig?.label ?? ''),
        _reviewRow('Environment', _duplicateCheckResult?['environment_type'] ?? 'Detecting...'),
        ..._fieldValues.entries.map((e) => _reviewRow(
          e.key.replaceAll('_', ' ').split(' ').map((w) => '${w[0].toUpperCase()}${w.substring(1)}').join(' '),
          e.value.toString(),
        )),
        _reviewRow('GPS', _locationData != null
            ? '${_locationData!['latitude']!.toStringAsFixed(5)}, ${_locationData!['longitude']!.toStringAsFixed(5)}'
            : 'N/A'),
        _reviewRow('Photo', _capturedImage != null ? '✅ Captured' : '❌ Missing'),
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _captureLocation());
  }
}
