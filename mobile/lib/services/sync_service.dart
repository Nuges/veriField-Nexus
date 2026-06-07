// =============================================================================
// VeriField Nexus — Sync Service
// =============================================================================
// Offline-first sync engine that manages data synchronization:
// 1. Save activities locally when offline
// 2. Queue for sync when connectivity is restored
// 3. Batch upload pending activities to the server
// 4. Handle conflicts and deduplication via client_id
// =============================================================================

import 'dart:io';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../core/config/supabase_config.dart';
import 'local_db_service.dart';
import 'api_service.dart';
import 'dart:convert';

/// Manages offline-first data synchronization.
class SyncService {
  /// Check if the device has internet connectivity.
  static Future<bool> isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return !result.contains(ConnectivityResult.none);
  }

  /// Upload a captured image to Supabase Storage.
  /// Returns the public URL of the uploaded image.
  static Future<String?> uploadImage(File imageFile, String fileName) async {
    try {
      final bytes = kIsWeb 
          ? (await http.get(Uri.parse(imageFile.path))).bodyBytes 
          : await imageFile.readAsBytes();
      await SupabaseConfig.client.storage
          .from('activity-photos')
          .uploadBinary(fileName, bytes);

      // Get public URL for the uploaded image
      final publicUrl = SupabaseConfig.client.storage
          .from('activity-photos')
          .getPublicUrl(fileName);

      return publicUrl;
    } catch (e) {
      return null;
    }
  }

  /// Sync all pending activities to the server.
  /// Called when connectivity is restored or manually triggered.
  static Future<SyncResult> syncPendingActivities() async {
    if (!await isOnline()) {
      return SyncResult(synced: 0, failed: 0, message: 'No internet connection');
    }

    final pending = await LocalDbService.getPendingActivities();
    if (pending.isEmpty) {
      return SyncResult(synced: 0, failed: 0, message: 'Nothing to sync');
    }

    int synced = 0;
    int failed = 0;

    // Build batch payload
    final activitiesBatch = <Map<String, dynamic>>[];

    for (final activity in pending) {
      try {
        Map<String, dynamic> actData = {};
        if (activity['activity_data'] is Map) {
          actData = Map<String, dynamic>.from(activity['activity_data'] as Map);
        } else if (activity['activity_data'] is String) {
          try {
            actData = jsonDecode(activity['activity_data'] as String) as Map<String, dynamic>;
          } catch (_) {}
        }

        // Upload primary image if present
        String? primaryUrl;
        if (activity['image_path'] != null) {
          final file = File(activity['image_path']);
          if (await file.exists()) {
            final fileName = '${activity['client_id']}_primary.jpg';
            primaryUrl = await uploadImage(file, fileName);
            if (primaryUrl == null) {
              throw Exception('Primary image upload failed');
            }
          }
        }

        // Scan activity_data for additional local image paths to upload
        final keysToUpload = actData.keys.where((k) => k.endsWith('_image_path')).toList();
        final Map<String, String> uploadedUrls = {};

        for (final key in keysToUpload) {
          final localPath = actData[key] as String?;
          if (localPath != null && localPath.isNotEmpty) {
            final file = File(localPath);
            if (await file.exists()) {
              final cleanKey = key.replaceAll('_image_path', '');
              final fileName = '${activity['client_id']}_$cleanKey.jpg';
              final url = await uploadImage(file, fileName);
              if (url == null) {
                throw Exception('Additional image $cleanKey upload failed');
              }
              uploadedUrls['${cleanKey}_image_url'] = url;
            }
          }
        }

        // Clean up paths and merge URL keys
        for (final key in keysToUpload) {
          actData.remove(key);
        }
        actData.addAll(uploadedUrls);

        // Map primary key URL in activity_data too (e.g. solar_installation_image_url)
        final primaryKey = activity['activity_type'] == 'HYBRID_ENERGY' ? 'solar_installation' : 'stove_installation';
        if (primaryUrl != null) {
          actData['${primaryKey}_image_url'] = primaryUrl;
        }

        activitiesBatch.add({
          'activity_type': activity['activity_type'],
          'activity_data': actData,
          'description': activity['description'],
          'image_url': primaryUrl,
          'image_hash': activity['image_hash'],
          'latitude': activity['latitude'],
          'longitude': activity['longitude'],
          'gps_accuracy': activity['gps_accuracy'],
          'captured_at': activity['captured_at'],
          'property_id': activity['property_id'],
          'client_id': activity['client_id'],
        });
      } catch (e) {
        failed++;
      }
    }

    // Send batch request
    if (activitiesBatch.isNotEmpty) {
      try {
        final response = await ApiService.post(
          '/activities/batch',
          body: {'activities': activitiesBatch},
        );

        // Mark successful activities as synced
        final results = response['results'] as List? ?? [];
        for (final result in results) {
          if (result['status'] == 'submitted' || result['status'] == 'duplicate') {
            await LocalDbService.markAsSynced(result['client_id']);
            synced++;
          } else {
            failed++;
          }
        }
      } catch (e) {
        failed += activitiesBatch.length;
      }
    }

    return SyncResult(
      synced: synced,
      failed: failed,
      message: synced > 0 ? '$synced activities synced' : 'Sync failed',
    );
  }

  /// Listen for connectivity changes and auto-sync.
  static void startAutoSync() {
    Connectivity().onConnectivityChanged.listen((result) async {
      if (!result.contains(ConnectivityResult.none)) {
        // Device came online — sync pending data
        await syncPendingActivities();
      }
    });
  }
}

/// Result of a sync operation.
class SyncResult {
  final int synced;
  final int failed;
  final String message;

  SyncResult({required this.synced, required this.failed, required this.message});
}
