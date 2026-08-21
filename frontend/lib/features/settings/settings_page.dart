import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/services/push_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final push = ref.watch(pushStatusProvider);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _SectionCard(
          title: '服务端',
          icon: Icons.dns_outlined,
          children: [
            ListTile(
              title: const Text('API 地址'),
              subtitle: SelectableText(AppConfig.apiBaseUrl),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _SectionCard(
          title: 'Android 推送',
          icon: Icons.notifications_active_outlined,
          children: [
            push.when(
              loading: () => const ListTile(
                leading: CircularProgressIndicator(),
                title: Text('检查 FCM 配置…'),
              ),
              error: (error, stack) => ListTile(
                title: const Text('FCM 检查失败'),
                subtitle: Text(error.toString()),
              ),
              data: (status) => Column(
                children: [
                  ListTile(
                    title: Text(status.title),
                    subtitle: Text(status.detail),
                    trailing: IconButton(
                      tooltip: '重新检查',
                      onPressed: () => ref.invalidate(pushStatusProvider),
                      icon: const Icon(Icons.refresh),
                    ),
                  ),
                  if (status.token case final token?)
                    ListTile(
                      title: const Text('设备 Token'),
                      subtitle: SelectableText(token),
                      trailing: IconButton(
                        tooltip: '复制 Token',
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: token));
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Token 已复制')),
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
        const _SectionCard(
          title: '隐私边界',
          icon: Icons.shield_outlined,
          children: [
            ListTile(
              title: Text('云端 AI'),
              subtitle: Text('由服务端通过 OpenAI 兼容 API 调用；客户端不保存模型密钥。'),
            ),
            ListTile(
              title: Text('MCP'),
              subtitle: Text('当前不承担模型推理，仅为未来受限工具接入预留。'),
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
