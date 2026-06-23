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
import '../core/config/supabase_config.dart';

/// Centralized API client for communicating with the FastAPI backend.
class ApiService {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.1.100:8000',
  );

  static String get baseUrl {
    debugPrint('[ApiService] API Base URL requested: $apiBaseUrl/api/v1');
    return '$apiBaseUrl/api/v1';
  }

  static String? _customToken;

  static String? get customToken => _customToken;

  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _customToken = prefs.getString('auth_token');
      debugPrint('[ApiService] Initialized: customToken loaded: ${_customToken != null ? "exists" : "null"}');
    } catch (e) {
      debugPrint('[ApiService] Failed to initialize persistent customToken: $e');
    }
  }

  static Future<void> setCustomToken(String? token) async {
    _customToken = token;
    try {
      final prefs = await SharedPreferences.getInstance();
      if (token == null) {
        await prefs.remove('auth_token');
        debugPrint('[ApiService] customToken cleared from SharedPreferences');
      } else {
        await prefs.setString('auth_token', token);
        debugPrint('[ApiService] customToken saved to SharedPreferences');
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
    ).timeout(const Duration(seconds: 15));
    
    debugPrint('[ApiService] Backend login status code: ${response.statusCode}');
    return _handleResponse(response);
  }

  /// Check server connectivity by querying /health endpoint.
  static Future<bool> checkServerConnection() async {
    final healthUrl = '$apiBaseUrl/health';
    debugPrint('[ApiService] Verifying server reachability at: $healthUrl');
    try {
      final response = await http.get(Uri.parse(healthUrl)).timeout(
        const Duration(seconds: 30),
      );
      debugPrint('[ApiService] Server responded with status code: ${response.statusCode}');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] Server check failed: $e');
      return false;
    }
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
