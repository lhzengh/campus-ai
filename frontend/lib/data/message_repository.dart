// Coordinates Core synchronization with the device-local message cache.

import 'package:campus_ai_client/data/app_database.dart';
import 'package:campus_ai_client/data/campus_api.dart';
import 'package:campus_ai_client/data/campus_message.dart';

/// Testable inbox boundary consumed by controllers and widgets.
abstract interface class MessageStore {
  /// Watches all locally available messages.
  Stream<List<CampusMessage>> watchMessages();

  /// Watches one locally available message by identifier.
  Stream<CampusMessage?> watchMessage(String id);

  /// Refreshes the local cache from Core.
  Future<void> refresh();

  /// Persists device-local read state.
  Future<void> markRead(String id);
}

/// Repository that serves cached streams and refreshes them from Core.
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

  /// Releases network resources owned by this repository.
  void close() => _api.close();
}
