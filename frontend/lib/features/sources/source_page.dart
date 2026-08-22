// Presents configured sources, Connector choices, authentication, and job actions.

import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/features/sources/source_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

/// Primary destination for managing institution-independent source instances.
class SourcePage extends ConsumerWidget {
  const SourcePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(sourceControllerProvider);
    return value.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => _SourceError(
        error: error,
        onRetry: ref.read(sourceControllerProvider.notifier).refresh,
      ),
      data: (state) => RefreshIndicator(
        onRefresh: ref.read(sourceControllerProvider.notifier).refresh,
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              sliver: SliverToBoxAdapter(
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        context.strings.sourcesTitle,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                    ),
                    FilterChip(
                      selected: state.showArchived,
                      label: Text(context.strings.showArchived),
                      onSelected: ref
                          .read(sourceControllerProvider.notifier)
                          .setShowArchived,
                    ),
                    const SizedBox(width: 8),
                    FilledButton.icon(
                      onPressed: () => _chooseConnector(context, state),
                      icon: const Icon(Icons.add),
                      label: Text(context.strings.addSource),
                    ),
                  ],
                ),
              ),
            ),
            if (state.sources.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _EmptySources(
                  onAdd: () => _chooseConnector(context, state),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                sliver: SliverList.separated(
                  itemCount: state.sources.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final source = state.sources[index];
                    return _SourceCard(
                      source: source,
                      connector: state.connector(source.connectorId),
                      auth: state.authResults[source.id],
                      job: state.jobs[source.id],
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _chooseConnector(
    BuildContext context,
    SourceManagementState state,
  ) async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => _ConnectorPicker(connectors: state.connectors),
    );
    if (selected != null && context.mounted) {
      context.push('/sources/new/${Uri.encodeComponent(selected)}');
    }
  }
}

class _SourceCard extends ConsumerWidget {
  const _SourceCard({
    required this.source,
    required this.connector,
    required this.auth,
    required this.job,
  });

  final SourceInstance source;
  final ConnectorRegistration? connector;
  final AuthResultData? auth;
  final CampusJob? job;

  bool get _jobBusy => job != null && !job!.isTerminal;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final manifest = connector?.manifest;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  child: Icon(
                    manifest?.requiresBrowser == true
                        ? Icons.language
                        : Icons.rss_feed,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        source.name,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(manifest?.displayName ?? source.connectorId),
                    ],
                  ),
                ),
                _StatusChip(
                  icon: source.isArchived
                      ? Icons.archive_outlined
                      : _authIcon(source.authStatus),
                  label: source.isArchived
                      ? context.strings.archived
                      : context.strings.authState(source.authStatus),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              context.strings.sourceSchedule(
                source.schedule.mode,
                source.schedule.time,
                source.schedule.timezone,
              ),
            ),
            if (source.nextRunAt case final nextRun?) ...[
              const SizedBox(height: 4),
              Text(context.strings.nextRunAt(_formatDate(nextRun))),
            ],
            const SizedBox(height: 6),
            Material(
              type: MaterialType.transparency,
              child: SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  source.enabled
                      ? context.strings.enabled
                      : context.strings.disabled,
                ),
                value: source.enabled,
                onChanged: source.isArchived
                    ? null
                    : (value) => _setEnabled(context, ref, value),
              ),
            ),
            Text(
              source.lastSuccessAt == null
                  ? context.strings.neverSynced
                  : context.strings.lastSynced(
                      _formatDate(source.lastSuccessAt!),
                    ),
            ),
            if (source.lastError case final error?) ...[
              const SizedBox(height: 6),
              Text(
                error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            if (auth?.message.isNotEmpty == true) ...[
              const SizedBox(height: 6),
              Text(auth!.message),
            ],
            if (job != null) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  if (_jobBusy)
                    const Padding(
                      padding: EdgeInsets.only(right: 8),
                      child: SizedBox.square(
                        dimension: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    ),
                  Text(context.strings.jobState(job!.status)),
                  if (job!.lastError case final error?)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Text(
                          error,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              if (job!.isTerminal && job!.result.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  context.strings.jobResult(_jobSummary(job!)),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
            const SizedBox(height: 12),
            if (source.isArchived)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: () => _restore(context, ref),
                  icon: const Icon(Icons.unarchive_outlined),
                  label: Text(context.strings.restore),
                ),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.end,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _checkConnection(context, ref),
                    icon: const Icon(Icons.cable_outlined),
                    label: Text(context.strings.connectionCheck),
                  ),
                  if (manifest?.supportsUserAssistedAuth == true)
                    OutlinedButton.icon(
                      onPressed: () => _beginAuth(context, ref),
                      icon: const Icon(Icons.login),
                      label: Text(context.strings.beginAuth),
                    ),
                  OutlinedButton.icon(
                    onPressed: _jobBusy || !source.enabled
                        ? null
                        : () => _preview(context, ref),
                    icon: const Icon(Icons.preview_outlined),
                    label: Text(context.strings.preview),
                  ),
                  FilledButton.icon(
                    onPressed: _jobBusy || !source.enabled
                        ? null
                        : () => _sync(context, ref),
                    icon: const Icon(Icons.sync),
                    label: Text(context.strings.manualSync),
                  ),
                  PopupMenuButton<String>(
                    tooltip: MaterialLocalizations.of(context)
                        .moreButtonTooltip,
                    onSelected: (value) => _menuAction(context, ref, value),
                    itemBuilder: (context) => [
                      PopupMenuItem(
                        value: 'edit',
                        child: ListTile(
                          leading: const Icon(Icons.edit_outlined),
                          title: Text(context.strings.editSource),
                        ),
                      ),
                      PopupMenuItem(
                        value: 'archive',
                        child: ListTile(
                          leading: const Icon(Icons.archive_outlined),
                          title: Text(context.strings.archive),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _checkConnection(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(sourceControllerProvider.notifier).checkSource(source.id);
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(context.strings.connectionReady)));
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _setEnabled(
    BuildContext context,
    WidgetRef ref,
    bool enabled,
  ) async {
    try {
      await ref
          .read(sourceControllerProvider.notifier)
          .updateSource(sourceId: source.id, enabled: enabled);
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _preview(BuildContext context, WidgetRef ref) async {
    try {
      final job = await ref
          .read(sourceControllerProvider.notifier)
          .previewSource(source.id);
      if (!context.mounted) return;
      if (job.status == 'failed') {
        throw StateError(job.lastError ?? context.strings.failed);
      }
      await showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (context) => _PreviewSheet(job: job),
      );
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _menuAction(
    BuildContext context,
    WidgetRef ref,
    String value,
  ) async {
    if (value == 'edit') {
      context.push('/sources/${Uri.encodeComponent(source.id)}/edit');
      return;
    }
    if (value != 'archive') return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.strings.archiveSource),
        content: Text(context.strings.archiveSourceHint),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.strings.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.strings.archive),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      await ref
          .read(sourceControllerProvider.notifier)
          .archiveSource(source.id);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(context.strings.sourceArchived)));
      }
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _restore(BuildContext context, WidgetRef ref) async {
    try {
      await ref
          .read(sourceControllerProvider.notifier)
          .restoreSource(source.id);
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(context.strings.sourceRestored)));
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _beginAuth(BuildContext context, WidgetRef ref) async {
    try {
      final result = await ref
          .read(sourceControllerProvider.notifier)
          .beginAuth(source.id);
      if (!context.mounted) return;
      final challenge = result.challenge;
      if (challenge == null) {
        _showResult(context, result);
        return;
      }
      final response = await showDialog<Map<String, String>>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AuthChallengeDialog(challenge: challenge),
      );
      if (response == null || !context.mounted) return;
      final completed = await ref
          .read(sourceControllerProvider.notifier)
          .submitAuthResponse(
            sourceId: source.id,
            challengeId: challenge.challengeId,
            response: response,
          );
      if (context.mounted) _showResult(context, completed);
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  Future<void> _sync(BuildContext context, WidgetRef ref) async {
    try {
      final result = await ref
          .read(sourceControllerProvider.notifier)
          .syncSource(source.id);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.strings.jobState(result.status))),
      );
    } catch (error) {
      if (context.mounted) _showError(context, error);
    }
  }

  void _showResult(BuildContext context, AuthResultData result) {
    final message = result.message.isNotEmpty
        ? result.message
        : context.strings.authState(result.state);
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  void _showError(BuildContext context, Object error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(context.strings.operationFailed(error))),
    );
  }
}

class _ConnectorPicker extends StatelessWidget {
  const _ConnectorPicker({required this.connectors});

  final List<ConnectorRegistration> connectors;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: 560),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 12),
              child: Text(
                context.strings.chooseConnector,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            Expanded(
              child: connectors.isEmpty
                  ? Center(child: Text(context.strings.noConnectors))
                  : ListView.builder(
                      itemCount: connectors.length,
                      itemBuilder: (context, index) {
                        final connector = connectors[index];
                        final manifest = connector.manifest;
                        return ListTile(
                          enabled: connector.isAvailable,
                          leading: Icon(
                            manifest?.requiresBrowser == true
                                ? Icons.language
                                : Icons.extension_outlined,
                          ),
                          title: Text(
                            manifest?.displayName ?? connector.connectorId,
                          ),
                          subtitle: Text(
                            connector.isAvailable
                                ? manifest!.description
                                : connector.error ??
                                      (connector.status == 'incompatible'
                                          ? context
                                                .strings
                                                .connectorIncompatible
                                          : context
                                                .strings
                                                .connectorUnavailable),
                          ),
                          trailing: connector.isAvailable
                              ? const Icon(Icons.chevron_right)
                              : const Icon(Icons.error_outline),
                          onTap: connector.isAvailable
                              ? () => Navigator.pop(
                                  context,
                                  connector.connectorId,
                                )
                              : null,
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PreviewSheet extends StatelessWidget {
  const _PreviewSheet({required this.job});

  final CampusJob job;

  @override
  Widget build(BuildContext context) {
    final rawItems = job.result['items'];
    final items = rawItems is List
        ? rawItems.whereType<Map>().toList(growable: false)
        : const <Map>[];
    return SafeArea(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: 680),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                context.strings.previewTitle,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              if (items.isEmpty)
                Expanded(
                  child: Center(child: Text(context.strings.noPreviewItems)),
                )
              else
                Expanded(
                  child: ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, _) => const Divider(),
                    itemBuilder: (context, index) {
                      final item = items[index];
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(item['title']?.toString() ?? ''),
                        subtitle: Text(
                          item['content_text']?.toString() ?? '',
                          maxLines: 4,
                          overflow: TextOverflow.ellipsis,
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Dynamic dialog that renders fields supplied by a Connector challenge.
class AuthChallengeDialog extends StatefulWidget {
  const AuthChallengeDialog({required this.challenge, super.key});

  final AuthChallengeData challenge;

  @override
  State<AuthChallengeDialog> createState() => _AuthChallengeDialogState();
}

class _AuthChallengeDialogState extends State<AuthChallengeDialog> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, bool> _booleans = {};

  @override
  void initState() {
    super.initState();
    for (final field in widget.challenge.fields) {
      if (field.inputType == 'boolean') {
        _booleans[field.name] = false;
      } else {
        _controllers[field.name] = TextEditingController();
      }
    }
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final loginUrl = _safeExternalUrl(widget.challenge.metadata['login_url']);
    return AlertDialog(
      title: Text(widget.challenge.title),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.challenge.instructions.isNotEmpty)
                  Text(widget.challenge.instructions),
                if (loginUrl != null) ...[
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => launchUrl(
                      loginUrl,
                      mode: LaunchMode.externalApplication,
                    ),
                    icon: const Icon(Icons.open_in_new),
                    label: Text(context.strings.openLoginPage),
                  ),
                ],
                for (final field in widget.challenge.fields) ...[
                  const SizedBox(height: 12),
                  if (field.inputType == 'boolean')
                    FormField<bool>(
                      initialValue: false,
                      validator: (value) => field.required && value != true
                          ? context.strings.requiredField(field.label)
                          : null,
                      builder: (formField) => CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(field.label),
                        value: formField.value ?? false,
                        onChanged: (value) {
                          final normalized = value ?? false;
                          formField.didChange(normalized);
                          _booleans[field.name] = normalized;
                        },
                      ),
                    )
                  else
                    TextFormField(
                      controller: _controllers[field.name],
                      obscureText:
                          field.secret || field.inputType == 'password',
                      keyboardType: field.inputType == 'sms_code'
                          ? TextInputType.number
                          : TextInputType.text,
                      decoration: InputDecoration(
                        labelText: field.label,
                        border: const OutlineInputBorder(),
                      ),
                      validator: (value) =>
                          field.required && (value == null || value.isEmpty)
                          ? context.strings.requiredField(field.label)
                          : null,
                    ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(context.strings.cancel),
        ),
        FilledButton(onPressed: _submit, child: Text(context.strings.submit)),
      ],
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    Navigator.pop(context, {
      for (final field in widget.challenge.fields)
        field.name: field.inputType == 'boolean'
            ? (_booleans[field.name] == true).toString()
            : _controllers[field.name]!.text,
    });
  }
}

class _EmptySources extends StatelessWidget {
  const _EmptySources({required this.onAdd});

  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.hub_outlined,
            size: 72,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(height: 20),
          Text(
            context.strings.noSources,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(context.strings.noSourcesHint, textAlign: TextAlign.center),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: onAdd,
            icon: const Icon(Icons.add),
            label: Text(context.strings.addSource),
          ),
        ],
      ),
    ),
  );
}

class _SourceError extends StatelessWidget {
  const _SourceError({required this.error, required this.onRetry});

  final Object error;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_outlined, size: 56),
          const SizedBox(height: 16),
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

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Chip(
    avatar: Icon(icon, size: 18),
    label: Text(label),
    visualDensity: VisualDensity.compact,
  );
}

IconData _authIcon(String status) => switch (status) {
  'ready' || 'not_required' => Icons.verified_outlined,
  'waiting_for_user' => Icons.person_outline,
  'auth_required' || 'expired' => Icons.warning_amber_outlined,
  _ => Icons.help_outline,
};

String _formatDate(DateTime value) {
  final local = value.toLocal();
  String twoDigits(int part) => part.toString().padLeft(2, '0');
  return '${local.year}-${twoDigits(local.month)}-${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}

String _jobSummary(CampusJob job) {
  final result = job.result;
  final parts = <String>[];
  for (final key in ['items_seen', 'created', 'updated', 'unchanged']) {
    if (result[key] != null) parts.add('$key=${result[key]}');
  }
  if (job.durationMs != null) parts.add('duration_ms=${job.durationMs}');
  return parts.isEmpty ? job.kind : parts.join(' · ');
}

Uri? _safeExternalUrl(Object? value) {
  if (value is! String) return null;
  final uri = Uri.tryParse(value);
  if (uri == null ||
      !uri.hasAuthority ||
      (uri.scheme != 'http' && uri.scheme != 'https') ||
      uri.userInfo.isNotEmpty) {
    return null;
  }
  return uri;
}
