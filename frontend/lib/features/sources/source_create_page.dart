// Creates and edits sources using each Connector's runtime configuration schema.

import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/features/sources/schema_form.dart';
import 'package:campus_ai_client/features/sources/source_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Creates or edits a source while keeping Connector configuration schema-driven.
class SourceCreatePage extends ConsumerStatefulWidget {
  const SourceCreatePage({this.connectorId, this.sourceId, super.key})
    : assert(connectorId != null || sourceId != null);

  final String? connectorId;
  final String? sourceId;

  @override
  ConsumerState<SourceCreatePage> createState() => _SourceCreatePageState();
}

class _SourceCreatePageState extends ConsumerState<SourceCreatePage> {
  final _nameController = TextEditingController();
  final _timezoneController = TextEditingController(text: 'Asia/Shanghai');
  final _nameFormKey = GlobalKey<FormState>();
  final _scheduleFormKey = GlobalKey<FormState>();
  final _configFormKey = GlobalKey<FormState>();
  JsonMap _config = const {};
  JsonMap _initialConfig = const {};
  String _scheduleMode = 'daily';
  TimeOfDay _scheduleTime = const TimeOfDay(hour: 7, minute: 0);
  bool _enabled = true;
  bool _initialized = false;
  bool _submitting = false;

  bool get _editing => widget.sourceId != null;

