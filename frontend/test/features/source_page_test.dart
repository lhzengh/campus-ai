import 'package:campus_ai_client/app.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/data/source_repository.dart';
import 'package:campus_ai_client/features/sources/source_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('creates a source from a Connector schema', (tester) async {
    tester.view.physicalSize = const Size(800, 1400);
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
    await tester.enterText(fields.at(2), 'https://example.test/notices');
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

  testWidgets('edits an existing source with its current configuration', (
    tester,
  ) async {
    await _setLargeTestView(tester);
    appRouter.go('/sources');
    final store = _FakeSourceStore()..seedSource();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sourceStoreProvider.overrideWithValue(store)],
        child: const CampusAiApp(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(PopupMenuButton<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit source'));
    await tester.pumpAndSettle();

    expect(find.text('Edit source'), findsWidgets);
    final fields = find.byType(EditableText);
    expect(
      (tester.widget<EditableText>(fields.at(2))).controller.text,
      'https://example.test/notices',
    );
    await tester.enterText(fields.at(0), 'Updated notices');
    final saveButton = find.widgetWithText(FilledButton, 'Save');
    await tester.ensureVisible(saveButton);
    await tester.tap(saveButton);
    await tester.pumpAndSettle();

    expect(find.text('Updated notices'), findsOneWidget);
    expect(store.sources.single.name, 'Updated notices');
  });

  testWidgets('archives and restores a source without deleting it', (
    tester,
  ) async {
    await _setLargeTestView(tester);
    appRouter.go('/sources');
    final store = _FakeSourceStore()..seedSource();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sourceStoreProvider.overrideWithValue(store)],
        child: const CampusAiApp(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(PopupMenuButton<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Archive'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Archive'));
    await tester.pumpAndSettle();
    expect(find.text('No sources configured'), findsOneWidget);

    await tester.tap(find.text('Show archived'));
    await tester.pumpAndSettle();
    expect(find.text('Archived'), findsOneWidget);
    await tester.tap(find.text('Restore'));
    await tester.pumpAndSettle();

    expect(store.sources.single.isArchived, isFalse);
    expect(store.sources.single.enabled, isFalse);
    expect(find.text('Disabled'), findsOneWidget);
  });
}

Future<void> _setLargeTestView(WidgetTester tester) async {
  tester.view.physicalSize = const Size(800, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

class _FakeSourceStore implements SourceStore {
  final List<SourceInstance> _sources = [];
  JsonMap? createdConfig;

  List<SourceInstance> get sources => List.unmodifiable(_sources);

  void seedSource() {
    _sources.add(
      SourceInstance(
        id: 'source-1',
        name: 'Public notices',
        connectorId: 'example.static',
        connectorVersion: '1.0.0',
        enabled: true,
        config: const {
          'url': 'https://example.test/notices',
          'interval': 0.5,
          'enabled': false,
        },
        schedule: SourceScheduleData.dailyDefault,
        authStatus: 'not_required',
        createdAt: DateTime(2026, 8, 21),
        updatedAt: DateTime(2026, 8, 21),
      ),
    );
  }

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
  Future<List<SourceInstance>> fetchSources({
    bool includeArchived = false,
  }) async => List.of(
    _sources.where((source) => includeArchived || !source.isArchived),
  );

  @override
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
    required SourceScheduleData schedule,
  }) async {
    createdConfig = config;
    final source = SourceInstance(
      id: 'source-1',
      name: name,
      connectorId: connectorId,
      connectorVersion: '1.0.0',
      enabled: true,
      config: config,
      schedule: schedule,
      authStatus: 'not_required',
      createdAt: DateTime(2026, 8, 21),
      updatedAt: DateTime(2026, 8, 21),
    );
    _sources.add(source);
    return source;
  }

  @override
  Future<SourceInstance> updateSource({
    required String sourceId,
    String? name,
    JsonMap? config,
    bool? enabled,
    SourceScheduleData? schedule,
  }) async {
    final old = _sources.singleWhere((source) => source.id == sourceId);
    final updated = SourceInstance(
      id: old.id,
      name: name ?? old.name,
      connectorId: old.connectorId,
      connectorVersion: old.connectorVersion,
      enabled: enabled ?? old.enabled,
      config: config ?? old.config,
      schedule: schedule ?? old.schedule,
      authStatus: old.authStatus,
      createdAt: old.createdAt,
      updatedAt: DateTime(2026, 8, 22),
    );
    _sources[_sources.indexOf(old)] = updated;
    return updated;
  }

  @override
  Future<void> archiveSource(String sourceId) async {
    final old = _sources.singleWhere((source) => source.id == sourceId);
    _sources[_sources.indexOf(old)] = _copySource(
      old,
      enabled: false,
      archivedAt: DateTime(2026, 8, 22),
    );
  }

  @override
  Future<SourceInstance> restoreSource(String sourceId) async {
    final old = _sources.singleWhere((source) => source.id == sourceId);
    final restored = _copySource(old, enabled: false, clearArchived: true);
    _sources[_sources.indexOf(old)] = restored;
    return restored;
  }

  @override
  Future<SourceCheckData> checkSource(String sourceId) async => SourceCheckData(
    connectorStatus: 'available',
    configStatus: 'valid',
    authStatus: 'not_required',
    checkedAt: DateTime(2026, 8, 21),
  );

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
  Future<CampusJob> previewSource(String sourceId) async => const CampusJob(
    id: 'preview-1',
    status: 'succeeded',
    attempts: 1,
    maxAttempts: 2,
    kind: 'preview_source',
    result: {'items': <Object>[]},
  );

  @override
  void close() {}

  static SourceInstance _copySource(
    SourceInstance old, {
    bool? enabled,
    DateTime? archivedAt,
    bool clearArchived = false,
  }) => SourceInstance(
    id: old.id,
    name: old.name,
    connectorId: old.connectorId,
    connectorVersion: old.connectorVersion,
    enabled: enabled ?? old.enabled,
    config: old.config,
    schedule: old.schedule,
    authStatus: old.authStatus,
    lastSuccessAt: old.lastSuccessAt,
    lastError: old.lastError,
    nextRunAt: old.nextRunAt,
    archivedAt: clearArchived ? null : archivedAt ?? old.archivedAt,
    createdAt: old.createdAt,
    updatedAt: DateTime(2026, 8, 22),
  );
}
