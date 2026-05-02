import 'dart:io';
import 'package:flutter/foundation.dart';

class DeviceService {
  /// Captures basic device fingerprinting data for fraud detection.
  static Future<Map<String, String>> getDeviceSignature() async {
    if (kIsWeb) {
      return {
        'os': 'web',
        'os_version': 'unknown',
        'device_id': 'web-browser',
        'app_version': '1.0.0',
      };
    }
    
    try {
      return {
        'os': Platform.operatingSystem,
        'os_version': Platform.operatingSystemVersion,
        'device_id': Platform.localHostname,
        'app_version': '1.0.0',
      };
    } catch (e) {
      return {
        'os': 'unknown',
        'os_version': 'unknown',
        'device_id': 'unknown',
        'app_version': '1.0.0',
      };
    }
  }
}
