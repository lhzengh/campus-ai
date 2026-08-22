// Shows deployment, cloud AI, and push-notification diagnostics.

import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/services/push_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Read-only diagnostics and privacy-boundary destination.
class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final push = ref.watch(pushStatusProvider);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _SectionCard(
          title: context.strings.server,
          icon: Icons.dns_outlined,
          children: [
            ListTile(
              title: Text(context.strings.apiAddress),
              subtitle: SelectableText(AppConfig.apiBaseUrl),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _SectionCard(
          title: context.strings.androidPush,
          icon: Icons.notifications_active_outlined,
          children: [
            push.when(
              loading: () => ListTile(
                leading: const CircularProgressIndicator(),
                title: Text(context.strings.checkingFcm),
              ),
              error: (error, stack) => ListTile(
                title: Text(context.strings.fcmCheckFailed),
                subtitle: Text(error.toString()),
              ),
              data: (status) => Column(
                children: [
                  ListTile(
                    title: Text(context.strings.pushTitle(status.kind)),
                    subtitle: Text(
                      context.strings.pushDetail(status.kind, status.detail),
                    ),
                    trailing: IconButton(
                      tooltip: context.strings.refresh,
                      onPressed: () => ref.invalidate(pushStatusProvider),
                      icon: const Icon(Icons.refresh),
                    ),
                  ),
                  if (status.token case final token?)
                    ListTile(
                      title: Text(context.strings.deviceToken),
                      subtitle: SelectableText(token),
                      trailing: IconButton(
                        tooltip: context.strings.copyToken,
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: token));
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(context.strings.tokenCopied),
                              ),
                            );
                          }
                        },
                        icon: const Icon(Icons.copy),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _SectionCard(
          title: context.strings.privacyBoundary,
          icon: Icons.shield_outlined,
          children: [
            ListTile(
              title: Text(context.strings.cloudAi),
              subtitle: Text(context.strings.cloudAiDetail),
            ),
            ListTile(
              title: Text('MCP'),
              subtitle: Text(context.strings.mcpDetail),
            ),
          ],
        ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.children,
  });

  final String title;
  final IconData icon;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Row(
                children: [
                  Icon(icon),
                  const SizedBox(width: 10),
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
            ),
            ...children,
          ],
        ),
      ),
    );
  }
}
