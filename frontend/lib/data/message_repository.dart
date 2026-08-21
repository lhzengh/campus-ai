import 'package:campus_ai_client/data/app_database.dart';
import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/campus_message.dart';

abstract interface class MessageStore {
  Stream<List<CampusMessage>> watchMessages();
  Stream<CampusMessage?> watchMessage(String id);
  Future<void> refresh();
  Future<void> markRead(String id);
}

class MessageRepository implements MessageStore {
  MessageRepository(this._database, this._api);

  final AppDatabase _database;
  final CampusApi _api;

  @override
  Stream<List<CampusMessage>> watchMessages() => _database.watchMessages();

  @override
  Stream<CampusMessage?> watchMessage(String id) => _database.watchMessage(id);

  @override
  Future<void> refresh() async {
    final messages = await _api.fetchMessages();
    await _database.upsertMessages(messages);
  }

  @override
  Future<void> markRead(String id) => _database.markRead(id);

  void close() => _api.close();
}
