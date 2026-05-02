// =============================================================================
// VeriField Nexus — Local Database Service
// =============================================================================
// SQLite database for offline-first data storage.
// Stores activities locally before syncing to the server.
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
      version: 1,
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
      },
    );
  }

  // =========================================================================
  // Pending Activities (Offline Queue)
  // =========================================================================

  /// Save an activity to the local offline queue.
  static Future<void> savePendingActivity(Map<String, dynamic> activity) async {
    if (kIsWeb) return; // Skip offline queue on web
    final db = await database;
    // Convert nested maps to JSON strings for SQLite storage
    if (activity['activity_data'] is Map) {
      activity['activity_data'] = jsonEncode(activity['activity_data']);
    }
    await db.insert('pending_activities', activity,
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// Get all pending activities that need syncing.
  static Future<List<Map<String, dynamic>>> getPendingActivities() async {
    if (kIsWeb) return [];
    final db = await database;
    final results = await db.query(
      'pending_activities',
      where: 'sync_status = ?',
      whereArgs: ['pending'],
      orderBy: 'created_at ASC',
    );
    // Parse JSON strings back to maps
    return results.map((row) {
      final mutable = Map<String, dynamic>.from(row);
      if (mutable['activity_data'] is String) {
        try {
          mutable['activity_data'] = jsonDecode(mutable['activity_data']);
        } catch (_) {}
      }
      return mutable;
    }).toList();
  }

  /// Mark a pending activity as synced.
  static Future<void> markAsSynced(String clientId) async {
    if (kIsWeb) return;
    final db = await database;
    await db.update(
      'pending_activities',
      {'sync_status': 'synced'},
      where: 'client_id = ?',
      whereArgs: [clientId],
    );
  }

  /// Get the count of pending (unsynced) activities.
  static Future<int> getPendingCount() async {
    if (kIsWeb) return 0;
    final db = await database;
    final result = await db.rawQuery(
      'SELECT COUNT(*) as count FROM pending_activities WHERE sync_status = ?',
      ['pending'],
    );
    return Sqflite.firstIntValue(result) ?? 0;
  }

  // =========================================================================
  // Cached Activities
  // =========================================================================

  /// Cache activities fetched from the server.
  static Future<void> cacheActivities(List<Map<String, dynamic>> activities) async {
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
}
