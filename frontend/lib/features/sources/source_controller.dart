import 'dart:async';

import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/data/source_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final sourceStoreProvider = Provider<SourceStore>((ref) {
  final store = ApiSourceStore(CampusApi(baseUrl: AppConfig.apiBaseUrl));
  ref.onDispose(store.close);
  return store;
});

final sourceControllerProvider =
    StateNotifierProvider.autoDispose<
      SourceController,
      AsyncValue<SourceManagementState>
    >((ref) => SourceController(ref.watch(sourceStoreProvider))..refresh());

class SourceManagementState {
  const SourceManagementState({
    required this.connectors,
    required this.sources,
    this.authResults = const {},
    this.jobs = const {},
  });

  final List<ConnectorRegistration> connectors;
  final List<SourceInstance> sources;
  final Map<String, AuthResultData> authResults;
  final Map<String, CampusJob> jobs;

  ConnectorRegistration? connector(String connectorId) {
    for (final connector in connectors) {
      if (connector.connectorId == connectorId) return connector;
    }
    return null;
  }

  SourceManagementState copyWith({
    List<ConnectorRegistration>? connectors,
    List<SourceInstance>? sources,
    Map<String, AuthResultData>? authResults,
    Map<String, CampusJob>? jobs,
  }) => SourceManagementState(
    connectors: connectors ?? this.connectors,
    sources: sources ?? this.sources,
    authResults: authResults ?? this.authResults,
    jobs: jobs ?? this.jobs,
  );
}

class SourceController
    extends StateNotifier<AsyncValue<SourceManagementState>> {
  SourceController(this._store) : super(const AsyncLoading());

  final SourceStore _store;

  Future<void> refresh() async {
    final previous = state.valueOrNull;
    if (previous == null) state = const AsyncLoading();
    try {
      final results = await Future.wait<Object>([
        _store.fetchConnectors(),
        _store.fetchSources(),
      ]);
      state = AsyncData(
        SourceManagementState(
          connectors: results[0] as List<ConnectorRegistration>,
          sources: results[1] as List<SourceInstance>,
          authResults: previous?.authResults ?? const {},
          jobs: previous?.jobs ?? const {},
        ),
      );
    } catch (error, stack) {
      state = AsyncError(error, stack);
    }
  }

  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
  }) async {
    final created = await _store.createSource(
      name: name,
      connectorId: connectorId,
      config: config,
    );
    final current = state.requireValue;
    state = AsyncData(current.copyWith(sources: [...current.sources, created]));
    return created;
  }

  Future<AuthResultData> checkAuth(String sourceId) async {
    final result = await _store.fetchAuthStatus(sourceId);
    _recordAuth(sourceId, result);
    return result;
  }

  Future<AuthResultData> beginAuth(String sourceId) async {
    final result = await _store.beginAuth(sourceId);
    _recordAuth(sourceId, result);
    return result;
  }

  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  }) async {
    final result = await _store.submitAuthResponse(
      sourceId: sourceId,
      challengeId: challengeId,
      response: response,
    );
    _recordAuth(sourceId, result);
    return result;
  }

  Future<CampusJob> syncSource(String sourceId) async {
    final job = await _store.syncSource(sourceId);
    _recordJob(sourceId, job);
    if (!job.isTerminal) unawaited(_pollJob(sourceId, job.id));
    return job;
  }

  void _recordAuth(String sourceId, AuthResultData result) {
    final current = state.requireValue;
    state = AsyncData(
      current.copyWith(
        authResults: {...current.authResults, sourceId: result},
        sources: [
          for (final source in current.sources)
            source.id == sourceId
                ? source.copyWith(authStatus: result.state)
                : source,
        ],
      ),
    );
  }

  void _recordJob(String sourceId, CampusJob job) {
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData(current.copyWith(jobs: {...current.jobs, sourceId: job}));
  }

  Future<void> _pollJob(String sourceId, String jobId) async {
    for (var attempt = 0; attempt < 60 && mounted; attempt++) {
      await Future<void>.delayed(const Duration(seconds: 1));
      if (!mounted) return;
      try {
        final job = await _store.fetchJob(jobId);
        _recordJob(sourceId, job);
        if (job.isTerminal) {
          await refresh();
          return;
        }
      } catch (_) {
        // A manual refresh remains available if a transient poll fails.
      }
    }
  }
}
