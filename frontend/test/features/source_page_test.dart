import 'package:campus_ai_client/app.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/data/source_repository.dart';
import 'package:campus_ai_client/features/sources/source_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('creates a source from a Connector schema', (tester) async {
    tester.view.physicalSize = const Size(800, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    appRouter.go('/sources');
    final store = _FakeSourceStore();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [sourceStoreProvider.overrideWithValue(store)],
        child: const CampusAiApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('No sources configured'), findsOneWidget);
    await tester.tap(find.text('Add source').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Example Static'));
    await tester.pumpAndSettle();

    expect(find.text('Create source'), findsWidgets);
    final fields = find.byType(EditableText);
    await tester.enterText(fields.at(0), 'Public notices');
    await tester.enterText(fields.at(1), 'https://example.test/notices');
    final createButton = find.widgetWithText(FilledButton, 'Create source');
    await tester.ensureVisible(createButton);
    await tester.tap(createButton);
    await tester.pumpAndSettle();

    expect(find.text('Public notices'), findsOneWidget);
    expect(store.createdConfig, {
      'url': 'https://example.test/notices',
      'interval': 0.5,
      'enabled': false,
    });
    expect(store.createdConfig, isNot(contains('password')));
  });
}

class _FakeSourceStore implements SourceStore {
  final List<SourceInstance> _sources = [];
  JsonMap? createdConfig;

  static const manifest = ConnectorManifestData(
    connectorId: 'example.static',
    version: '1.0.0',
    displayName: 'Example Static',
    description: 'Collects public notices.',
    capabilities: {'sync'},
    configSchema: {
      'type': 'object',
      'required': ['url', 'enabled'],
      'properties': {
        'url': {'type': 'string', 'format': 'uri', 'title': 'URL'},
        'interval': {'type': 'number', 'minimum': 0, 'default': 0.5},
        'enabled': {'type': 'boolean'},
        'password': {
          'type': 'string',
          'title': 'Password',
          'x-campus-secret': true,
        },
      },
    },
    requiresBrowser: false,
  );

  @override
  Future<List<ConnectorRegistration>> fetchConnectors() async => const [
    ConnectorRegistration(
      connectorId: 'example.static',
      status: 'available',
      manifest: manifest,
    ),
  ];

  @override
  Future<List<SourceInstance>> fetchSources() async => List.of(_sources);

  @override
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
  }) async {
    createdConfig = config;
    final source = SourceInstance(
      id: 'source-1',
      name: name,
      connectorId: connectorId,
      connectorVersion: '1.0.0',
      enabled: true,
      config: config,
      authStatus: 'not_required',
      createdAt: DateTime(2026, 8, 21),
      updatedAt: DateTime(2026, 8, 21),
    );
    _sources.add(source);
    return source;
  }

  @override
  Future<AuthResultData> beginAuth(String sourceId) async =>
      const AuthResultData(state: 'not_required', message: '');

  @override
  Future<AuthResultData> fetchAuthStatus(String sourceId) async =>
      const AuthResultData(state: 'not_required', message: '');

  @override
  Future<CampusJob> fetchJob(String jobId) async => const CampusJob(
    id: 'job-1',
    status: 'succeeded',
    attempts: 1,
    maxAttempts: 3,
  );

  @override
  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  }) async => const AuthResultData(state: 'ready', message: '');

  @override
  Future<CampusJob> syncSource(String sourceId) async => const CampusJob(
    id: 'job-1',
    status: 'succeeded',
    attempts: 1,
    maxAttempts: 3,
  );

  @override
  void close() {}
}
