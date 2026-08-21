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
            'source_url': 'https://example.edu/notice/1',
            'title': '奖学金申请通知',
            'content_text': '请按时提交材料。',
            'published_at': '2026-08-19T00:00:00Z',
            'fetched_at': '2026-08-19T01:00:00Z',
            'extensions_json': {
              'example.static': {'category': 'student'},
            },
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
    expect(messages.single.body, '请按时提交材料。');
    expect(messages.single.metadata, contains('example.static'));
  });

  test(
    'discovers Connector manifests and their configuration schema',
    () async {
      final client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/v1/connectors');
        return http.Response(
          jsonEncode([
            {
              'connector_id': 'example.static',
              'status': 'available',
              'manifest': {
                'connector_id': 'example.static',
                'version': '1.0.0',
                'contract_version': '1.0',
                'display_name': 'Example Static',
                'description': 'Public notices',
                'capabilities': ['sync'],
                'config_schema': {
                  'type': 'object',
                  'properties': {
                    'url': {'type': 'string', 'format': 'uri'},
                  },
                },
                'requires_browser': false,
              },
              'error': null,
            },
          ]),
          200,
        );
      });
      final api = CampusApi(baseUrl: 'https://campus.test', client: client);
      addTearDown(api.close);

      final connectors = await api.fetchConnectors();

      expect(connectors.single.isAvailable, isTrue);
      expect(connectors.single.manifest!.displayName, 'Example Static');
      expect(
        connectors.single.manifest!.configSchema['properties'],
        isA<Map>(),
      );
    },
  );

  test('creates a source, submits auth, and polls its sync job', () async {
    final requests = <http.Request>[];
    final client = MockClient((request) async {
      requests.add(request);
      if (request.url.path == '/v1/sources') {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['connector_id'], 'example.static');
        expect(body['config'], {'url': 'https://example.test/notices'});
        return http.Response(jsonEncode(_sourceJson()), 201);
      }
      if (request.url.path.endsWith('/auth/respond')) {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['challenge_id'], 'challenge-1');
        expect(body['response'], {'code': '123456'});
        return http.Response(
          jsonEncode({'state': 'ready', 'challenge': null, 'message': ''}),
          200,
        );
      }
      if (request.url.path.endsWith('/sync')) {
        return http.Response(jsonEncode(_jobJson('pending')), 202);
      }
      if (request.url.path == '/v1/jobs/job-1') {
        return http.Response(jsonEncode(_jobJson('succeeded')), 200);
      }
      fail('Unexpected request: ${request.method} ${request.url}');
    });
    final api = CampusApi(baseUrl: 'https://campus.test', client: client);
    addTearDown(api.close);

    final source = await api.createSource(
      name: 'Public notices',
      connectorId: 'example.static',
      config: {'url': 'https://example.test/notices'},
    );
    final auth = await api.submitAuthResponse(
      sourceId: source.id,
      challengeId: 'challenge-1',
      response: {'code': '123456'},
    );
    final queued = await api.syncSource(source.id);
    final completed = await api.fetchJob(queued.id);

    expect(source.connectorId, 'example.static');
    expect(auth.state, 'ready');
    expect(queued.status, 'pending');
    expect(completed.isTerminal, isTrue);
    expect(requests, hasLength(4));
  });
}

Map<String, Object?> _sourceJson() => {
  'id': 'source-1',
  'name': 'Public notices',
  'connector_id': 'example.static',
  'connector_version': '1.0.0',
  'enabled': true,
  'config': {'url': 'https://example.test/notices'},
  'auth_status': 'unknown',
  'sync_cursor': {},
  'last_success_at': null,
  'last_error': null,
  'created_at': '2026-08-21T00:00:00Z',
  'updated_at': '2026-08-21T00:00:00Z',
};

Map<String, Object?> _jobJson(String status) => {
  'id': 'job-1',
  'kind': 'sync_source',
  'payload': {'source_id': 'source-1'},
  'dedupe_key': 'manual-sync:source-1',
  'status': status,
  'attempts': status == 'succeeded' ? 1 : 0,
  'max_attempts': 3,
  'available_at': '2026-08-21T00:00:00Z',
  'last_error': null,
};
