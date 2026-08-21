import 'package:campus_ai_client/data/app_database.dart';
import 'package:campus_ai_client/data/campus_message.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'caches messages and preserves local read state during refresh',
    () async {
      final database = AppDatabase(NativeDatabase.memory());
      addTearDown(database.close);
      final original = CampusMessage(
        id: 'message-1',
        sourceId: 'source-1',
        url: 'https://example.edu/1',
        title: '原始标题',
        body: '正文',
        publishedAt: DateTime.utc(2026, 8, 19),
        fetchedAt: DateTime.utc(2026, 8, 19, 1),
        metadata: const {'kind': 'notice'},
      );

      await database.upsertMessages([original]);
      await database.markRead(original.id);
      await database.upsertMessages([original.copyWith()]);

      final cached = await database.watchMessage(original.id).first;
      expect(cached, isNotNull);
      expect(cached!.title, '原始标题');
      expect(cached.isRead, isTrue);
      expect(cached.metadata['kind'], 'notice');
    },
  );
}
