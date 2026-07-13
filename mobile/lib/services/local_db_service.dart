// =============================================================================
// VeriField Nexus — Local Database Service
// =============================================================================
// SQLite database for offline-first data storage.
// Stores activities locally before syncing to the server.
//
// v1: pending_activities, cached_activities
// v2: + error_message, retry_count on pending_activities
// v3: + assets table, sector_schemas table, sector column on pending_activities
// =============================================================================

import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:flutter/foundation.dart';

/// Local SQLite database for offline activity storage.
class LocalDbService {
  static Database? _db;

  /// Get the database instance (lazy initialization).
  static Future<Database> get database async {
    if (kIsWeb) throw UnsupportedError('SQLite is not supported on Web');
    if (_db != null) return _db!;
    _db = await _initDatabase();
    return _db!;
  }

  /// Initialize the SQLite database with required tables.
  static Future<Database> _initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'verifield_nexus.db');

    return openDatabase(
      path,
      version: 3,
      onCreate: (db, version) async {
        // Pending activities awaiting sync
        await db.execute('''
          CREATE TABLE pending_activities (
            id TEXT PRIMARY KEY,
            client_id TEXT UNIQUE NOT NULL,
            activity_type TEXT NOT NULL,
            activity_data TEXT,
            description TEXT,
            image_path TEXT,
            image_hash TEXT,
            latitude REAL,
            longitude REAL,
            gps_accuracy REAL,
            captured_at TEXT NOT NULL,
            property_id TEXT,
            sync_status TEXT DEFAULT 'pending',
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            sector TEXT,
            created_at TEXT NOT NULL
          )
        ''');

        // Cached activities (synced from server)
        await db.execute('''
          CREATE TABLE cached_activities (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            activity_data TEXT,
            description TEXT,
            image_url TEXT,
            latitude REAL,
            longitude REAL,
            trust_score REAL,
            status TEXT,
            captured_at TEXT,
            created_at TEXT
          )
        ''');

        // Unified assets table — sector-agnostic, schema-driven
        await db.execute('''
          CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            organization_id TEXT,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            sector TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            latitude REAL,
            longitude REAL,
            attributes TEXT,
            synced_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
          )
        ''');

        // Sector plugin schemas — cached from GET /api/v1/registry/plugins
        await db.execute('''
          CREATE TABLE IF NOT EXISTS sector_schemas (
            sector TEXT PRIMARY KEY,
            schema_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            synced_at TEXT NOT NULL
          )
        ''');
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute(
              'ALTER TABLE pending_activities ADD COLUMN error_message TEXT');
          await db.execute(
              'ALTER TABLE pending_activities ADD COLUMN retry_count INTEGER DEFAULT 0');
        }
        if (oldVersion < 3) {
          // Add sector column to pending_activities for sector-scoped queries.
          await db.execute(
              'ALTER TABLE pending_activities ADD COLUMN sector TEXT');

          // Create the unified assets table.
          await db.execute('''
            CREATE TABLE IF NOT EXISTS assets (
              id TEXT PRIMARY KEY,
              project_id TEXT,
              organization_id TEXT,
              name TEXT NOT NULL,
              asset_type TEXT NOT NULL,
              sector TEXT NOT NULL,
              status TEXT DEFAULT 'active',
              latitude REAL,
              longitude REAL,
              attributes TEXT,
              synced_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');

          // Create the sector schemas table.
          await db.execute('''
            CREATE TABLE IF NOT EXISTS sector_schemas (
              sector TEXT PRIMARY KEY,
              schema_json TEXT NOT NULL,
              metadata_json TEXT NOT NULL,
              synced_at TEXT NOT NULL
            )
          ''');
        }
      },
    );
  }

  // =========================================================================
  // Pending Activities (Offline Queue)
  // =========================================================================

  /// Save an activity to the local offline queue.
  static Future<void> savePendingActivity(
      Map<String, dynamic> activity) async {
    if (kIsWeb) return; // Skip offline queue on web
    final db = await database;
    // Convert nested maps to JSON strings for SQLite storage
    if (activity['activity_data'] is Map) {
      activity['activity_data'] = jsonEncode(activity['activity_data']);
    }
    await db.insert('pending_activities', activity,
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// Get all pending and failed activities.
  static Future<List<Map<String, dynamic>>> getPendingActivities() async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'pending_activities',
      where: 'sync_status = ? OR sync_status = ?',
      whereArgs: ['pending', 'failed'],
      orderBy: 'created_at ASC',
    );
    return _parseActivityRows(results);
  }

  /// Get all failed activities.
  static Future<List<Map<String, dynamic>>> getFailedActivities() async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'pending_activities',
      where: 'sync_status = ?',
      whereArgs: ['failed'],
      orderBy: 'created_at ASC',
    );
    return _parseActivityRows(results);
  }

  /// Get all activities that can be synced (pending, or failed with retry_count < 5).
  static Future<List<Map<String, dynamic>>> getRetryableActivities() async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'pending_activities',
      where:
          "sync_status = 'pending' OR (sync_status = 'failed' AND retry_count < 5)",
      orderBy: 'created_at ASC',
    );
    return _parseActivityRows(results);
  }

  /// Get pending activities filtered by sector.
  static Future<List<Map<String, dynamic>>> getPendingActivitiesBySector(
      String sector) async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'pending_activities',
      where:
          "(sync_status = 'pending' OR sync_status = 'failed') AND sector = ?",
      whereArgs: [sector],
      orderBy: 'created_at ASC',
    );
    return _parseActivityRows(results);
  }

  /// Parse raw SQLite rows back into usable maps with decoded activity_data.
  static List<Map<String, dynamic>> _parseActivityRows(
      List<Map<String, dynamic>> rows) {
    return rows.map((row) {
      final mutable = Map<String, dynamic>.from(row);
      if (mutable['activity_data'] is String) {
        try {
          mutable['activity_data'] = jsonDecode(mutable['activity_data']);
        } catch (_) {}
      }
      return mutable;
    }).toList();
  }

  /// Mark a pending activity as synced and reset error/retry values.
  static Future<void> markAsSynced(String clientId) async {
    if (kIsWeb) return;
    final db = await database;
    await db.update(
      'pending_activities',
      {
        'sync_status': 'synced',
        'error_message': null,
        'retry_count': 0,
      },
      where: 'client_id = ?',
      whereArgs: [clientId],
    );
  }

  /// Mark a pending activity as failed with an error message and increment retry_count.
  static Future<void> markAsFailed(String clientId, String error) async {
    if (kIsWeb) return;
    final db = await database;
    await db.rawUpdate('''
      UPDATE pending_activities 
      SET sync_status = ?, 
          error_message = ?, 
          retry_count = retry_count + 1 
      WHERE client_id = ?
    ''', ['failed', error, clientId]);
  }

  /// Get the count of pending and failed (unsynced) activities.
  static Future<int> getPendingCount() async {
    if (kIsWeb) return 0;
    final db = await database;
    final result = await db.rawQuery(
      "SELECT COUNT(*) as count FROM pending_activities WHERE sync_status = 'pending' OR sync_status = 'failed'",
    );
    return Sqflite.firstIntValue(result) ?? 0;
  }

  // =========================================================================
  // Cached Activities
  // =========================================================================

  /// Cache activities fetched from the server.
  static Future<void> cacheActivities(
      List<Map<String, dynamic>> activities) async {
    if (kIsWeb) return;
    final db = await database;
    final batch = db.batch();
    for (final activity in activities) {
      final row = Map<String, dynamic>.from(activity);
      if (row['activity_data'] is Map) {
        row['activity_data'] = jsonEncode(row['activity_data']);
      }
      batch.insert('cached_activities', row,
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  /// Get cached activities for offline viewing.
  static Future<List<Map<String, dynamic>>> getCachedActivities() async {
    if (kIsWeb) return [];
    final db = await database;
    return db.query('cached_activities', orderBy: 'created_at DESC');
  }

  // =========================================================================
  // Assets (Unified, Sector-Agnostic)
  // =========================================================================

  /// Save or update a single asset in the local database.
  ///
  /// The [asset] map must include at minimum: `id`, `name`, `asset_type`,
  /// `sector`, `created_at`, and `updated_at`. The `attributes` field should
  /// be a JSON-encodable Map containing sector-specific dynamic data.
  static Future<void> saveAsset(Map<String, dynamic> asset) async {
    if (kIsWeb) return;
    final db = await database;
    final row = Map<String, dynamic>.from(asset);
    // Serialize the dynamic attributes blob
    if (row['attributes'] is Map) {
      row['attributes'] = jsonEncode(row['attributes']);
    }
    await db.insert('assets', row,
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// Batch-save a list of assets (used during sync).
  static Future<void> saveAssets(List<Map<String, dynamic>> assets) async {
    if (kIsWeb) return;
    final db = await database;
    final batch = db.batch();
    for (final asset in assets) {
      final row = Map<String, dynamic>.from(asset);
      if (row['attributes'] is Map) {
        row['attributes'] = jsonEncode(row['attributes']);
      }
      batch.insert('assets', row,
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  /// Get all assets for a given [sector], e.g. 'cookstove', 'ev_mobility'.
  ///
  /// Returns decoded `attributes` as a Map.
  static Future<List<Map<String, dynamic>>> getAssets(String sector) async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'assets',
      where: 'sector = ?',
      whereArgs: [sector],
      orderBy: 'updated_at DESC',
    );
    return _parseAssetRows(results);
  }

  /// Get all assets regardless of sector (for dashboard summaries, etc.).
  static Future<List<Map<String, dynamic>>> getAllAssets() async {
    if (kIsWeb) return [];
    final db = await database;
    final results =
        await db.query('assets', orderBy: 'updated_at DESC');
    return _parseAssetRows(results);
  }

  /// Get a single asset by its [id].
  static Future<Map<String, dynamic>?> getAssetById(String id) async {
    if (kIsWeb) return null;
    final db = await database;
    final results = await db.query(
      'assets',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (results.isEmpty) return null;
    return _parseAssetRows(results).first;
  }

  /// Get assets filtered by [sector] and [status].
  static Future<List<Map<String, dynamic>>> getAssetsBySectorAndStatus(
      String sector, String status) async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'assets',
      where: 'sector = ? AND status = ?',
      whereArgs: [sector, status],
      orderBy: 'updated_at DESC',
    );
    return _parseAssetRows(results);
  }

  /// Delete a single asset by its [id].
  static Future<void> deleteAsset(String id) async {
    if (kIsWeb) return;
    final db = await database;
    await db.delete('assets', where: 'id = ?', whereArgs: [id]);
  }

  /// Parse asset rows, deserializing the `attributes` JSON blob.
  static List<Map<String, dynamic>> _parseAssetRows(
      List<Map<String, dynamic>> rows) {
    return rows.map((row) {
      final mutable = Map<String, dynamic>.from(row);
      if (mutable['attributes'] is String) {
        try {
          mutable['attributes'] = jsonDecode(mutable['attributes']);
        } catch (_) {}
      }
      return mutable;
    }).toList();
  }

  // =========================================================================
  // Sector Schemas (Plugin Definitions Cache)
  // =========================================================================

  /// Save or update a sector plugin schema.
  ///
  /// [sector] — e.g. 'cookstove', 'hybrid_energy', 'biochar', 'ev_mobility'.
  /// [schemaJson] — the JSON schema defining form fields and validation rules.
  /// [metadataJson] — plugin metadata (name, version, asset types, etc.).
  /// [syncedAt] — ISO 8601 timestamp of when the schema was fetched.
  static Future<void> saveSectorSchema({
    required String sector,
    required Map<String, dynamic> schemaJson,
    required Map<String, dynamic> metadataJson,
    required String syncedAt,
  }) async {
    if (kIsWeb) return;
    final db = await database;
    await db.insert(
      'sector_schemas',
      {
        'sector': sector,
        'schema_json': jsonEncode(schemaJson),
        'metadata_json': jsonEncode(metadataJson),
        'synced_at': syncedAt,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Get the cached schema for a single [sector].
  ///
  /// Returns `null` if no schema is cached for the requested sector.
  static Future<Map<String, dynamic>?> getSectorSchema(String sector) async {
    if (kIsWeb) return null;
    final db = await database;
    final results = await db.query(
      'sector_schemas',
      where: 'sector = ?',
      whereArgs: [sector],
      limit: 1,
    );
    if (results.isEmpty) return null;
    return _parseSectorSchemaRow(results.first);
  }

  /// Get all cached sector schemas.
  static Future<List<Map<String, dynamic>>> getAllSectorSchemas() async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query('sector_schemas');
    return results.map(_parseSectorSchemaRow).toList();
  }

  /// Delete a single sector schema.
  static Future<void> deleteSectorSchema(String sector) async {
    if (kIsWeb) return;
    final db = await database;
    await db.delete('sector_schemas',
        where: 'sector = ?', whereArgs: [sector]);
  }

  /// Parse a sector_schemas row, deserializing the JSON blobs.
  static Map<String, dynamic> _parseSectorSchemaRow(
      Map<String, dynamic> row) {
    final mutable = Map<String, dynamic>.from(row);
    if (mutable['schema_json'] is String) {
      try {
        mutable['schema_json'] = jsonDecode(mutable['schema_json']);
      } catch (_) {}
    }
    if (mutable['metadata_json'] is String) {
      try {
        mutable['metadata_json'] = jsonDecode(mutable['metadata_json']);
      } catch (_) {}
    }
    return mutable;
  }
}
