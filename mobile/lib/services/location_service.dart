// =============================================================================
// VeriField Nexus — Location Service
// =============================================================================
// GPS capture with accuracy checking and permission handling.
// Uses Geolocator package for cross-platform location access.
// =============================================================================

import 'package:geolocator/geolocator.dart';

/// Service for GPS location capture and permission management.
class LocationService {
  /// Check and request location permissions.
  /// Returns true if permissions are granted.
  static Future<bool> checkPermissions() async {
    // Check if location services are enabled
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    // Check permission status
    LocationPermission permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      // Request permission
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return false;
    }

    if (permission == LocationPermission.deniedForever) {
      // Permissions permanently denied — can't request again
      return false;
    }

    return true;
  }

  /// Get the current GPS position with high accuracy.
  /// Returns null if location is unavailable.
  static Future<Position?> getCurrentPosition() async {
    final hasPermission = await checkPermissions();
    if (!hasPermission) return null;

    try {
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 0,
        ),
      );
    } catch (e) {
      return null;
    }
  }

  /// Get a simplified location map for API submission.
  static Future<Map<String, double>?> getLocationData() async {
    final position = await getCurrentPosition();
    if (position == null) return null;

    return {
      'latitude': position.latitude,
      'longitude': position.longitude,
      'accuracy': position.accuracy,
    };
  }
}
