// =============================================================================
// VeriField Nexus — Camera Service
// =============================================================================
// Image capture using device camera with compression.
// Supports photo capture for activity proof documentation.
//
// PWA note: XFile on web holds a blob URL which CANNOT be loaded via
// http.get or Image.network. Instead:
//   - Use [XFile.readAsBytes()] for hashing or sending to server.
//   - Use [CameraService.getImageBytes(xfile)] for Image.memory display.
// =============================================================================

import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';
import 'package:crypto/crypto.dart';

/// Service for capturing and processing images.
class CameraService {
  static final ImagePicker _picker = ImagePicker();

  /// Capture a photo using the device camera.
  /// Returns the captured [XFile], or null if cancelled.
  /// On web, use [getImageBytes] or [XFile.readAsBytes()] —
  /// do NOT call File(xfile.path) on web.
  static Future<XFile?> capturePhoto() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,       // Limit resolution for upload efficiency
        maxHeight: 1080,
        imageQuality: 85,     // Good quality with reasonable file size
        preferredCameraDevice: CameraDevice.rear,
      );
      return photo;
    } catch (e) {
      return null;
    }
  }

  /// Pick an image from the device gallery (fallback option).
  static Future<XFile?> pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );
      return image;
    } catch (e) {
      return null;
    }
  }

  /// Read an [XFile] into bytes. Works correctly on both web (blob URLs)
  /// and native platforms. Use this for image display (Image.memory) and
  /// for building the multipart upload body.
  static Future<Uint8List?> getImageBytes(XFile xfile) async {
    try {
      return await xfile.readAsBytes();
    } catch (_) {
      return null;
    }
  }

  /// Generate a SHA256 hash of an image file for duplicate detection.
  /// This is computed on-device and sent with the activity submission.
  /// Uses [XFile.readAsBytes()] to support web blob URLs correctly.
  static Future<String> generateImageHash(XFile xfile) async {
    final bytes = await xfile.readAsBytes();
    final digest = sha256.convert(bytes);
    return digest.toString().substring(0, 16); // Use first 16 chars
  }
}
