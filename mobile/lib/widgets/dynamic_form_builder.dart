// =============================================================================
// VeriField Nexus — Dynamic Form Builder
// =============================================================================
// Renders forms dynamically from JSON schemas provided by CIOS sector plugins.
// Supports: text, number, boolean (switch), dropdown (enum), date,
//           image_capture fields with validation and evidence capture.
//
// Usage:
//   DynamicFormBuilder(
//     schema: sectorSchema,            // JSON schema from backend plugin
//     onSubmit: (data) => handleData(data),
//     submitLabel: 'Save Activity',
//   )
//
// JSON schema format (from GET /api/v1/registry/plugins):
//   {
//     "type": "object",
//     "required": ["field_name"],
//     "properties": {
//       "field_name": {
//         "type": "string",
//         "title": "Display Label",
//         "description": "Helper text",
//         "enum": ["option1", "option2"],
//         "minimum": 0,
//         "maximum": 100,
//         "pattern": "^[A-Z].*"
//       }
//     }
//   }
// =============================================================================

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_typography.dart';
import '../core/constants/app_spacing.dart';

// =============================================================================
// DynamicFormFieldType — Supported field types
// =============================================================================

/// The set of field types renderable by the dynamic form builder.
enum DynamicFormFieldType {
  text,
  number,
  boolean,
  dropdown,
  date,
  imageCapture,
}

// =============================================================================
// DynamicFormField — Single field definition parsed from JSON schema
// =============================================================================

/// Represents a single field definition extracted from a JSON schema property.
class DynamicFormField {
  /// The property key in the schema (used as the key in the returned data map).
  final String key;

  /// Human-readable label shown above the field.
  final String title;

  /// Optional helper / description text shown below the field.
  final String? description;

  /// The resolved field type to render.
  final DynamicFormFieldType type;

  /// Whether this field is required (appears in the schema's `required` array).
  final bool isRequired;

  /// For `dropdown` type — the list of allowed enum values.
  final List<String>? enumValues;

  /// For `number` type — minimum allowed value.
  final num? minimum;

  /// For `number` type — maximum allowed value.
  final num? maximum;

  /// For `text` type — regex pattern the value must match.
  final String? pattern;

  /// Optional default value from the schema.
  final dynamic defaultValue;

  const DynamicFormField({
    required this.key,
    required this.title,
    required this.type,
    this.description,
    this.isRequired = false,
    this.enumValues,
    this.minimum,
    this.maximum,
    this.pattern,
    this.defaultValue,
  });

  /// Parse a list of [DynamicFormField]s from a JSON schema map.
  ///
  /// The schema must be a standard JSON Schema object with `type`, `required`,
  /// and `properties` at the top level.
  static List<DynamicFormField> fromSchema(Map<String, dynamic> schema) {
    final properties =
        (schema['properties'] as Map<String, dynamic>?) ?? {};
    final requiredFields =
        (schema['required'] as List?)?.cast<String>() ?? [];

    return properties.entries.map((entry) {
      final key = entry.key;
      final prop = entry.value as Map<String, dynamic>;

      final type = _resolveFieldType(prop);
      final title =
          (prop['title'] as String?) ?? _humanizeKey(key);

      return DynamicFormField(
        key: key,
        title: title,
        description: prop['description'] as String?,
        type: type,
        isRequired: requiredFields.contains(key),
        enumValues: (prop['enum'] as List?)?.cast<String>(),
        minimum: prop['minimum'] as num?,
        maximum: prop['maximum'] as num?,
        pattern: prop['pattern'] as String?,
        defaultValue: prop['default'],
      );
    }).toList();
  }

  /// Determine the [DynamicFormFieldType] from a JSON schema property map.
  static DynamicFormFieldType _resolveFieldType(Map<String, dynamic> prop) {
    final schemaType = prop['type'] as String? ?? 'string';
    final format = prop['format'] as String?;

    // Explicit image_capture format or keys containing 'image'/'photo'/'evidence'
    if (format == 'image_capture' || format == 'image' || format == 'photo') {
      return DynamicFormFieldType.imageCapture;
    }

    // Date format
    if (format == 'date' || format == 'date-time') {
      return DynamicFormFieldType.date;
    }

    // Enum list → dropdown
    if (prop.containsKey('enum')) {
      return DynamicFormFieldType.dropdown;
    }

    // Boolean
    if (schemaType == 'boolean') {
      return DynamicFormFieldType.boolean;
    }

    // Number / integer
    if (schemaType == 'number' || schemaType == 'integer') {
      return DynamicFormFieldType.number;
    }

    // Default to text
    return DynamicFormFieldType.text;
  }

