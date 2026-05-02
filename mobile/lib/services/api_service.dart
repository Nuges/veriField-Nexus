// =============================================================================
// VeriField Nexus — API Service
// =============================================================================
// HTTP client wrapper for the FastAPI backend.
// Handles token attachment, error handling, and request formatting.
// =============================================================================

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../core/config/supabase_config.dart';

/// Centralized API client for communicating with the FastAPI backend.
class ApiService {
  static String get baseUrl {
    // Return the production Render URL
    return 'https://verifield-nexus.onrender.com/api/v1';
  }

  /// Get the current auth token from Supabase session.
  static String? get _authToken =>
      SupabaseConfig.currentSession?.accessToken;

  /// Standard headers with auth token.
  static Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

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

  /// Perform a DELETE request.
  static Future<Map<String, dynamic>> delete(String endpoint) async {
    final response = await http.delete(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
    );
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
