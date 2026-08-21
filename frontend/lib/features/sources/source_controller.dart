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
    this.showArchived = false,
  });

  final List<ConnectorRegistration> connectors;
  final List<SourceInstance> sources;
  final Map<String, AuthResultData> authResults;
  final Map<String, CampusJob> jobs;
  final bool showArchived;

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
    bool? showArchived,
  }) => SourceManagementState(
    connectors: connectors ?? this.connectors,
    sources: sources ?? this.sources,
    authResults: authResults ?? this.authResults,
    jobs: jobs ?? this.jobs,
    showArchived: showArchived ?? this.showArchived,
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
        _store.fetchSources(includeArchived: previous?.showArchived ?? false),
      ]);
      state = AsyncData(
        SourceManagementState(
          connectors: results[0] as List<ConnectorRegistration>,
          sources: results[1] as List<SourceInstance>,
          authResults: previous?.authResults ?? const {},
          jobs: previous?.jobs ?? const {},
          showArchived: previous?.showArchived ?? false,
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
    required SourceScheduleData schedule,
  }) async {
    final created = await _store.createSource(
      name: name,
      connectorId: connectorId,
      config: config,
      schedule: schedule,
    );
    final current = state.requireValue;
    state = AsyncData(current.copyWith(sources: [...current.sources, created]));
    return created;
  }

  Future<SourceInstance> updateSource({
    required String sourceId,
    String? name,
    JsonMap? config,
    bool? enabled,
    SourceScheduleData? schedule,
  }) async {
    final updated = await _store.updateSource(
      sourceId: sourceId,
      name: name,
      config: config,
      enabled: enabled,
      schedule: schedule,
    );
    _replaceSource(updated);
    return updated;
  }

  Future<void> setShowArchived(bool value) async {
    final current = state.requireValue;
    state = AsyncData(current.copyWith(showArchived: value));
    try {
      final sources = await _store.fetchSources(includeArchived: value);
      final latest = state.valueOrNull;
      if (latest != null) {
        state = AsyncData(latest.copyWith(sources: sources));
      }
    } catch (error, stack) {
      state = AsyncError(error, stack);
    }
  }

  Future<void> archiveSource(String sourceId) async {
    await _store.archiveSource(sourceId);
    final current = state.requireValue;
    if (current.showArchived) {
      final sources = await _store.fetchSources(includeArchived: true);
      state = AsyncData(current.copyWith(sources: sources));
      return;
    }
    state = AsyncData(
      current.copyWith(
        sources: current.sources
            .where((source) => source.id != sourceId)
            .toList(),
      ),
    );
  }

  Future<SourceInstance> restoreSource(String sourceId) async {
    final restored = await _store.restoreSource(sourceId);
    _replaceSource(restored);
    return restored;
  }

  Future<SourceCheckData> checkSource(String sourceId) async {
    final result = await _store.checkSource(sourceId);
    _recordAuth(
      sourceId,
      AuthResultData(state: result.authStatus, message: ''),
    );
    return result;
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

  Future<CampusJob> previewSource(String sourceId) async {
    final job = await _store.previewSource(sourceId);
    _recordJob(sourceId, job);
    return job.isTerminal ? job : _waitForJob(sourceId, job.id);
  }

  void _replaceSource(SourceInstance updated) {
    final current = state.requireValue;
    state = AsyncData(
      current.copyWith(
        sources: [
          for (final source in current.sources)
            if (source.id == updated.id) updated else source,
        ],
      ),
    );
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
    try {
      await _waitForJob(sourceId, jobId, refreshWhenDone: true);
    } catch (_) {
      // Background polling must not surface an unhandled asynchronous error.
    }
  }

  Future<CampusJob> _waitForJob(
    String sourceId,
    String jobId, {
    bool refreshWhenDone = false,
  }) async {
    for (var attempt = 0; attempt < 60 && mounted; attempt++) {
      await Future<void>.delayed(const Duration(seconds: 1));
      if (!mounted) throw StateError('Source controller was disposed.');
      try {
        final job = await _store.fetchJob(jobId);
        _recordJob(sourceId, job);
        if (job.isTerminal) {
          if (refreshWhenDone) await refresh();
          return job;
        }
      } catch (_) {
        // A manual refresh remains available if a transient poll fails.
      }
    }
    throw TimeoutException('Core did not finish the job within 60 seconds.');
  }
}