  /// Convert a snake_case or camelCase key to a human-readable title.
  static String _humanizeKey(String key) {
    return key
        .replaceAllMapped(RegExp(r'([a-z])([A-Z])'),
            (m) => '${m[1]} ${m[2]}')
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isEmpty
            ? w
            : '${w[0].toUpperCase()}${w.substring(1).toLowerCase()}')
        .join(' ');
  }
}

// =============================================================================
// DynamicFormBuilder — Stateful widget that renders & validates the form
// =============================================================================

/// A schema-driven form builder that renders fields from a JSON schema and
/// returns the completed data as a `Map<String, dynamic>` via [onSubmit].
///
/// ```dart
/// DynamicFormBuilder(
///   schema: pluginSchema['form_config'],
///   onSubmit: (data) => saveActivity(data),
///   submitLabel: 'Submit',
/// )
/// ```
class DynamicFormBuilder extends StatefulWidget {
  /// The JSON schema object describing the form structure.
  final Map<String, dynamic> schema;

  /// Callback invoked when the form passes validation and the user taps submit.
  final void Function(Map<String, dynamic> formData) onSubmit;

  /// Label for the submit button.
  final String submitLabel;

  /// Whether the submit button should show a loading indicator.
  final bool isLoading;

  /// Optional pre-filled values (e.g. when editing an existing record).
  final Map<String, dynamic>? initialValues;

  /// Optional callback when the form data changes (for auto-save scenarios).
  final void Function(Map<String, dynamic> formData)? onChanged;

  /// Whether the form fields should be read-only (view mode).
  final bool readOnly;

  const DynamicFormBuilder({
    super.key,
    required this.schema,
    required this.onSubmit,
    this.submitLabel = 'Submit',
    this.isLoading = false,
    this.initialValues,
    this.onChanged,
    this.readOnly = false,
  });

  @override
  State<DynamicFormBuilder> createState() => _DynamicFormBuilderState();
}

class _DynamicFormBuilderState extends State<DynamicFormBuilder> {
  final _formKey = GlobalKey<FormState>();
  late List<DynamicFormField> _fields;

  /// Stores the current value for each field, keyed by field key.
  final Map<String, dynamic> _formData = {};

  /// Text editing controllers for text/number fields.
  final Map<String, TextEditingController> _controllers = {};

