import 'dart:convert';
import 'dart:io';

import 'package:campus_ai_client/data/campus_message.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

part 'app_database.g.dart';

class CachedMessages extends Table {
  TextColumn get id => text()();
  TextColumn get sourceId => text()();
  TextColumn get url => text()();
  TextColumn get title => text()();
  TextColumn get body => text()();
  DateTimeColumn get publishedAt => dateTime().nullable()();
  DateTimeColumn get fetchedAt => dateTime()();
  TextColumn get metadataJson => text().withDefault(const Constant('{}'))();
  BoolColumn get isRead => boolean().withDefault(const Constant(false))();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

@DriftDatabase(tables: [CachedMessages])
class AppDatabase extends _$AppDatabase {
  AppDatabase([QueryExecutor? executor]) : super(executor ?? _openConnection());

  @override
  int get schemaVersion => 1;

  Stream<List<CampusMessage>> watchMessages() {
    final query = select(cachedMessages)
      ..orderBy([
        (row) =>
            OrderingTerm(expression: row.publishedAt, mode: OrderingMode.desc),
        (row) =>
            OrderingTerm(expression: row.fetchedAt, mode: OrderingMode.desc),
      ]);
    return query.watch().map(
      (rows) => rows.map(_toDomain).toList(growable: false),
    );
  }

  Stream<CampusMessage?> watchMessage(String id) {
    final query = select(cachedMessages)..where((row) => row.id.equals(id));
    return query.watchSingleOrNull().map(
      (row) => row == null ? null : _toDomain(row),
    );
  }

  Future<void> upsertMessages(Iterable<CampusMessage> messages) async {
    final readRows = await (select(
      cachedMessages,
    )..where((row) => row.isRead.equals(true))).get();
    final readIds = readRows.map((row) => row.id).toSet();
    await batch((batch) {
      batch.insertAllOnConflictUpdate(
        cachedMessages,
        messages
            .map(
              (message) => CachedMessagesCompanion.insert(
                id: message.id,
                sourceId: message.sourceId,
                url: message.url,
                title: message.title,
                body: message.body,
                publishedAt: Value(message.publishedAt),
                fetchedAt: message.fetchedAt,
                metadataJson: Value(jsonEncode(message.metadata)),
                isRead: Value(readIds.contains(message.id) || message.isRead),
              ),
            )
            .toList(growable: false),
      );
    });
  }

  Future<void> markRead(String id) {
    return (update(cachedMessages)..where((row) => row.id.equals(id))).write(
      const CachedMessagesCompanion(isRead: Value(true)),
    );
  }

  CampusMessage _toDomain(CachedMessage row) {
    Map<String, Object?> metadata = const {};
    try {
      final decoded = jsonDecode(row.metadataJson);
      if (decoded is Map) {
        metadata = decoded.map((key, value) => MapEntry(key.toString(), value));
      }
    } on FormatException {
      // A corrupt optional metadata field must not hide the actual message.
    }
    return CampusMessage(
      id: row.id,
      sourceId: row.sourceId,
      url: row.url,
      title: row.title,
      body: row.body,
      publishedAt: row.publishedAt,
      fetchedAt: row.fetchedAt,
      metadata: metadata,
      isRead: row.isRead,
    );
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final directory = await getApplicationSupportDirectory();
    final file = File(p.join(directory.path, 'campus_ai.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