  @override
  void dispose() {
    _nameController.dispose();
    _timezoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final sourceState = ref.watch(sourceControllerProvider);
    return sourceState.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => _LoadError(
        error: error,
        onRetry: ref.read(sourceControllerProvider.notifier).refresh,
      ),
      data: (state) {
        final source = _findSource(state.sources, widget.sourceId);
        if (_editing && source == null) return _missingSource(context);
        final connectorId = source?.connectorId ?? widget.connectorId!;
        final registration = state.connector(connectorId);
        final manifest = registration?.manifest;
        if (registration == null ||
            !registration.isAvailable ||
            manifest == null) {
          return _missingSource(context);
        }
        _initialize(source);
        return _buildForm(context, manifest, source);
      },
    );
  }

  SourceInstance? _findSource(List<SourceInstance> sources, String? id) {
    if (id == null) return null;
    for (final source in sources) {
      if (source.id == id) return source;
    }
    return null;
  }

  void _initialize(SourceInstance? source) {
    if (_initialized) return;
    _initialized = true;
    if (source == null) return;
    _nameController.text = source.name;
    _config = source.config;
    _initialConfig = source.config;
    _scheduleMode = source.schedule.mode;
    _scheduleTime = _parseTime(source.schedule.time);
    _timezoneController.text = source.schedule.timezone;
    _enabled = source.enabled;
  }

  Widget _missingSource(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.extension_off_outlined, size: 56),
          const SizedBox(height: 16),
          Text(context.strings.sourceNotFound),
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () => _backToSources(context),
            child: Text(context.strings.sources),
          ),
        ],
      ),
    ),
  );

  Widget _buildForm(
    BuildContext context,
    ConnectorManifestData manifest,
    SourceInstance? source,
  ) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: _submitting ? null : () => _backToSources(context),
            icon: const Icon(Icons.arrow_back),
            label: Text(context.strings.sources),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          _editing ? context.strings.editSource : context.strings.createSource,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 8),
        Text(
          '${manifest.displayName} · ${manifest.version}',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (manifest.description.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(manifest.description),
        ],
        const SizedBox(height: 24),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Form(
                key: _nameFormKey,
                child: TextFormField(
                  controller: _nameController,
                  autofocus: !_editing,
                  decoration: InputDecoration(
                    labelText: '${context.strings.sourceName} *',
                    hintText: context.strings.sourceNameHint,
                    border: const OutlineInputBorder(),
                  ),
                  maxLength: 200,
                  validator: (value) => value == null || value.trim().isEmpty
                      ? context.strings.requiredName
                      : null,
                ),
              ),
              Material(
                type: MaterialType.transparency,
                child: SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(context.strings.sourceEnabled),
                  subtitle: Text(context.strings.sourceEnabledHint),
                  value: _enabled,
                  onChanged: (value) => setState(() => _enabled = value),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                context.strings.collectionSchedule,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _scheduleMode,
                decoration: InputDecoration(
                  labelText: context.strings.scheduleMode,
                  border: const OutlineInputBorder(),
                ),
                items: [
                  DropdownMenuItem(
                    value: 'manual',
                    child: Text(context.strings.manualOnly),
                  ),
                  DropdownMenuItem(
                    value: 'daily',
                    child: Text(context.strings.daily),
                  ),
                ],
                onChanged: (value) =>
                    setState(() => _scheduleMode = value ?? 'manual'),
              ),
              if (_scheduleMode == 'daily') ...[
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: _chooseTime,
                  icon: const Icon(Icons.schedule),
                  label: Text(
                    '${context.strings.dailyTime}: ${_formatTime(_scheduleTime)}',
                  ),
                ),
                const SizedBox(height: 12),
                Form(
                  key: _scheduleFormKey,
                  child: TextFormField(
                    controller: _timezoneController,
                    decoration: InputDecoration(
                      labelText: context.strings.timezone,
                      helperText: context.strings.timezoneHint,
                      border: const OutlineInputBorder(),
                    ),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? context.strings.requiredField(
                            context.strings.timezone,
                          )
                        : null,
                  ),
                ),
              ],
              const SizedBox(height: 20),
              Text(
                context.strings.connectorConfiguration,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              DynamicConfigForm(
                schema: manifest.configSchema,
                initialValues: _initialConfig,
                formKey: _configFormKey,
                onChanged: (value) => _config = value,
              ),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _submitting ? null : () => _submit(manifest, source),
                icon: _submitting
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(_editing ? Icons.save_outlined : Icons.add),
                label: Text(
                  _editing
                      ? context.strings.save
                      : context.strings.createSource,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _chooseTime() async {
    final value = await showTimePicker(
      context: context,
      initialTime: _scheduleTime,
    );
    if (value != null && mounted) setState(() => _scheduleTime = value);
  }

  Future<void> _submit(
    ConnectorManifestData manifest,
    SourceInstance? source,
  ) async {
    final nameValid = _nameFormKey.currentState?.validate() ?? false;
    final scheduleValid =
        _scheduleMode == 'manual' ||
        (_scheduleFormKey.currentState?.validate() ?? false);
    final configValid = _configFormKey.currentState?.validate() ?? false;
    if (!nameValid || !scheduleValid || !configValid) return;
    setState(() => _submitting = true);
    final schedule = SourceScheduleData(
      mode: _scheduleMode,
      time: _formatTime(_scheduleTime),
      timezone: _timezoneController.text.trim(),
    );
    try {
      final controller = ref.read(sourceControllerProvider.notifier);
      if (source == null) {
        await controller.createSource(
          name: _nameController.text.trim(),
          connectorId: manifest.connectorId,
          config: _config,
          schedule: schedule,
        );
      } else {
        await controller.updateSource(
          sourceId: source.id,
          name: _nameController.text.trim(),
          config: _config,
          enabled: _enabled,
          schedule: schedule,
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _editing
                ? context.strings.sourceSaved
                : context.strings.sourceCreated,
          ),
        ),
      );
      _backToSources(context);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.strings.operationFailed(error))),
      );
      setState(() => _submitting = false);
    }
  }

  static TimeOfDay _parseTime(String value) {
    final parts = value.split(':');
    return TimeOfDay(
      hour: int.tryParse(parts.first) ?? 7,
      minute: parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0,
    );
  }

  static String _formatTime(TimeOfDay value) =>
      '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';

  void _backToSources(BuildContext context) {
    // A directly opened create/edit URL has no parent entry to pop.
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/sources');
    }
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.error, required this.onRetry});

  final Object error;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(context.strings.operationFailed(error)),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: Text(context.strings.retry),
          ),
        ],
      ),
    ),
  );
}
