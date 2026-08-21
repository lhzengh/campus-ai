import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/source_models.dart';

/// Testable boundary between the source-management UI and the Client API.
abstract interface class SourceStore {
  Future<List<ConnectorRegistration>> fetchConnectors();
  Future<List<SourceInstance>> fetchSources();
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
  });
  Future<AuthResultData> fetchAuthStatus(String sourceId);
  Future<AuthResultData> beginAuth(String sourceId);
  Future<AuthResultData> submitAuthResponse({
    required String sourceId,
    required String challengeId,
    required Map<String, String> response,
  });
  Future<CampusJob> syncSource(String sourceId);
  Future<CampusJob> fetchJob(String jobId);
  void close();
}

class ApiSourceStore implements SourceStore {
  ApiSourceStore(this._api);

  final CampusApi _api;

  @override
  Future<List<ConnectorRegistration>> fetchConnectors() =>
      _api.fetchConnectors();

  @override
  Future<List<SourceInstance>> fetchSources() => _api.fetchSources();

  @override
  Future<SourceInstance> createSource({
    required String name,
    required String connectorId,
    required JsonMap config,
  }) => _api.createSource(name: name, connectorId: connectorId, config: config);

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
  Future<CampusJob> fetchJob(String jobId) => _api.fetchJob(jobId);

  @override
  void close() => _api.close();
}
