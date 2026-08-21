import 'package:campus_ai_client/features/inbox/inbox_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

class MessageDetailPage extends ConsumerStatefulWidget {
  const MessageDetailPage({required this.messageId, super.key});

  final String messageId;

  @override
  ConsumerState<MessageDetailPage> createState() => _MessageDetailPageState();
}

class _MessageDetailPageState extends ConsumerState<MessageDetailPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(
      () =>
          ref.read(inboxControllerProvider.notifier).markRead(widget.messageId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final message = ref.watch(messageProvider(widget.messageId));
    return message.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('读取消息失败：$error')),
      data: (item) {
        if (item == null) {
          return const Center(child: Text('消息不存在或尚未同步'));
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: context.pop,
                icon: const Icon(Icons.arrow_back),
                label: const Text('返回消息列表'),
              ),
            ),
            const SizedBox(height: 8),
            Text(item.title, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                Chip(
                  avatar: const Icon(Icons.source_outlined, size: 18),
                  label: Text(item.sourceId),
                ),
                const Chip(
                  avatar: Icon(Icons.auto_awesome_outlined, size: 18),
                  label: Text('AI 分析待同步'),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text('原文信息', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            SelectableText(item.body),
            const SizedBox(height: 24),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                onPressed: () => launchUrl(
                  Uri.parse(item.url),
                  mode: LaunchMode.externalApplication,
                ),
                icon: const Icon(Icons.open_in_new),
                label: const Text('打开学校原文'),
              ),
            ),
          ],
        );
      },
    );
  }
}
