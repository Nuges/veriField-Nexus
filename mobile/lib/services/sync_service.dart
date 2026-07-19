// =============================================================================
// VeriField Nexus — Sync Service
// =============================================================================
// Offline-first sync engine that manages data synchronization:
// 1. Save activities locally when offline
// 2. Queue for sync when connectivity is restored
// 3. Batch upload pending activities to the server
// 4. Handle conflicts and deduplication via client_id
// 5. Incremental delta sync for assets & sector schemas (CIOS plugin-driven)
//
// Conflict resolution policy:
// - Server wins: sector schemas & project metadata (authoritative backend data)
// - Client wins: pending activities (never overwrite unsynced local data)
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

/// The four CIOS sectors supported by the platform.
class CiosSectors {
  CiosSectors._();

  static const String cookstove = 'cookstove';
  static const String hybridEnergy = 'hybrid_energy';
  static const String biochar = 'biochar';
  static const String evMobility = 'ev_mobility';

  /// All registered sector identifiers.
  static const List<String> all = [
    cookstove,
    hybridEnergy,
    biochar,
    evMobility,
  ];
}

/// Manages offline-first data synchronization.
class SyncService {
  // =========================================================================
  // Connectivity
  // =========================================================================

  /// Check if the device has internet connectivity.
  static Future<bool> isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return !result.contains(ConnectivityResult.none);
  }

  // =========================================================================
  // Image Upload
  // =========================================================================

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
  static Future<String?> uploadImageFromPath(
      String filePath, String fileName) async {
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

  // =========================================================================
  // Sector Schema Sync (Server → Client, server wins)
  // =========================================================================

  /// Download plugin schemas from the backend registry and cache them locally.
  ///
  /// Endpoint: GET /api/v1/registry/plugins
  /// Response shape:
  /// ```json
  /// {
  ///   "plugins": [
  ///     {
  ///       "sector": "cookstove",
  ///       "metadata": { ... },
  ///       "schema": { "type": "object", "properties": { ... } }
  ///     }
  ///   ]
  /// }
  /// ```
  ///
  /// Server wins: local schema cache is always replaced with the latest
  /// backend version. This ensures field agents always have the most current
  /// form definitions, asset types, and validation rules.
  static Future<SyncResult> syncSectorSchemas() async {
    if (!await isOnline()) {
      return SyncResult(
          synced: 0, failed: 0, message: 'No internet connection');
    }

    try {
      final response = await ApiService.get('/registry/plugins');
      final plugins = response['plugins'] as List? ?? [];

      if (plugins.isEmpty) {
        return SyncResult(
            synced: 0, failed: 0, message: 'No plugins returned');
      }

      int synced = 0;
      int failed = 0;
      final now = DateTime.now().toIso8601String();

      for (final plugin in plugins) {
        try {
          final sector = plugin['sector'] as String? ?? '';
          if (sector.isEmpty) continue;

          final schema =
              (plugin['schema'] as Map<String, dynamic>?) ?? {};
          final metadata =
              (plugin['metadata'] as Map<String, dynamic>?) ?? {};

          await LocalDbService.saveSectorSchema(
            sector: sector,
            schemaJson: schema,
            metadataJson: metadata,
            syncedAt: now,
          );
          synced++;
        } catch (e) {
          debugPrint(
              '[SyncService] Failed to save schema for plugin: $e');
          failed++;
        }
      }

      // Record last sync timestamp for schemas.
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('last_schema_sync_time', now);

      return SyncResult(
        synced: synced,
        failed: failed,
        message: '$synced sector schemas synced',
      );
    } catch (e) {
      debugPrint('[SyncService] syncSectorSchemas error: $e');
      return SyncResult(
          synced: 0, failed: 0, message: 'Schema sync failed: $e');
    }
  }

  // =========================================================================
  // Asset Sync — Incremental Delta (Server → Client, server wins)
  // =========================================================================

  /// Download assets for a specific [sector] using timestamp-based delta sync.
  ///
  /// Only assets updated after the last sync timestamp are fetched. The
  /// `last_sync_timestamp` is stored per-sector in SharedPreferences, keyed
  /// as `last_asset_sync_{sector}`.
  ///
  /// Endpoint: GET /api/v1/assets?sector={sector}&updated_after={timestamp}
  /// Response shape:
  /// ```json
  /// {
  ///   "assets": [ { "id": "...", "name": "...", ... } ],
  ///   "total": 42,
  ///   "has_more": false
  /// }
  /// ```
  static Future<SyncResult> syncAssetsForSector(String sector) async {
    if (!await isOnline()) {
      return SyncResult(
          synced: 0, failed: 0, message: 'No internet connection');
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      final lastSyncKey = 'last_asset_sync_$sector';
      final lastSync = prefs.getString(lastSyncKey);

      // Build query parameters for incremental delta fetch.
      final queryParams = <String, String>{
        'sector': sector,
      };
      if (lastSync != null) {
        queryParams['updated_after'] = lastSync;
      }

      final queryString = queryParams.entries
          .map((e) =>
              '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
          .join('&');

      int totalSynced = 0;
      bool hasMore = true;
      int page = 1;

      // Paginated fetch loop for large datasets.
      while (hasMore) {
        final endpoint = '/assets?$queryString&page=$page&page_size=100';
        final response = await ApiService.get(endpoint);

        final assets = (response['assets'] as List?) ?? [];
        if (assets.isEmpty) break;

        // Batch-save to local DB (server wins — overwrites local cache).
        final assetMaps = assets
            .whereType<Map<String, dynamic>>()
            .toList();
        await LocalDbService.saveAssets(assetMaps);

        totalSynced += assetMaps.length;
        hasMore = response['has_more'] == true;
        page++;
      }

      // Update the per-sector sync timestamp.
      final now = DateTime.now().toIso8601String();
      await prefs.setString(lastSyncKey, now);

      return SyncResult(
        synced: totalSynced,
        failed: 0,
        message: '$totalSynced $sector assets synced',
      );
    } catch (e) {
      debugPrint('[SyncService] syncAssetsForSector($sector) error: $e');
      return SyncResult(
          synced: 0,
          failed: 0,
          message: 'Asset sync for $sector failed: $e');
    }
  }

  /// Sync assets for all licensed sectors.
  ///
  /// [licensedSectors] — list of sector identifiers the user's organization is
  /// licensed for. If null, syncs all known CIOS sectors.
  static Future<SyncResult> syncAllAssets(
      {List<String>? licensedSectors}) async {
    final sectors = licensedSectors ?? CiosSectors.all;
    int totalSynced = 0;
    int totalFailed = 0;
    final messages = <String>[];

    for (final sector in sectors) {
      final result = await syncAssetsForSector(sector);
      totalSynced += result.synced;
      totalFailed += result.failed;
      if (result.message.isNotEmpty) messages.add(result.message);
    }

    return SyncResult(
      synced: totalSynced,
      failed: totalFailed,
      message: messages.join('; '),
    );
  }

  // =========================================================================
  // Project Sync (Server → Client)
  // =========================================================================

  /// Download assigned projects for the logged-in user.
  ///
  /// Endpoint: GET /api/v1/projects/assigned
  /// The response is cached locally for offline access. Uses delta sync
  /// with `updated_after` timestamp stored in SharedPreferences.
  static Future<SyncResult> syncProjectsForUser() async {
    if (!await isOnline()) {
      return SyncResult(
          synced: 0, failed: 0, message: 'No internet connection');
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      final lastSync = prefs.getString('last_projects_sync_time');

      String endpoint = '/projects/assigned';
      if (lastSync != null) {
        endpoint += '?updated_after=${Uri.encodeComponent(lastSync)}';
      }

      final response = await ApiService.get(endpoint);
      final projects = (response['projects'] as List?) ??
          (response['data'] as List?) ??
          [];

      // Cache projects in SharedPreferences as JSON (lightweight data).
      if (projects.isNotEmpty) {
        // Merge with existing cached projects (server wins for conflicts).
        final existingJson = prefs.getString('cached_projects');
        final existing = existingJson != null
            ? (jsonDecode(existingJson) as List)
                .cast<Map<String, dynamic>>()
            : <Map<String, dynamic>>[];

        // Build a map keyed by project ID for merge.
        final merged = <String, Map<String, dynamic>>{};
        for (final p in existing) {
          final id = p['id']?.toString();
          if (id != null) merged[id] = p;
        }
        for (final p in projects) {
          if (p is Map<String, dynamic>) {
            final id = p['id']?.toString();
            if (id != null) merged[id] = p; // Server wins
          }
        }

        await prefs.setString(
            'cached_projects', jsonEncode(merged.values.toList()));
      }

      final now = DateTime.now().toIso8601String();
      await prefs.setString('last_projects_sync_time', now);

      return SyncResult(
        synced: projects.length,
        failed: 0,
        message: '${projects.length} projects synced',
      );
    } catch (e) {
      debugPrint('[SyncService] syncProjectsForUser error: $e');
      return SyncResult(
          synced: 0,
          failed: 0,
          message: 'Project sync failed: $e');
    }
  }

  // =========================================================================
  // Pending Activity Upload (Client → Server, client wins)
  // =========================================================================

  /// Sync pending activities to the server.
  /// Called when connectivity is restored or manually triggered.
  ///
  /// Conflict resolution: client wins. Pending local activities are never
  /// overwritten by server data. They are uploaded and marked as synced or
  /// failed (with retry). Duplicates are handled via `client_id` on the server.
  static Future<SyncResult> syncPendingActivities(
      {bool failedOnly = false, bool forceAll = false}) async {
    if (!await isOnline()) {
      return SyncResult(
          synced: 0, failed: 0, message: 'No internet connection');
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
          actData =
              Map<String, dynamic>.from(activity['activity_data'] as Map);
        } else if (activity['activity_data'] is String) {
          try {
            actData = jsonDecode(activity['activity_data'] as String)
                as Map<String, dynamic>;
          } catch (_) {}
        }

        // Upload primary image if present
        String? primaryUrl;
        if (activity['image_path'] != null) {
          final fileName = '${activity['client_id']}_primary.jpg';
          primaryUrl =
              await uploadImageFromPath(activity['image_path'], fileName);
          if (primaryUrl == null) {
            throw Exception('Primary image upload failed');
          }
        }

        // Scan activity_data for additional local image paths to upload.
        // Convention: keys ending in `_image_path` are local file paths that
        // need to be uploaded and replaced with `_image_url` keys.
        final keysToUpload =
            actData.keys.where((k) => k.endsWith('_image_path')).toList();
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

        // Clean up local paths and merge uploaded URL keys.
        for (final key in keysToUpload) {
          actData.remove(key);
        }
        actData.addAll(uploadedUrls);

        // ---------------------------------------------------------------
        // Generic primary image URL mapping.
        //
        // Instead of hardcoded sector-specific key names, we derive the
        // primary image key from the `sector` or `activity_type` stored
        // on the activity itself. The backend plugin schema defines which
        // key it expects; the mobile app infers it generically.
        // ---------------------------------------------------------------
        if (primaryUrl != null) {
          final primaryImageKey =
              _resolvePrimaryImageKey(activity, actData);
          actData['${primaryImageKey}_image_url'] = primaryUrl;
        }

        final batchItem = <String, dynamic>{
          'activity_type': activity['activity_type'],
          'sector': activity['sector'],
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
        };

        // ---------------------------------------------------------------
        // Generic sector-specific field promotion.
        //
        // Instead of hardcoding BIOCHAR_C_SINK field mappings, we promote
        // any top-level fields that the activity_data specifies. The
        // backend plugin schema defines which fields it expects at the
        // top level. If the activity_data contains fields with matching
        // keys, they are promoted into the batch item.
        //
        // The `_promoteSectorFields` method uses schema metadata (cached
        // from sector_schemas table) to determine which fields to promote.
        // ---------------------------------------------------------------
        await _promoteSectorFields(batchItem, actData, activity);

        activitiesBatch.add(batchItem);
      } catch (e) {
        await LocalDbService.markAsFailed(clientId, e.toString());
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
          final cid = result['client_id']?.toString() ?? '';
          if (cid.isEmpty) continue;

          if (result['status'] == 'submitted' ||
              result['status'] == 'duplicate') {
            await LocalDbService.markAsSynced(cid);
            synced++;
          } else {
            final errorStr = result['error']?.toString() ??
                'Unknown backend validation error';
            await LocalDbService.markAsFailed(cid, errorStr);
            failed++;
          }
        }

        // Record successful sync time
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('last_sync_time',
            DateTime.now().toLocal().toString().split('.')[0]);
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
        // For network errors, don't mark as failed — leave them for retry
        // on next connectivity restoration (resumable upload behavior).
        failed += activitiesBatch.length;
      }
    }

    return SyncResult(
      synced: synced,
      failed: failed,
      message: synced > 0 ? '$synced activities synced' : 'Sync failed',
    );
  }

  // =========================================================================
  // Generic Field Promotion (replaces hardcoded sector checks)
  // =========================================================================

  /// Resolve the primary image key name from the activity's sector/type.
  ///
  /// Falls back to the activity_type as a snake_case prefix if no sector
  /// schema is available. This replaces the old hardcoded mapping of
  /// HYBRID_ENERGY→solar_installation, BIOCHAR_C_SINK→kiln_pyrolysis, etc.
  static String _resolvePrimaryImageKey(
      Map<String, dynamic> activity, Map<String, dynamic> actData) {
    // Try to get the primary_image_key from cached sector schema metadata.
    // If not available, fall back to a sensible default.
    final sector = activity['sector'] as String?;
    final activityType = activity['activity_type'] as String? ?? '';

    // Check if activity_data has a `primary_image_key` hint from the schema.
    if (actData.containsKey('_primary_image_key')) {
      return actData.remove('_primary_image_key') as String;
    }

    // Fallback: derive from activity_type (snake_case).
    return activityType.toLowerCase();
  }

  /// Promote sector-specific fields from [actData] to the [batchItem] root.
  ///
  /// Uses the cached sector schema's `promoted_fields` metadata list if
  /// available. Otherwise, for backward compatibility with existing sectors,
  /// falls back to known field patterns.
  ///
  /// This is a generic replacement for the old hardcoded BIOCHAR_C_SINK
  /// field promotion block (lines 167-178 in the original sync_service.dart).
  static Future<void> _promoteSectorFields(
    Map<String, dynamic> batchItem,
    Map<String, dynamic> actData,
    Map<String, dynamic> activity,
  ) async {
    final sector = activity['sector'] as String?;
    if (sector == null) return;

    // Attempt to load the sector schema for promoted fields metadata.
    List<String>? promotedFields;
    try {
      final schemaRow = await LocalDbService.getSectorSchema(sector);
      if (schemaRow != null) {
        final metadata =
            schemaRow['metadata_json'] as Map<String, dynamic>?;
        if (metadata != null && metadata['promoted_fields'] is List) {
          promotedFields =
              (metadata['promoted_fields'] as List).cast<String>();
        }
      }
    } catch (_) {
      // Schema not cached yet — fall back to activity_data-driven promotion.
    }

    if (promotedFields != null && promotedFields.isNotEmpty) {
      // Schema-driven promotion: copy listed keys to the batch item root.
      for (final field in promotedFields) {
        if (actData.containsKey(field)) {
          batchItem[field] = actData[field];
        }
      }
    } else {
      // Backward-compatible: promote any fields from actData that have
      // corresponding evidence keys (ending in _image_url). This covers
      // all sectors generically without hardcoding field names.
      final evidenceKeys = actData.keys
          .where((k) => k.startsWith('evidence_') || k.endsWith('_image_url'))
          .toList();
      for (final key in evidenceKeys) {
        batchItem[key] = actData[key];
      }

      // Also promote known timestamp/coordinate/quantity fields that
      // commonly appear at the batch item root level.
      const commonPromotedPatterns = [
        'application_timestamp',
        'application_latitude',
        'application_longitude',
        'applied_quantity_kg',
        'remaining_quantity_kg',
        'field_agent_id',
      ];
      for (final pattern in commonPromotedPatterns) {
        if (actData.containsKey(pattern)) {
          batchItem[pattern] = actData[pattern];
        }
        // Also check activity-level fields for lat/lon overrides.
        if (pattern.contains('latitude') &&
            !actData.containsKey(pattern) &&
            activity.containsKey('latitude')) {
          batchItem[pattern] = activity['latitude'];
        }
        if (pattern.contains('longitude') &&
            !actData.containsKey(pattern) &&
            activity.containsKey('longitude')) {
          batchItem[pattern] = activity['longitude'];
        }
      }
    }
  }

  // =========================================================================
  // Full Sync (schemas + assets + projects + pending uploads)
  // =========================================================================

  /// Perform a full bidirectional sync:
  /// 1. Download latest sector schemas (server wins)
  /// 2. Download assets for licensed sectors (server wins, delta)
  /// 3. Download assigned projects (server wins, delta)
  /// 4. Upload pending activities (client wins)
  ///
  /// [licensedSectors] — optional list of sectors to sync assets for.
  /// If null, all CIOS sectors are synced.
  static Future<SyncResult> performFullSync(
      {List<String>? licensedSectors}) async {
    if (!await isOnline()) {
      return SyncResult(
          synced: 0, failed: 0, message: 'No internet connection');
    }

    int totalSynced = 0;
    int totalFailed = 0;
    final messages = <String>[];

    // 1. Sector schemas
    final schemaResult = await syncSectorSchemas();
    totalSynced += schemaResult.synced;
    totalFailed += schemaResult.failed;
    messages.add(schemaResult.message);

    // 2. Assets (incremental delta)
    final assetResult =
        await syncAllAssets(licensedSectors: licensedSectors);
    totalSynced += assetResult.synced;
    totalFailed += assetResult.failed;
    messages.add(assetResult.message);

    // 3. Projects
    final projectResult = await syncProjectsForUser();
    totalSynced += projectResult.synced;
    totalFailed += projectResult.failed;
    messages.add(projectResult.message);

    // 4. Pending activity upload
    final uploadResult = await syncPendingActivities();
    totalSynced += uploadResult.synced;
    totalFailed += uploadResult.failed;
    messages.add(uploadResult.message);

    return SyncResult(
      synced: totalSynced,
      failed: totalFailed,
      message: messages.where((m) => m.isNotEmpty).join('; '),
    );
  }

  // =========================================================================
  // Auto-Sync Listener
  // =========================================================================

  /// Listen for connectivity changes and auto-sync.
  static void startAutoSync() {
    Connectivity().onConnectivityChanged.listen((result) async {
      if (!result.contains(ConnectivityResult.none)) {
        // Device came online — sync pending data
        await syncPendingActivities();
      }
    });
  }

  // =========================================================================
  // Utilities
  // =========================================================================

  /// Get the last sync timestamp for a specific purpose.
  static Future<String?> getLastSyncTime(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(key);
  }

  /// Get cached projects from SharedPreferences.
  static Future<List<Map<String, dynamic>>> getCachedProjects() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('cached_projects');
    if (json == null) return [];
    try {
      return (jsonDecode(json) as List).cast<Map<String, dynamic>>();
    } catch (_) {
      return [];
    }
  }
}

/// Result of a sync operation.
class SyncResult {
  final int synced;
  final int failed;
  final String message;

  SyncResult(
      {required this.synced, required this.failed, required this.message});

  @override
  String toString() =>
      'SyncResult(synced: $synced, failed: $failed, message: $message)';
}
