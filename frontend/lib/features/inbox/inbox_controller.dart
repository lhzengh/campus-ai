import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/data/app_database.dart';
import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/campus_message.dart';
import 'package:campus_ai_client/data/message_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final databaseProvider = Provider<AppDatabase>((ref) {
  final database = AppDatabase();
  ref.onDispose(database.close);
  return database;
});

final messageStoreProvider = Provider<MessageStore>((ref) {
  final repository = MessageRepository(
    ref.watch(databaseProvider),
    CampusApi(baseUrl: AppConfig.apiBaseUrl),
  );
  ref.onDispose(repository.close);
  return repository;
});

final inboxMessagesProvider = StreamProvider<List<CampusMessage>>(
  (ref) => ref.watch(messageStoreProvider).watchMessages(),
);

final messageProvider = StreamProvider.autoDispose
    .family<CampusMessage?, String>(
      (ref, id) => ref.watch(messageStoreProvider).watchMessage(id),
    );

final inboxControllerProvider =
    StateNotifierProvider<InboxController, AsyncValue<void>>(
      (ref) => InboxController(ref.watch(messageStoreProvider)),
    );

class InboxController extends StateNotifier<AsyncValue<void>> {
  InboxController(this._store) : super(const AsyncData(null));

  final MessageStore _store;

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(_store.refresh);
  }

  Future<void> markRead(String id) => _store.markRead(id);
}
