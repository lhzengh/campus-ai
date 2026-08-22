import 'package:campus_ai_client/app.dart';
import 'package:campus_ai_client/data/campus_message.dart';
import 'package:campus_ai_client/data/message_repository.dart';
import 'package:campus_ai_client/features/inbox/inbox_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows cached messages and opens message detail', (tester) async {
    appRouter.go('/');
    final store = _FakeMessageStore([
      CampusMessage(
        id: 'message-1',
        sourceId: '教务处',
        url: 'https://example.edu/notice/1',
        title: '选课确认通知',
        body: '请在本周五前完成确认。',
        publishedAt: DateTime(2026, 8, 19, 8),
        fetchedAt: DateTime(2026, 8, 19, 9),
      ),
    ]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [messageStoreProvider.overrideWithValue(store)],
        child: const CampusAiApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('选课确认通知'), findsOneWidget);
    expect(find.text('教务处 · 2026-08-19 08:00'), findsOneWidget);

    await tester.tap(find.text('选课确认通知'));
    await tester.pumpAndSettle();

    expect(find.text('Original content'), findsOneWidget);
    expect(find.text('请在本周五前完成确认。'), findsOneWidget);
    expect(store.readIds, contains('message-1'));

    await tester.tap(find.text('Back to inbox'));
    await tester.pumpAndSettle();

    expect(find.text('Campus inbox'), findsOneWidget);
    expect(find.text('Original content'), findsNothing);
  });

  testWidgets('back to inbox also works for a direct detail link', (
    tester,
  ) async {
    appRouter.go('/messages/message-1');
    final store = _FakeMessageStore([
      CampusMessage(
        id: 'message-1',
        sourceId: 'source-1',
        url: 'https://example.edu/notice/1',
        title: 'Direct message',
        body: 'Opened from a direct link.',
        fetchedAt: DateTime(2026, 8, 22, 9),
      ),
    ]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [messageStoreProvider.overrideWithValue(store)],
        child: const CampusAiApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Original content'), findsOneWidget);
    await tester.tap(find.text('Back to inbox'));
    await tester.pumpAndSettle();

    expect(find.text('Campus inbox'), findsOneWidget);
    expect(find.text('Original content'), findsNothing);
  });
}

class _FakeMessageStore implements MessageStore {
  _FakeMessageStore(this.messages);

  final List<CampusMessage> messages;
  final Set<String> readIds = {};

  @override
  Future<void> markRead(String id) async => readIds.add(id);

  @override
  Future<void> refresh() async {}

  @override
  Stream<CampusMessage?> watchMessage(String id) =>
      Stream.value(messages.where((message) => message.id == id).firstOrNull);

  @override
  Stream<List<CampusMessage>> watchMessages() => Stream.value(messages);
}
