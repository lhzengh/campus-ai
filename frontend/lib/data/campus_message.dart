class CampusMessage {
  const CampusMessage({
    required this.id,
    required this.sourceId,
    required this.url,
    required this.title,
    required this.body,
    required this.fetchedAt,
    this.publishedAt,
    this.metadata = const {},
    this.isRead = false,
  });

  final String id;
  final String sourceId;
  final String url;
  final String title;
  final String body;
  final DateTime? publishedAt;
  final DateTime fetchedAt;
  final Map<String, Object?> metadata;
  final bool isRead;

  factory CampusMessage.fromJson(Map<String, Object?> json) {
    final rawMetadata = json['metadata_json'];
    return CampusMessage(
      id: json['id']! as String,
      sourceId: json['source_id']! as String,
      url: json['url']! as String,
      title: json['title']! as String,
      body: json['body']! as String,
      publishedAt: _parseDate(json['published_at']),
      fetchedAt: _parseDate(json['fetched_at']) ?? DateTime.now().toUtc(),
      metadata: rawMetadata is Map
          ? rawMetadata.map((key, value) => MapEntry(key.toString(), value))
          : const {},
    );
  }

  CampusMessage copyWith({bool? isRead}) => CampusMessage(
    id: id,
    sourceId: sourceId,
    url: url,
    title: title,
    body: body,
    publishedAt: publishedAt,
    fetchedAt: fetchedAt,
    metadata: metadata,
    isRead: isRead ?? this.isRead,
  );

  static DateTime? _parseDate(Object? value) {
    if (value is! String || value.isEmpty) return null;
    return DateTime.tryParse(value)?.toLocal();
  }
}
