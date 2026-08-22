// Adapts the Core API to a replaceable source-management data boundary.

import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/source_models.dart';

/// Testable boundary between the source-management UI and the Client API.
abstract interface class SourceStore {
  /// Loads Connector registrations known to Core.
  Future<List<ConnectorRegistration>> fetchConnectors();

  /// Loads source instances with an optional archive view.
  Future<List<SourceInstance>> fetchSources({bool includeArchived = false});

  /// Creates a configured source instance.
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
    required SourceScheduleData schedule,
  });

  /// Applies editable source fields without changing Connector identity.
  Future<SourceInstance> updateSource({
    required String sourceId,
    String? name,
    JsonMap? config,
    bool? enabled,
    SourceScheduleData? schedule,
  });

  /// Archives a source while retaining its history.
  Future<void> archiveSource(String sourceId);

  /// Restores a previously archived source.
  Future<SourceInstance> restoreSource(String sourceId);

  /// Checks source readiness without collecting content.
  Future<SourceCheckData> checkSource(String sourceId);

  /// Loads the current Connector-owned authentication state.
  Future<AuthResultData> fetchAuthStatus(String sourceId);

  /// Begins user-assisted authentication when supported.
  Future<AuthResultData> beginAuth(String sourceId);

  /// Submits a response to the active authentication challenge.
  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  });

  /// Enqueues an incremental source synchronization.
  Future<CampusJob> syncSource(String sourceId);

  /// Enqueues a non-persisting source preview.
  Future<CampusJob> previewSource(String sourceId);

  /// Loads the latest durable job state.
  Future<CampusJob> fetchJob(String jobId);

  /// Releases resources owned by the store.
  void close();
}

/// Production SourceStore backed by the Core HTTP API.
class ApiSourceStore implements SourceStore {
  ApiSourceStore(this._api);

  final CampusApi _api;

  @override
  Future<List<ConnectorRegistration>> fetchConnectors() =>
      _api.fetchConnectors();

  @override
  Future<List<SourceInstance>> fetchSources({bool includeArchived = false}) =>
      _api.fetchSources(includeArchived: includeArchived);

  @override
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
    required SourceScheduleData schedule,
  }) => _api.createSource(
    name: name,
    connectorId: connectorId,
    config: config,
    schedule: schedule,
  );

  @override
  Future<SourceInstance> updateSource({
    required String sourceId,
    String? name,
    JsonMap? config,
    bool? enabled,
    SourceScheduleData? schedule,
  }) => _api.updateSource(
    sourceId: sourceId,
    name: name,
    config: config,
    enabled: enabled,
    schedule: schedule,
  );

  @override
  Future<void> archiveSource(String sourceId) => _api.archiveSource(sourceId);

  @override
  Future<SourceInstance> restoreSource(String sourceId) =>
      _api.restoreSource(sourceId);

  @override
  Future<SourceCheckData> checkSource(String sourceId) =>
      _api.checkSource(sourceId);

  @override
  Future<AuthResultData> fetchAuthStatus(String sourceId) =>
      _api.fetchAuthStatus(sourceId);

  @override
  Future<AuthResultData> beginAuth(String sourceId) => _api.beginAuth(sourceId);

  @override
  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  }) => _api.submitAuthResponse(
    sourceId: sourceId,
    challengeId: challengeId,
    response: response,
  );

  @override
  Future<CampusJob> syncSource(String sourceId) => _api.syncSource(sourceId);

  @override
  Future<CampusJob> previewSource(String sourceId) =>
      _api.previewSource(sourceId);

  @override
  Future<CampusJob> fetchJob(String jobId) => _api.fetchJob(jobId);

  @override
  void close() => _api.close();
}
