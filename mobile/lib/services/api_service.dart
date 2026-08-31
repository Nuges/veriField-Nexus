// =============================================================================

// VeriField Nexus — API Service

// =============================================================================

// HTTP client wrapper for the FastAPI backend.

// Handles token attachment, error handling, and request formatting.

// =============================================================================



import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../core/config/supabase_config.dart';

/// Centralized API client for communicating with the FastAPI backend.
class ApiService {
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  static String _customBaseUrl = 'http://127.0.0.1:8000';

  static String get apiBaseUrl {
    const envUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (envUrl.isNotEmpty) return envUrl;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return _customBaseUrl;
  }

  static Future<void> setCustomServerUrl(String url) async {
    var cleaned = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
      cleaned = 'http://$cleaned';
    }
    _customBaseUrl = cleaned;
    debugPrint('[ApiService] Custom Server URL updated: $_customBaseUrl');
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('custom_server_url', cleaned);
    } catch (e) {
      debugPrint('[ApiService] Failed to persist custom_server_url: $e');
    }
  }

  static String get baseUrl {
    debugPrint('[ApiService] API Base URL requested: $apiBaseUrl/api/v1');
    return '$apiBaseUrl/api/v1';
  }

  static String? _customToken;

  static String? get customToken => _customToken;

  static Future<void> init() async {
    try {
      // 1. Try to read from Keychain/Keystore secure storage
      String? token;
      try {
        token = await _secureStorage.read(key: 'auth_token');
      } catch (se) {
        debugPrint('[ApiService] Secure storage read notice: $se');
      }

      // 2. Backward-compatible migration from legacy SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      if (token == null || token.isEmpty) {
        final legacyToken = prefs.getString('auth_token');
        if (legacyToken != null && legacyToken.isNotEmpty) {
          debugPrint('[ApiService] Migrating legacy token from SharedPreferences to FlutterSecureStorage');
          token = legacyToken;
          try {
            await _secureStorage.write(key: 'auth_token', value: legacyToken);
            await prefs.remove('auth_token'); // Safely purge plaintext token after migration
            debugPrint('[ApiService] Legacy token migration complete and plaintext purged.');
          } catch (me) {
            debugPrint('[ApiService] Secure storage migration warning: $me');
          }
        }
      }

      _customToken = token;

      final savedUrl = prefs.getString('custom_server_url');
      if (savedUrl != null && savedUrl.isNotEmpty) {
        _customBaseUrl = savedUrl;
        debugPrint('[ApiService] Loaded saved custom_server_url: $_customBaseUrl');
      }
      debugPrint('[ApiService] Initialized: customToken loaded: ${_customToken != null ? "exists" : "null"}');
    } catch (e) {
      debugPrint('[ApiService] Failed to initialize persistent customToken: $e');
    }
  }

  static Future<void> setCustomToken(String? token) async {
    _customToken = token;
    try {
      if (token == null) {
        try {
          await _secureStorage.delete(key: 'auth_token');
        } catch (_) {}
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove('auth_token');
        debugPrint('[ApiService] customToken cleared from secure storage');
      } else {
        try {
          await _secureStorage.write(key: 'auth_token', value: token);
          debugPrint('[ApiService] customToken saved to FlutterSecureStorage (Keychain/Keystore)');
        } catch (se) {
          debugPrint('[ApiService] Secure storage write fallback: $se');
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('auth_token', token);
        }
      }
    } catch (e) {
      debugPrint('[ApiService] Failed to save/clear customToken: $e');
    }
  }



  /// Log in with email and password via FastAPI backend.

  static Future<Map<String, dynamic>> login(String email, String password) async {

    final url = '$baseUrl/auth/login';

    debugPrint('[ApiService] Attempting backend login at: $url for email: $email');



    final response = await http.post(

      Uri.parse(url),

      headers: {

        'Content-Type': 'application/json',

      },

      body: jsonEncode({

        'email': email,

        'password': password,

      }),

    ).timeout(const Duration(seconds: 45));



    debugPrint('[ApiService] Backend login status code: ${response.statusCode}');

    return _handleResponse(response);

  }



  /// Sign up with email and password via FastAPI backend.

  static Future<Map<String, dynamic>> signup(String email, String password, String fullName) async {

    final url = '$baseUrl/auth/signup';

    debugPrint('[ApiService] Attempting backend signup at: $url for email: $email');



    final response = await http.post(

      Uri.parse(url),

      headers: {

        'Content-Type': 'application/json',

      },

      body: jsonEncode({

        'email': email,

        'password': password,

        'full_name': fullName,

      }),

    ).timeout(const Duration(seconds: 45));



    debugPrint('[ApiService] Backend signup status code: ${response.statusCode}');

    return _handleResponse(response);

  }



  /// Check server connectivity by querying /health endpoint.

  /// Auto-discovers and falls back across localhost, 127.0.0.1, 10.0.2.2, and custom URLs.

  static Future<bool> checkServerConnection() async {

    final candidateHosts = [
      apiBaseUrl,
      'https://verifield-nexus.onrender.com',
      if (apiBaseUrl.contains('127.0.0.1')) apiBaseUrl.replaceAll('127.0.0.1', 'localhost'),
      if (apiBaseUrl.contains('localhost')) apiBaseUrl.replaceAll('localhost', '127.0.0.1'),
      'http://127.0.0.1:8000',
      'http://localhost:8000',
      'http://10.0.2.2:8000',
    ];



    for (final host in candidateHosts) {

      final cleanHost = host.trim().replaceAll(RegExp(r'/+$'), '');

      final candidateHealthUrls = [

        '$cleanHost/health',

        '$cleanHost/api/v1/health',

      ];



      for (final healthUrl in candidateHealthUrls) {

        try {

          debugPrint('[ApiService] Probing server reachability at: $healthUrl');

          final response = await http.get(Uri.parse(healthUrl)).timeout(const Duration(seconds: 5));

          debugPrint('[ApiService] Probed $healthUrl -> Status: ${response.statusCode}');

          if (response.statusCode == 200) {

            _customBaseUrl = cleanHost;

            debugPrint('[ApiService] Connection established! Auto-locked to server URL: $_customBaseUrl');

            return true;

          }

        } catch (e) {

          debugPrint('[ApiService] Probe failed for $healthUrl: $e');

        }

      }

    }



    debugPrint('[ApiService] All candidate server connection probes failed.');

    return false;

  }



  /// Format an image URL to be fully qualified, handling relative paths and emulator localhost mapping.

  static String formatImageUrl(String? url) {

    if (url == null || url.isEmpty) return '';

    if (url.startsWith('/static/')) {

      final host = baseUrl.replaceAll('/api/v1', '');

      return '$host$url';

    }

    if (defaultTargetPlatform == TargetPlatform.android && !kIsWeb) {

      return url.replaceAll('localhost', '10.0.2.2').replaceAll('127.0.0.1', '10.0.2.2');

    }

    return url;

  }



  /// Get the current auth token from Supabase session.

  static String? get _authToken =>

      _customToken ?? SupabaseConfig.currentSession?.accessToken;



  /// Standard headers with auth token.

  static Map<String, String> get _headers {

    final token = _authToken;

    final headers = {

      'Content-Type': 'application/json',

      if (token != null) 'Authorization': 'Bearer $token',

    };

    debugPrint('[ApiService] Request Headers: $headers');

    return headers;

  }



  // =========================================================================

  // Generic HTTP Methods

  // =========================================================================



  /// Perform a GET request.

  static Future<Map<String, dynamic>> get(String endpoint) async {

    final response = await http.get(

      Uri.parse('$baseUrl$endpoint'),

      headers: _headers,

    );

    return _handleResponse(response);

  }



  /// Perform a POST request.

  static Future<Map<String, dynamic>> post(

    String endpoint, {

    Map<String, dynamic>? body,

  }) async {

    final response = await http.post(

      Uri.parse('$baseUrl$endpoint'),

      headers: _headers,

      body: body != null ? jsonEncode(body) : null,

    );

    return _handleResponse(response);

  }



  /// Perform a PUT request.

  static Future<Map<String, dynamic>> put(

    String endpoint, {

    Map<String, dynamic>? body,

  }) async {

    final response = await http.put(

      Uri.parse('$baseUrl$endpoint'),

      headers: _headers,

      body: body != null ? jsonEncode(body) : null,

    );

    return _handleResponse(response);

  }



  /// Perform a PATCH request.

  static Future<Map<String, dynamic>> patch(

    String endpoint, {

    Map<String, dynamic>? body,

  }) async {

    final response = await http.patch(

      Uri.parse('$baseUrl$endpoint'),

      headers: _headers,

      body: body != null ? jsonEncode(body) : null,

    );

    return _handleResponse(response);

  }



  /// Perform a DELETE request.

  static Future<Map<String, dynamic>> delete(String endpoint) async {

    final response = await http.delete(

      Uri.parse('$baseUrl$endpoint'),

      headers: _headers,

    );

    return _handleResponse(response);

  }



  /// Upload an avatar image file.

  static Future<Map<String, dynamic>> uploadAvatar(XFile file) async {

    final uri = Uri.parse('$baseUrl/auth/upload-avatar');

    final request = http.MultipartRequest('POST', uri);

    if (_authToken != null) {

      request.headers['Authorization'] = 'Bearer $_authToken';

    }

    if (kIsWeb) {

      final bytes = await file.readAsBytes();

      final multipartFile = http.MultipartFile.fromBytes(

        'file',

        bytes,

        filename: file.name,

      );

      request.files.add(multipartFile);

    } else {

      final multipartFile = await http.MultipartFile.fromPath('file', file.path);

      request.files.add(multipartFile);

    }

    final streamedResponse = await request.send();

    final response = await http.Response.fromStream(streamedResponse);

    return _handleResponse(response);

  }



  /// Upload a proof/activity image via the backend's /activities/upload-proof
  /// endpoint. Returns the image URL from Supabase Storage (live) or local
  /// filesystem (dev). This routes through the authenticated backend so the
  /// mobile app does not need direct Supabase Storage credentials.
  static Future<String?> uploadProofImage(XFile file, {String? fileName}) async {

    try {

      final uri = Uri.parse('$baseUrl/activities/upload-proof');

      final request = http.MultipartRequest('POST', uri);

      if (_authToken != null) {

        request.headers['Authorization'] = 'Bearer $_authToken';

      }

      final effectiveName = fileName ?? file.name;

      if (kIsWeb) {

        final bytes = await file.readAsBytes();

        final multipartFile = http.MultipartFile.fromBytes(

          'file',

          bytes,

          filename: effectiveName,

        );

        request.files.add(multipartFile);

      } else {

        final multipartFile = await http.MultipartFile.fromPath(

          'file', file.path, filename: effectiveName,

        );

        request.files.add(multipartFile);

      }

      final streamedResponse = await request.send().timeout(const Duration(seconds: 60));

      final response = await http.Response.fromStream(streamedResponse);

      debugPrint('[ApiService] uploadProofImage status: ${response.statusCode}');

      if (response.statusCode == 200 || response.statusCode == 201) {

        final data = jsonDecode(response.body) as Map<String, dynamic>;

        return data['image_url'] as String?;

      } else {

        debugPrint('[ApiService] uploadProofImage failed: ${response.body}');

        return null;

      }

    } catch (e) {

      debugPrint('[ApiService] uploadProofImage exception: $e');

      return null;

    }

  }



  // =========================================================================

  // Response Handler

  // =========================================================================



  /// Parse API response and handle errors.

  static Map<String, dynamic> _handleResponse(http.Response response) {

    final body = jsonDecode(response.body);



    if (response.statusCode >= 200 && response.statusCode < 300) {

      if (body is Map<String, dynamic>) return body;

      if (body is List) return {'data': body};

      return {'data': body};

    }



    // Error response

    final detail = body is Map ? body['detail'] ?? 'Unknown error' : 'Unknown error';

    throw ApiException(

      statusCode: response.statusCode,

      message: detail.toString(),

    );

  }

}



/// Custom exception for API errors.

class ApiException implements Exception {

  final int statusCode;

  final String message;



  ApiException({required this.statusCode, required this.message});



  @override

  String toString() => 'ApiException($statusCode): $message';

}
