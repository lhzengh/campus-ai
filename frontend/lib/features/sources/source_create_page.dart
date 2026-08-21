import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/features/sources/schema_form.dart';
import 'package:campus_ai_client/features/sources/source_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class SourceCreatePage extends ConsumerStatefulWidget {
  const SourceCreatePage({required this.connectorId, super.key});

  final String connectorId;

  @override
  ConsumerState<SourceCreatePage> createState() => _SourceCreatePageState();
}

class _SourceCreatePageState extends ConsumerState<SourceCreatePage> {
  final _nameController = TextEditingController();
  final _nameFormKey = GlobalKey<FormState>();
  final _configFormKey = GlobalKey<FormState>();
  JsonMap _config = const {};
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
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
        final registration = state.connector(widget.connectorId);
        final manifest = registration?.manifest;
        if (registration == null ||
            !registration.isAvailable ||
            manifest == null) {
          return Center(
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
                    onPressed: () => context.go('/sources'),
                    child: Text(context.strings.sources),
                  ),
                ],
              ),
            ),
          );
        }
        return _buildForm(context, manifest);
      },
    );
  }

  Widget _buildForm(BuildContext context, ConnectorManifestData manifest) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: _submitting ? null : () => context.go('/sources'),
            icon: const Icon(Icons.arrow_back),
            label: Text(context.strings.sources),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          context.strings.createSource,
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
                  autofocus: true,
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
              const SizedBox(height: 12),
              Text(
                context.strings.connectorConfiguration,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              DynamicConfigForm(
                schema: manifest.configSchema,
                formKey: _configFormKey,
                onChanged: (value) => _config = value,
              ),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _submitting ? null : () => _submit(manifest),
                icon: _submitting
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add),
                label: Text(context.strings.createSource),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _submit(ConnectorManifestData manifest) async {
    final nameValid = _nameFormKey.currentState?.validate() ?? false;
    final configValid = _configFormKey.currentState?.validate() ?? false;
    if (!nameValid || !configValid) return;
    setState(() => _submitting = true);
    try {
      await ref
          .read(sourceControllerProvider.notifier)
          .createSource(
            name: _nameController.text.trim(),
            connectorId: manifest.connectorId,
            config: _config,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(context.strings.sourceCreated)));
      context.go('/sources');
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.strings.operationFailed(error))),
      );
      setState(() => _submitting = false);
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
