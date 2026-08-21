import 'dart:convert';

import 'package:campus_ai_client/data/campus_message.dart';
import 'package:http/http.dart' as http;

class CampusApi {
  CampusApi({required String baseUrl, http.Client? client})
    : baseUrl = _validateBaseUrl(baseUrl),
      _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

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
    final root = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final response = await _client
        .get(Uri.parse('$root/v1/messages?limit=$limit'))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw CampusApiException(
        '消息同步失败：HTTP ${response.statusCode}',
        response.body,
      );
    }
    final payload = jsonDecode(response.body);
    if (payload is! List) {
      throw const CampusApiException('消息接口返回的不是数组');
    }
    return payload
        .map(
          (item) => CampusMessage.fromJson(
            (item as Map).map((key, value) => MapEntry(key.toString(), value)),
          ),
        )
        .toList(growable: false);
  }

  void close() => _client.close();
}

class CampusApiException implements Exception {
  const CampusApiException(this.message, [this.responseBody]);

  final String message;
  final String? responseBody;

  @override
  String toString() => message;
}
