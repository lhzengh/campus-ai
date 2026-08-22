// Defines client-side models for Connectors, sources, authentication, and jobs.

/// JSON object shape shared by the source-management data layer.
typedef JsonMap = Map<String, Object?>;

/// A user-facing collection schedule that remains independent of Flutter UI types.
class SourceScheduleData {
  const SourceScheduleData({
    required this.mode,
    required this.time,
    required this.timezone,
  });

  static const dailyDefault = SourceScheduleData(
    mode: 'daily',
    time: '07:00',
    timezone: 'Asia/Shanghai',
  );

  final String mode;
  final String time;
  final String timezone;

  bool get isDaily => mode == 'daily';

  JsonMap toJson() => {'mode': mode, 'time': time, 'timezone': timezone};

  factory SourceScheduleData.fromJson(JsonMap json) => SourceScheduleData(
    mode: json['mode'] as String? ?? 'manual',
    time: _shortTime(json['time'] as String? ?? '07:00'),
    timezone: json['timezone'] as String? ?? 'Asia/Shanghai',
  );
}

/// A Connector advertised by Core together with its current availability.
class ConnectorRegistration {
  const ConnectorRegistration({
    required this.connectorId,
    required this.status,
    this.manifest,
    this.error,
  });

  final String connectorId;
  final String status;
  final ConnectorManifestData? manifest;
  final String? error;

  bool get isAvailable => status == 'available' && manifest != null;

  factory ConnectorRegistration.fromJson(JsonMap json) {
    final rawManifest = json['manifest'];
    return ConnectorRegistration(
      connectorId: json['connector_id']! as String,
      status: json['status']! as String,
      manifest: rawManifest is Map
          ? ConnectorManifestData.fromJson(_stringMap(rawManifest))
          : null,
      error: json['error'] as String?,
    );
  }
}

/// The public Connector metadata used to build source configuration screens.
class ConnectorManifestData {
  const ConnectorManifestData({
    required this.connectorId,
    required this.version,
    required this.displayName,
    required this.description,
    required this.capabilities,
    required this.configSchema,
    required this.requiresBrowser,
  });

  final String connectorId;
  final String version;
  final String displayName;
  final String description;
  final Set<String> capabilities;
  final JsonMap configSchema;
  final bool requiresBrowser;

  bool get supportsUserAssistedAuth =>
      capabilities.contains('user_assisted_auth');

  factory ConnectorManifestData.fromJson(JsonMap json) => ConnectorManifestData(
    connectorId: json['connector_id']! as String,
    version: json['version']! as String,
    displayName: json['display_name']! as String,
    description: json['description'] as String? ?? '',
    capabilities: ((json['capabilities'] as List?) ?? const [])
        .map((value) => value.toString())
        .toSet(),
    configSchema: _stringMap(json['config_schema']! as Map),
    requiresBrowser: json['requires_browser'] as bool? ?? false,
  );
}

/// One user-configured source instance owned by Core.
class SourceInstance {
  const SourceInstance({
    required this.id,
    required this.name,
    required this.connectorId,
    required this.enabled,
    required this.config,
    required this.schedule,
    required this.authStatus,
    required this.createdAt,
    required this.updatedAt,
    this.connectorVersion,
    this.lastSuccessAt,
    this.lastError,
    this.nextRunAt,
    this.archivedAt,
  });

  final String id;
  final String name;
  final String connectorId;
  final String? connectorVersion;
  final bool enabled;
  final JsonMap config;
  final SourceScheduleData schedule;
  final String authStatus;
  final DateTime? lastSuccessAt;
  final String? lastError;
  final DateTime? nextRunAt;
  final DateTime? archivedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isArchived => archivedAt != null;

  SourceInstance copyWith({String? authStatus}) => SourceInstance(
    id: id,
    name: name,
    connectorId: connectorId,
    connectorVersion: connectorVersion,
    enabled: enabled,
    config: config,
    schedule: schedule,
    authStatus: authStatus ?? this.authStatus,
    lastSuccessAt: lastSuccessAt,
    lastError: lastError,
    nextRunAt: nextRunAt,
    archivedAt: archivedAt,
    createdAt: createdAt,
    updatedAt: updatedAt,
  );

  factory SourceInstance.fromJson(JsonMap json) => SourceInstance(
    id: json['id']! as String,
    name: json['name']! as String,
    connectorId: json['connector_id']! as String,
    connectorVersion: json['connector_version'] as String?,
    enabled: json['enabled']! as bool,
    config: _stringMap(json['config']! as Map),
    schedule: json['schedule'] is Map
        ? SourceScheduleData.fromJson(_stringMap(json['schedule']! as Map))
        : SourceScheduleData.dailyDefault,
    authStatus: json['auth_status']! as String,
    lastSuccessAt: _date(json['last_success_at']),
    lastError: json['last_error'] as String?,
    nextRunAt: _date(json['next_run_at']),
    archivedAt: _date(json['archived_at']),
    createdAt: _date(json['created_at'])!,
    updatedAt: _date(json['updated_at'])!,
  );
}

