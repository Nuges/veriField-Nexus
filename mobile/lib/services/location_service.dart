// =============================================================================
// VeriField Nexus — Location Service
// =============================================================================
// GPS capture with accuracy checking and permission handling.
// Uses Geolocator package for cross-platform location access.
// PWA note: geolocation only works over HTTPS or localhost. The browser
// must grant permission; if denied, a descriptive error is returned via
// [LocationResult.errorReason] so the UI can guide the user.
// =============================================================================

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

/// Result wrapper that pairs optional location data with an optional error reason.
class LocationResult {
  final Map<String, double>? data;
  final String? errorReason;
  bool get success => data != null;
  const LocationResult({this.data, this.errorReason});
}

/// Service for GPS location capture and permission management.
class LocationService {
  /// Timeout for a single GPS fix attempt.
  static const Duration _timeout = Duration(seconds: 15);

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
      ).timeout(_timeout);
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

  /// Full location fetch that returns a [LocationResult] with a descriptive
  /// [errorReason] so the caller can surface helpful guidance to the user.
  static Future<LocationResult> getLocationResult() async {
    // 1. Check service enabled (device GPS or network location)
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return const LocationResult(
        errorReason: 'Location services are disabled on this device. Please enable GPS.',
      );
    }

    // 2. Check/request permission
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      return LocationResult(
        errorReason: kIsWeb
            ? 'Browser denied location access. Tap the 🔒 icon in the address bar and allow "Location", then tap 🔄 to retry.'
            : 'Location permission denied. Please allow location access in your device settings.',
      );
    }
    if (permission == LocationPermission.deniedForever) {
      return const LocationResult(
        errorReason: 'Location permission is permanently blocked. Open device settings and enable location for this app.',
      );
    }

    // 3. Acquire position with timeout
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 0,
        ),
      ).timeout(_timeout);

      return LocationResult(
        data: {
          'latitude': position.latitude,
          'longitude': position.longitude,
          'accuracy': position.accuracy,
        },
      );
    } catch (e) {
      // Fallback: Try to get last known position
      try {
        final lastKnown = await Geolocator.getLastKnownPosition();
        if (lastKnown != null) {
          return LocationResult(
            data: {
              'latitude': lastKnown.latitude,
              'longitude': lastKnown.longitude,
              'accuracy': lastKnown.accuracy,
            },
          );
        }
      } catch (_) {}

      final msg = e.toString().toLowerCase();
      if (msg.contains('timeout') || msg.contains('timed out')) {
        return const LocationResult(
          errorReason: 'GPS timed out — tap 🔄 to retry. Make sure you are outdoors or near a window.',
        );
      }
      return LocationResult(
        errorReason: kIsWeb
            ? 'Could not get location. Ensure this page is served over HTTPS and location is allowed in your browser.'
            : 'Could not get GPS fix. Tap 🔄 to retry.',
      );
    }
  }
}
