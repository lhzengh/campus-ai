import 'dart:convert';

import 'package:campus_ai_client/data/campus_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('requires a configured URL without embedded credentials', () {
    expect(() => CampusApi(baseUrl: ''), throwsArgumentError);
    expect(
      () => CampusApi(baseUrl: 'https://user:password@campus.test'),
      throwsArgumentError,
    );
  });

  test('decodes the backend message contract', () async {
    final client = MockClient((request) async {
      expect(
        request.url.toString(),
        'https://campus.test/v1/messages?limit=25',
      );
      return http.Response(
        jsonEncode([
          {
            'id': 'message-1',
            'source_id': 'source-1',
            'external_id': 'external-1',
            'url': 'https://example.edu/notice/1',
            'title': '奖学金申请通知',
            'body': '请按时提交材料。',
            'published_at': '2026-08-19T00:00:00Z',
            'fetched_at': '2026-08-19T01:00:00Z',
            'metadata_json': {'category': 'student'},
          },
        ]),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final api = CampusApi(baseUrl: 'https://campus.test/', client: client);
    addTearDown(api.close);

    final messages = await api.fetchMessages(limit: 25);

    expect(messages, hasLength(1));
    expect(messages.single.title, '奖学金申请通知');
    expect(messages.single.metadata['category'], 'student');
  });
}