/// A non-collecting source health check returned by Core.
class SourceCheckData {
  const SourceCheckData({
    required this.connectorStatus,
    required this.configStatus,
    required this.authStatus,
    required this.checkedAt,
  });

  final String connectorStatus;
  final String configStatus;
  final String authStatus;
  final DateTime checkedAt;

  factory SourceCheckData.fromJson(JsonMap json) => SourceCheckData(
    connectorStatus: json['connector_status']! as String,
    configStatus: json['config_status']! as String,
    authStatus: json['auth_status']! as String,
    checkedAt: _date(json['checked_at'])!,
  );
}

/// One dynamic input requested by a Connector authentication challenge.
class AuthChallengeFieldData {
  const AuthChallengeFieldData({
    required this.name,
    required this.label,
    required this.inputType,
    required this.secret,
    required this.required,
  });

  final String name;
  final String label;
  final String inputType;
  final bool secret;
  final bool required;

  factory AuthChallengeFieldData.fromJson(JsonMap json) =>
      AuthChallengeFieldData(
        name: json['name']! as String,
        label: json['label']! as String,
        inputType: json['input_type'] as String? ?? 'text',
        secret: json['secret'] as bool? ?? false,
        required: json['required'] as bool? ?? true,
      );
}

/// Provider-neutral authentication challenge rendered by the client.
class AuthChallengeData {
  const AuthChallengeData({
    required this.challengeId,
    required this.kind,
    required this.title,
    required this.instructions,
    required this.fields,
    required this.metadata,
    this.expiresAt,
  });

  final String challengeId;
  final String kind;
  final String title;
  final String instructions;
  final List<AuthChallengeFieldData> fields;
  final DateTime? expiresAt;
  final JsonMap metadata;

  factory AuthChallengeData.fromJson(JsonMap json) => AuthChallengeData(
    challengeId: json['challenge_id']! as String,
    kind: json['kind']! as String,
    title: json['title']! as String,
    instructions: json['instructions'] as String? ?? '',
    fields: ((json['fields'] as List?) ?? const [])
        .map(
          (value) => AuthChallengeFieldData.fromJson(_stringMap(value as Map)),
        )
        .toList(growable: false),
    expiresAt: _date(json['expires_at']),
    metadata: json['metadata'] is Map
        ? _stringMap(json['metadata']! as Map)
        : const {},
  );
}

/// Current source authentication state and optional active challenge.
class AuthResultData {
  const AuthResultData({
    required this.state,
    required this.message,
    this.challenge,
  });

  final String state;
  final String message;
  final AuthChallengeData? challenge;

  factory AuthResultData.fromJson(JsonMap json) {
    final rawChallenge = json['challenge'];
    return AuthResultData(
      state: json['state']! as String,
      message: json['message'] as String? ?? '',
      challenge: rawChallenge is Map
          ? AuthChallengeData.fromJson(_stringMap(rawChallenge))
          : null,
    );
  }
}

/// Asynchronous Core job status used for sync and preview feedback.
class CampusJob {
  const CampusJob({
    required this.id,
    required this.status,
    required this.attempts,
    required this.maxAttempts,
    this.kind = '',
    this.result = const {},
    this.startedAt,
    this.finishedAt,
    this.durationMs,
    this.lastError,
  });

  final String id;
  final String status;
  final int attempts;
  final int maxAttempts;
  final String kind;
  final JsonMap result;
  final DateTime? startedAt;
  final DateTime? finishedAt;
  final int? durationMs;
  final String? lastError;

  bool get isTerminal =>
      status == 'succeeded' || status == 'completed' || status == 'failed';

  factory CampusJob.fromJson(JsonMap json) => CampusJob(
    id: json['id']! as String,
    status: json['status']! as String,
    attempts: json['attempts']! as int,
    maxAttempts: json['max_attempts']! as int,
    kind: json['kind'] as String? ?? '',
    result: json['result'] is Map
        ? _stringMap(json['result']! as Map)
        : const {},
    startedAt: _date(json['started_at']),
    finishedAt: _date(json['finished_at']),
    durationMs: json['duration_ms'] as int?,
    lastError: json['last_error'] as String?,
  );
}

JsonMap _stringMap(Map<dynamic, dynamic> value) =>
    value.map((key, item) => MapEntry(key.toString(), item));

DateTime? _date(Object? value) {
  if (value is! String || value.isEmpty) return null;
  return DateTime.tryParse(value)?.toLocal();
}

String _shortTime(String value) =>
    value.length >= 5 ? value.substring(0, 5) : value;
