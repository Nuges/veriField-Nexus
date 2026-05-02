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
        // Upload image if there's a local path
        String? imageUrl;
        if (activity['image_path'] != null) {
          final file = File(activity['image_path']);
          if (await file.exists()) {
            final fileName =
                '${activity['client_id']}_${DateTime.now().millisecondsSinceEpoch}.jpg';
            imageUrl = await uploadImage(file, fileName);
          }
        }

        activitiesBatch.add({
          'activity_type': activity['activity_type'],
          'activity_data': activity['activity_data'] != null ? jsonDecode(activity['activity_data'] as String) : null,
          'description': activity['description'],
          'image_url': imageUrl,
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
