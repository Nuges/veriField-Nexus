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
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
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
  /// Accepts [XFile] so that web blob URLs are handled correctly
  /// via [XFile.readAsBytes()] instead of dart:io File operations.
  /// Returns the public URL of the uploaded image.
  static Future<String?> uploadImage(XFile imageFile, String fileName) async {
    try {
      // XFile.readAsBytes() works on both web (blob URL) and native.
      final bytes = await imageFile.readAsBytes();
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

  /// Upload from a native [File] path (used during offline sync on non-web).
  static Future<String?> uploadImageFromPath(String filePath, String fileName) async {
    try {
      final file = File(filePath);
      if (!await file.exists()) return null;
      final bytes = await file.readAsBytes();
      await SupabaseConfig.client.storage
          .from('activity-photos')
          .uploadBinary(fileName, bytes);
      final publicUrl = SupabaseConfig.client.storage
          .from('activity-photos')
          .getPublicUrl(fileName);
      return publicUrl;
    } catch (e) {
      return null;
    }
  }

  /// Sync pending activities to the server.
  /// Called when connectivity is restored or manually triggered.
  static Future<SyncResult> syncPendingActivities({bool failedOnly = false, bool forceAll = false}) async {
    if (!await isOnline()) {
      return SyncResult(synced: 0, failed: 0, message: 'No internet connection');
    }

    final List<Map<String, dynamic>> pending;
    if (failedOnly) {
      pending = await LocalDbService.getFailedActivities();
    } else if (forceAll) {
      pending = await LocalDbService.getPendingActivities();
    } else {
      pending = await LocalDbService.getRetryableActivities();
    }

    if (pending.isEmpty) {
      return SyncResult(synced: 0, failed: 0, message: 'Nothing to sync');
    }

    int synced = 0;
    int failed = 0;

    // Build batch payload
    final activitiesBatch = <Map<String, dynamic>>[];

    for (final activity in pending) {
      final clientId = activity['client_id']?.toString() ?? '';
      if (clientId.isEmpty) continue;

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
          final fileName = '${activity['client_id']}_primary.jpg';
          primaryUrl = await uploadImageFromPath(activity['image_path'], fileName);
          if (primaryUrl == null) {
            throw Exception('Primary image upload failed');
          }
        }

        // Scan activity_data for additional local image paths to upload
        final keysToUpload = actData.keys.where((k) => k.endsWith('_image_path')).toList();
        final Map<String, String> uploadedUrls = {};

        for (final key in keysToUpload) {
          final localPath = actData[key] as String?;
          if (localPath != null && localPath.isNotEmpty) {
            final cleanKey = key.replaceAll('_image_path', '');
            final fileName = '${activity['client_id']}_$cleanKey.jpg';
            final url = await uploadImageFromPath(localPath, fileName);
            if (url == null) {
              throw Exception('Additional image $cleanKey upload failed');
            }
            uploadedUrls['${cleanKey}_image_url'] = url;
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
        await LocalDbService.markAsFailed(clientId, e.toString());
        failed++;
      }
    }

    // Send batch request
    if (activitiesBatch.isNotEmpty) {
      try {
        final response = await ApiService.post(
          '/installations/batch',
          body: {'activities': activitiesBatch},
        );

        // Mark successful activities as synced
        final results = response['results'] as List? ?? [];
        for (final result in results) {
          final cid = result['client_id']?.toString() ?? '';
          if (cid.isEmpty) continue;

          if (result['status'] == 'submitted' || result['status'] == 'duplicate') {
            await LocalDbService.markAsSynced(cid);
            synced++;
          } else {
            final errorStr = result['error']?.toString() ?? 'Unknown backend validation error';
            await LocalDbService.markAsFailed(cid, errorStr);
            failed++;
          }
        }

        // Record successful sync time
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('last_sync_time', DateTime.now().toLocal().toString().split('.')[0]);
      } catch (e) {
        final errStr = e.toString();
        final isNetworkError = errStr.contains('SocketException') ||
            errStr.contains('Connection refused') ||
            errStr.contains('HandshakeException') ||
            errStr.contains('Network is unreachable') ||
            errStr.contains('Failed to fetch');

        if (!isNetworkError) {
          for (final act in activitiesBatch) {
            final cid = act['client_id']?.toString() ?? '';
            if (cid.isNotEmpty) {
              await LocalDbService.markAsFailed(cid, errStr);
            }
          }
        }
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
