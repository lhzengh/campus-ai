import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/campus_message.dart';
import 'package:campus_ai_client/features/inbox/inbox_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class InboxPage extends ConsumerStatefulWidget {
  const InboxPage({super.key});

  @override
  ConsumerState<InboxPage> createState() => _InboxPageState();
}

class _InboxPageState extends ConsumerState<InboxPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(ref.read(inboxControllerProvider.notifier).refresh);
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(inboxMessagesProvider);
    final syncState = ref.watch(inboxControllerProvider);

    ref.listen(inboxControllerProvider, (previous, next) {
      if (next.hasError && previous?.error != next.error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.strings.inboxSyncFailed(next.error!))),
        );
      }
    });

    return Column(
      children: [
        if (syncState.isLoading) const LinearProgressIndicator(),
        Expanded(
          child: messages.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => _ErrorState(
              error: error,
              onRetry: ref.read(inboxControllerProvider.notifier).refresh,
            ),
            data: (items) => RefreshIndicator(
              onRefresh: ref.read(inboxControllerProvider.notifier).refresh,
              child: items.isEmpty
                  ? const _EmptyState()
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: items.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (context, index) =>
                          _MessageCard(message: items[index]),
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({required this.message});

  final CampusMessage message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Icon(
          message.isRead ? Icons.mark_email_read_outlined : Icons.circle,
          size: message.isRead ? 24 : 12,
          color: message.isRead
              ? Theme.of(context).colorScheme.onSurfaceVariant
              : Theme.of(context).colorScheme.primary,
        ),
        title: Text(
          message.title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: message.isRead
              ? null
              : const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(
            '${message.sourceId} · ${_formatDate(message.publishedAt ?? message.fetchedAt)}',
          ),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/messages/${message.id}'),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 80),
        Icon(
          Icons.mark_email_read_outlined,
          size: 72,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(height: 20),
        Text(
          context.strings.emptyInbox,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        Text(context.strings.emptyInboxHint, textAlign: TextAlign.center),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});

  final Object error;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 56),
            const SizedBox(height: 16),
            Text(
              context.strings.localInboxFailed(error),
              textAlign: TextAlign.center,
            ),
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
}

String _formatDate(DateTime value) {
  final local = value.toLocal();
  String twoDigits(int part) => part.toString().padLeft(2, '0');
  return '${local.year}-${twoDigits(local.month)}-${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}
