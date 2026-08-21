import 'dart:convert';

import 'package:campus_ai_client/data/campus_message.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:http/http.dart' as http;

class CampusApi {
  CampusApi({required String baseUrl, http.Client? client})
    : baseUrl = _validateBaseUrl(baseUrl),
      _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  String get _root => baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;

  static String _validateBaseUrl(String value) {
    final normalized = value.trim();
    final uri = Uri.tryParse(normalized);
    if (uri == null ||
        !uri.hasAuthority ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      throw ArgumentError.value(
        value,
        'baseUrl',
        'Set CAMPUS_AI_API_URL to an absolute HTTP(S) URL at build time.',
      );
    }
    if (uri.userInfo.isNotEmpty) {
      throw ArgumentError.value(
        value,
        'baseUrl',
        'Credentials must not be embedded in CAMPUS_AI_API_URL.',
      );
    }
    return normalized;
  }

  Future<List<CampusMessage>> fetchMessages({int limit = 100}) async {
    final payload = await _request('GET', '/v1/messages?limit=$limit');
    if (payload is! List) {
      throw const CampusApiException(
        'The messages endpoint did not return an array.',
      );
    }
    return payload
        .map(
          (item) => CampusMessage.fromJson(
            (item as Map).map((key, value) => MapEntry(key.toString(), value)),
          ),
        )
        .toList(growable: false);
  }

  Future<List<ConnectorRegistration>> fetchConnectors() async {
    final payload = await _request('GET', '/v1/connectors');
    if (payload is! List) {
      throw const CampusApiException(
        'The Connectors endpoint did not return an array.',
      );
    }
    return payload
        .map((item) => ConnectorRegistration.fromJson(_jsonMap(item as Map)))
        .toList(growable: false);
  }

  Future<List<SourceInstance>> fetchSources({
    bool includeArchived = false,
  }) async {
    final payload = await _request(
      'GET',
      '/v1/sources?include_archived=$includeArchived',
    );
    if (payload is! List) {
      throw const CampusApiException(
        'The sources endpoint did not return an array.',
      );
    }
    return payload
        .map((item) => SourceInstance.fromJson(_jsonMap(item as Map)))
        .toList(growable: false);
  }

  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
    bool enabled = true,
    SourceScheduleData schedule = SourceScheduleData.dailyDefault,
  }) async {
    final payload = await _request(
      'POST',
      '/v1/sources',
      body: {
        'name': name,
        'connector_id': connectorId,
        'config': config,
        'enabled': enabled,
        'schedule': schedule.toJson(),
      },
    );
    return SourceInstance.fromJson(_requiredMap(payload, 'Create source'));
  }

  Future<SourceInstance> updateSource({
    required String sourceId,
    String? name,
    JsonMap? config,
    bool? enabled,
    SourceScheduleData? schedule,
  }) async {
    final body = <String, Object?>{
      'name': ?name,
      'config': ?config,
      'enabled': ?enabled,
      if (schedule != null) 'schedule': schedule.toJson(),
    };
    final payload = await _request(
      'PATCH',
      '/v1/sources/${Uri.encodeComponent(sourceId)}',
      body: body,
    );
    return SourceInstance.fromJson(_requiredMap(payload, 'Update source'));
  }

  Future<void> archiveSource(String sourceId) async {
    await _request('DELETE', '/v1/sources/${Uri.encodeComponent(sourceId)}');
  }

  Future<SourceInstance> restoreSource(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/restore',
    );
    return SourceInstance.fromJson(_requiredMap(payload, 'Restore source'));
  }

  Future<SourceCheckData> checkSource(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/check',
    );
    return SourceCheckData.fromJson(_requiredMap(payload, 'Check source'));
  }

  Future<AuthResultData> fetchAuthStatus(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/auth/status',
    );
    return AuthResultData.fromJson(
      _requiredMap(payload, 'Authentication status'),
    );
  }

  Future<AuthResultData> beginAuth(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/auth/begin',
    );
    return AuthResultData.fromJson(
      _requiredMap(payload, 'Authentication challenge'),
    );
  }

  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  }) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/auth/respond',
      body: {'challenge_id': challengeId, 'response': response},
    );
    return AuthResultData.fromJson(
      _requiredMap(payload, 'Authentication response'),
    );
  }

  Future<CampusJob> syncSource(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/sync',
    );
    return CampusJob.fromJson(_requiredMap(payload, 'Sync job'));
  }

  Future<CampusJob> previewSource(String sourceId) async {
    final payload = await _request(
      'POST',
      '/v1/sources/${Uri.encodeComponent(sourceId)}/preview',
    );
    return CampusJob.fromJson(_requiredMap(payload, 'Preview job'));
  }

  Future<CampusJob> fetchJob(String jobId) async {
    final payload = await _request(
      'GET',
      '/v1/jobs/${Uri.encodeComponent(jobId)}',
    );
    return CampusJob.fromJson(_requiredMap(payload, 'Job status'));
  }

  Future<Object?> _request(String method, String path, {JsonMap? body}) async {
    final uri = Uri.parse('$_root$path');
    final headers = body == null
        ? const <String, String>{'accept': 'application/json'}
        : const <String, String>{
            'accept': 'application/json',
            'content-type': 'application/json',
          };
    final request = http.Request(method, uri)..headers.addAll(headers);
    if (body != null) request.body = jsonEncode(body);
    final streamed = await _client
        .send(request)
        .timeout(const Duration(seconds: 15));
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw CampusApiException(
        _errorMessage(response),
        response.body,
        response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    try {
      return jsonDecode(response.body);
    } on FormatException catch (error) {
      throw CampusApiException(
        'Core returned invalid JSON: $error',
        response.body,
      );
    }
  }

  static String _errorMessage(http.Response response) {
    try {
      final payload = jsonDecode(response.body);
      if (payload is Map) {
        final detail = payload['detail'];
        if (detail != null) {
          if (detail is Map && detail['message'] != null) {
            return detail['message'].toString();
          }
          return detail.toString();
        }
      }
    } on FormatException {
      // Fall back to a stable HTTP message when the response is not JSON.
    }
    return 'Core request failed: HTTP ${response.statusCode}';
  }

  static JsonMap _requiredMap(Object? value, String operation) {
    if (value is! Map) {
      throw CampusApiException('$operation did not return an object.');
    }
    return _jsonMap(value);
  }

  static JsonMap _jsonMap(Map<dynamic, dynamic> value) =>
      value.map((key, item) => MapEntry(key.toString(), item));

  void close() => _client.close();
}

class CampusApiException implements Exception {
  const CampusApiException(this.message, [this.responseBody, this.statusCode]);

  final String message;
  final String? responseBody;
  final int? statusCode;

  @override
  String toString() => message;
}