  /// Image picker instance.
  final ImagePicker _imagePicker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _fields = DynamicFormField.fromSchema(widget.schema);
    _initializeFormData();
  }

  @override
  void didUpdateWidget(covariant DynamicFormBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Re-parse fields if the schema reference changed.
    if (oldWidget.schema != widget.schema) {
      _disposeControllers();
      _fields = DynamicFormField.fromSchema(widget.schema);
      _formData.clear();
      _initializeFormData();
    }
  }

  /// Seed [_formData] with defaults and initial values, and create controllers.
  void _initializeFormData() {
    for (final field in _fields) {
      // Priority: initialValues > default > type-appropriate empty
      dynamic value;
      if (widget.initialValues != null &&
          widget.initialValues!.containsKey(field.key)) {
        value = widget.initialValues![field.key];
      } else if (field.defaultValue != null) {
        value = field.defaultValue;
      } else {
        value = _defaultForType(field.type);
      }
      _formData[field.key] = value;

      // Create controllers for text/number fields
      if (field.type == DynamicFormFieldType.text ||
          field.type == DynamicFormFieldType.number) {
        final controller =
            TextEditingController(text: value?.toString() ?? '');
        _controllers[field.key] = controller;
      }
    }
  }

  dynamic _defaultForType(DynamicFormFieldType type) {
    switch (type) {
      case DynamicFormFieldType.boolean:
        return false;
      case DynamicFormFieldType.number:
        return null;
      case DynamicFormFieldType.date:
        return null;
      case DynamicFormFieldType.imageCapture:
        return null;
      default:
        return null;
    }
  }

  void _disposeControllers() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    _controllers.clear();
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  /// Notify parent of data changes (for auto-save).
  void _notifyChanged() {
    widget.onChanged?.call(Map<String, dynamic>.from(_formData));
  }

  // =========================================================================
  // Form Submission
  // =========================================================================

  void _handleSubmit() {
    if (_formKey.currentState?.validate() ?? false) {
      _formKey.currentState!.save();

      // Build the clean output map
      final output = <String, dynamic>{};
      for (final field in _fields) {
        final value = _formData[field.key];
        // Include the value if it's non-null (or if the field is required).
        if (value != null || field.isRequired) {
          output[field.key] = value;
        }
      }

      widget.onSubmit(output);
    }
  }

  // =========================================================================
  // Build
  // =========================================================================

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.base,
          vertical: AppSpacing.lg,
        ),
        itemCount: _fields.length + 1, // +1 for the submit button
        separatorBuilder: (_, __) =>
            const SizedBox(height: AppSpacing.lg),
        itemBuilder: (context, index) {
          if (index == _fields.length) {
            return _buildSubmitButton();
          }
          return _buildField(_fields[index]);
        },
      ),
    );
  }

  // =========================================================================
  // Field Router
  // =========================================================================

  Widget _buildField(DynamicFormField field) {
    switch (field.type) {
      case DynamicFormFieldType.text:
        return _buildTextField(field);
      case DynamicFormFieldType.number:
        return _buildNumberField(field);
      case DynamicFormFieldType.boolean:
        return _buildBooleanField(field);
      case DynamicFormFieldType.dropdown:
        return _buildDropdownField(field);
      case DynamicFormFieldType.date:
        return _buildDateField(field);
      case DynamicFormFieldType.imageCapture:
        return _buildImageCaptureField(field);
    }
  }

  // =========================================================================
  // Text Field
  // =========================================================================

  Widget _buildTextField(DynamicFormField field) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(field),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          controller: _controllers[field.key],
          readOnly: widget.readOnly,
          style: AppTypography.body,
          decoration: _inputDecoration(field),
          onChanged: (value) {
            _formData[field.key] = value;
            _notifyChanged();
          },
          validator: (value) => _validateField(field, value),
        ),
      ],
    );
  }

  // =========================================================================
  // Number Field
  // =========================================================================

  Widget _buildNumberField(DynamicFormField field) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(field),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          controller: _controllers[field.key],
          readOnly: widget.readOnly,
          style: AppTypography.body,
          keyboardType: const TextInputType.numberWithOptions(
            decimal: true,
            signed: true,
          ),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[\d.\-]')),
          ],
          decoration: _inputDecoration(field),
          onChanged: (value) {
            _formData[field.key] = num.tryParse(value);
            _notifyChanged();
          },
          validator: (value) => _validateNumberField(field, value),
        ),
      ],
    );
  }

  // =========================================================================
  // Boolean (Switch) Field
  // =========================================================================

  Widget _buildBooleanField(DynamicFormField field) {
    final currentValue = _formData[field.key] as bool? ?? false;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.base),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _fieldLabel(field),
                if (field.description != null)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.xs),
                    child: Text(field.description!,
                        style: AppTypography.caption),
                  ),
              ],
            ),
          ),
          Switch.adaptive(
            value: currentValue,
            onChanged: widget.readOnly
                ? null
                : (value) {
                    setState(() => _formData[field.key] = value);
                    _notifyChanged();
                  },
            activeColor: AppColors.primary,
          ),
        ],
      ),
    );
  }

  // =========================================================================
  // Dropdown (Enum) Field
  // =========================================================================

  Widget _buildDropdownField(DynamicFormField field) {
    final currentValue = _formData[field.key] as String?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(field),
        const SizedBox(height: AppSpacing.sm),
        DropdownButtonFormField<String>(
          value: field.enumValues?.contains(currentValue) == true
              ? currentValue
              : null,
          isExpanded: true,
          dropdownColor: AppColors.surfaceLight,
          style: AppTypography.body,
          decoration: _inputDecoration(field),
          items: (field.enumValues ?? []).map((option) {
            return DropdownMenuItem<String>(
              value: option,
              child: Text(
                DynamicFormField._humanizeKey(option),
                style: AppTypography.body,
              ),
            );
          }).toList(),
          onChanged: widget.readOnly
              ? null
              : (value) {
                  setState(() => _formData[field.key] = value);
                  _notifyChanged();
                },
          validator: (value) {
            if (field.isRequired && (value == null || value.isEmpty)) {
              return '${field.title} is required';
            }
            return null;
          },
        ),
      ],
    );
  }

  // =========================================================================
  // Date Field
  // =========================================================================

  Widget _buildDateField(DynamicFormField field) {
    final currentValue = _formData[field.key] as String?;
    final displayText = currentValue != null
        ? _formatDateDisplay(currentValue)
        : 'Select date';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(field),
        const SizedBox(height: AppSpacing.sm),
        FormField<String>(
          initialValue: currentValue,
          validator: (value) {
            if (field.isRequired && (value == null || value.isEmpty)) {
              return '${field.title} is required';
            }
            return null;
          },
          builder: (state) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InkWell(
                  onTap: widget.readOnly
                      ? null
                      : () => _pickDate(field, state),
                  borderRadius:
                      BorderRadius.circular(AppSpacing.radiusMd),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.base,
                      vertical: AppSpacing.md + 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceLight,
                      borderRadius:
                          BorderRadius.circular(AppSpacing.radiusMd),
                      border: Border.all(
                        color: state.hasError
                            ? AppColors.error
                            : AppColors.border,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.calendar_today_rounded,
                            size: 18, color: AppColors.textSecondary),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: Text(
                            displayText,
                            style: currentValue != null
                                ? AppTypography.body
                                : AppTypography.bodySmall,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                if (state.hasError)
                  Padding(
                    padding: const EdgeInsets.only(
                        top: AppSpacing.xs, left: AppSpacing.sm),
                    child: Text(
                      state.errorText!,
                      style: AppTypography.caption
                          .copyWith(color: AppColors.error),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  Future<void> _pickDate(
      DynamicFormField field, FormFieldState<String> state) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: DateTime(2020),
      lastDate: now.add(const Duration(days: 365)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: AppColors.primary,
              onPrimary: AppColors.textInverse,
              surface: AppColors.surfaceLight,
              onSurface: AppColors.textPrimary,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      final isoString = picked.toIso8601String();
      setState(() => _formData[field.key] = isoString);
      state.didChange(isoString);
      _notifyChanged();
    }
  }

  String _formatDateDisplay(String isoString) {
    try {
      final date = DateTime.parse(isoString);
      return DateFormat('dd MMM yyyy').format(date);
    } catch (_) {
      return isoString;
    }
  }

  // =========================================================================
  // Image Capture Field
  // =========================================================================

  Widget _buildImageCaptureField(DynamicFormField field) {
    final currentPath = _formData[field.key] as String?;
    final hasImage = currentPath != null && currentPath.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(field),
        if (field.description != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child:
                Text(field.description!, style: AppTypography.caption),
          ),
        const SizedBox(height: AppSpacing.sm),
        FormField<String>(
          initialValue: currentPath,
          validator: (value) {
            if (field.isRequired &&
                (value == null || value.isEmpty)) {
              return '${field.title} photo is required';
            }
            return null;
          },
          builder: (state) {
            return Column(
              children: [
                InkWell(
                  onTap: widget.readOnly
                      ? null
                      : () => _captureImage(field, state),
                  borderRadius:
                      BorderRadius.circular(AppSpacing.radiusMd),
                  child: Container(
                    width: double.infinity,
                    height: hasImage ? 200 : 120,
                    decoration: BoxDecoration(
                      color: AppColors.surfaceLight,
                      borderRadius:
                          BorderRadius.circular(AppSpacing.radiusMd),
                      border: Border.all(
                        color: state.hasError
                            ? AppColors.error
                            : AppColors.border,
                        width: state.hasError ? 1.5 : 1,
                      ),
                    ),
                    child: hasImage
                        ? _buildImagePreview(currentPath)
                        : _buildImagePlaceholder(),
                  ),
                ),
                if (hasImage && !widget.readOnly)
                  Padding(
                    padding:
                        const EdgeInsets.only(top: AppSpacing.sm),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton.icon(
                          onPressed: () => _captureImage(field, state),
                          icon: const Icon(Icons.refresh_rounded,
                              size: 16),
                          label: Text('Retake',
                              style: AppTypography.caption.copyWith(
                                  color: AppColors.primary)),
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.primary,
                          ),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        TextButton.icon(
                          onPressed: () {
                            setState(
                                () => _formData[field.key] = null);
                            state.didChange(null);
                            _notifyChanged();
                          },
                          icon: const Icon(Icons.delete_outline_rounded,
                              size: 16),
                          label: Text('Remove',
                              style: AppTypography.caption.copyWith(
                                  color: AppColors.error)),
                          style: TextButton.styleFrom(
                            foregroundColor: AppColors.error,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (state.hasError)
                  Padding(
                    padding: const EdgeInsets.only(
                        top: AppSpacing.xs, left: AppSpacing.sm),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        state.errorText!,
                        style: AppTypography.caption
                            .copyWith(color: AppColors.error),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildImagePlaceholder() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.camera_alt_rounded,
            size: 36, color: AppColors.textTertiary),
        const SizedBox(height: AppSpacing.sm),
        Text('Tap to capture photo', style: AppTypography.bodySmall),
      ],
    );
  }

  Widget _buildImagePreview(String path) {
    if (kIsWeb) {
      // On web, the path may be a blob URL or data URL.
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        child: Image.network(
          path,
          fit: BoxFit.cover,
          width: double.infinity,
          errorBuilder: (_, __, ___) => _buildImagePlaceholder(),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
      child: Image.file(
        File(path),
        fit: BoxFit.cover,
        width: double.infinity,
        errorBuilder: (_, __, ___) => _buildImagePlaceholder(),
      ),
    );
  }

  Future<void> _captureImage(
      DynamicFormField field, FormFieldState<String> state) async {
    try {
      final source = await _showImageSourceDialog();
      if (source == null) return;

      final picked = await _imagePicker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );

      if (picked != null) {
        final path = kIsWeb ? picked.path : picked.path;
        setState(() => _formData[field.key] = path);
        state.didChange(path);
        _notifyChanged();
      }
    } catch (e) {
      debugPrint('[DynamicFormBuilder] Image capture failed: $e');
    }
  }

  Future<ImageSource?> _showImageSourceDialog() async {
    return showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: AppColors.surfaceLight,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppSpacing.radiusLg)),
      ),
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.base),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Select Image Source', style: AppTypography.title),
                const SizedBox(height: AppSpacing.lg),
                ListTile(
                  leading: const Icon(Icons.camera_alt_rounded,
                      color: AppColors.primary),
                  title: Text('Camera', style: AppTypography.body),
                  onTap: () =>
                      Navigator.pop(context, ImageSource.camera),
                ),
                ListTile(
                  leading: const Icon(Icons.photo_library_rounded,
                      color: AppColors.accent),
                  title: Text('Gallery', style: AppTypography.body),
                  onTap: () =>
                      Navigator.pop(context, ImageSource.gallery),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // =========================================================================
  // Validation
  // =========================================================================

  String? _validateField(DynamicFormField field, String? value) {
    if (field.isRequired && (value == null || value.trim().isEmpty)) {
      return '${field.title} is required';
    }

    // Pattern validation
    if (field.pattern != null &&
        value != null &&
        value.isNotEmpty) {
      final regex = RegExp(field.pattern!);
      if (!regex.hasMatch(value)) {
        return '${field.title} does not match the required format';
      }
    }

    return null;
  }

  String? _validateNumberField(DynamicFormField field, String? value) {
    if (field.isRequired && (value == null || value.trim().isEmpty)) {
      return '${field.title} is required';
    }

    if (value != null && value.isNotEmpty) {
      final number = num.tryParse(value);
      if (number == null) {
        return 'Please enter a valid number';
      }

      if (field.minimum != null && number < field.minimum!) {
        return '${field.title} must be at least ${field.minimum}';
      }

      if (field.maximum != null && number > field.maximum!) {
        return '${field.title} must be at most ${field.maximum}';
      }
    }

    return null;
  }

  // =========================================================================
  // Shared UI Helpers
  // =========================================================================

  /// Build the field label with an optional required indicator.
  Widget _fieldLabel(DynamicFormField field) {
    return RichText(
      text: TextSpan(
        text: field.title,
        style: AppTypography.bodySmall.copyWith(
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        children: [
          if (field.isRequired)
            TextSpan(
              text: ' *',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.error,
                fontWeight: FontWeight.w700,
              ),
            ),
        ],
      ),
    );
  }

  /// Shared [InputDecoration] for text-based fields.
  InputDecoration _inputDecoration(DynamicFormField field) {
    return InputDecoration(
      hintText: field.description ?? 'Enter ${field.title.toLowerCase()}',
      hintStyle: AppTypography.bodySmall
          .copyWith(color: AppColors.textTertiary),
      filled: true,
      fillColor: AppColors.surfaceLight,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.base,
        vertical: AppSpacing.md,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(
            color: AppColors.borderFocus, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide: const BorderSide(color: AppColors.error),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        borderSide:
            const BorderSide(color: AppColors.error, width: 1.5),
      ),
    );
  }

  // =========================================================================
  // Submit Button
  // =========================================================================

  Widget _buildSubmitButton() {
    if (widget.readOnly) return const SizedBox.shrink();

    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: widget.isLoading ? null : _handleSubmit,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.textInverse,
          padding:
              const EdgeInsets.symmetric(vertical: AppSpacing.base),
          shape: RoundedRectangleBorder(
            borderRadius:
                BorderRadius.circular(AppSpacing.radiusMd),
          ),
          elevation: 0,
        ),
        child: widget.isLoading
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.textInverse,
                ),
              )
            : Text(
                widget.submitLabel,
                style: AppTypography.button.copyWith(
                  color: AppColors.textInverse,
                ),
              ),
      ),
    );
  }
}
