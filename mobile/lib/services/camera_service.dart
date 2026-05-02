// =============================================================================
// VeriField Nexus — Camera Service
// =============================================================================
// Image capture using device camera with compression.
// Supports photo capture for activity proof documentation.
// =============================================================================

import 'dart:io';
import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Service for capturing and processing images.
class CameraService {
  static final ImagePicker _picker = ImagePicker();

  /// Capture a photo using the device camera.
  /// Returns the captured image file, or null if cancelled.
  static Future<File?> capturePhoto() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,       // Limit resolution for upload efficiency
        maxHeight: 1080,
        imageQuality: 85,     // Good quality with reasonable file size
        preferredCameraDevice: CameraDevice.rear,
      );

      if (photo == null) return null;
      return File(photo.path);
    } catch (e) {
      return null;
    }
  }

  /// Pick an image from the device gallery (fallback option).
  static Future<File?> pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );

      if (image == null) return null;
      return File(image.path);
    } catch (e) {
      return null;
    }
  }

  /// Generate a SHA256 hash of an image file for duplicate detection.
  /// This is computed on-device and sent with the activity submission.
  static Future<String> generateImageHash(File imageFile) async {
    final Uint8List bytes = kIsWeb 
        ? (await http.get(Uri.parse(imageFile.path))).bodyBytes 
        : await imageFile.readAsBytes();
    final digest = sha256.convert(bytes);
    return digest.toString().substring(0, 16); // Use first 16 chars
  }
}
