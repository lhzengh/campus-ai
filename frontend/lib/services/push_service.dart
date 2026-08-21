import 'dart:convert';

import 'package:campus_ai_client/core/app_config.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final pushStatusProvider = FutureProvider<PushStatus>(
  (ref) => PushService().initialize(),
);

class PushStatus {
  const PushStatus({required this.title, required this.detail, this.token});

  final String title;
  final String detail;
  final String? token;
}

class PushService {
  static bool _listenersRegistered = false;

  static void registerBackgroundHandler() {
    FirebaseMessaging.onBackgroundMessage(_backgroundMessageHandler);
  }

  Future<PushStatus> initialize() async {
    if (defaultTargetPlatform != TargetPlatform.android) {
      return const PushStatus(
        title: '当前平台不使用 FCM',
        detail: 'Linux 与 Windows 客户端保留应用内同步；FCM 仅在 Android 启用。',
      );
    }
    if (!AppConfig.enableFcm) {
      return const PushStatus(
        title: 'FCM 未启用',
        detail: '使用 ENABLE_FCM 和 Firebase 的四项 Dart Define 启动应用后再检查。',
      );
    }
    final options = AppConfig.firebaseOptions;
    if (options == null) {
      return const PushStatus(
        title: 'FCM 配置不完整',
        detail: '缺少 API Key、App ID、Project ID 或 Messaging Sender ID。',
      );
    }

    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp(options: options);
      }
      final messaging = FirebaseMessaging.instance;
      final permission = await messaging.requestPermission();
      final token = await messaging.getToken();
      if (!_listenersRegistered) {
        FirebaseMessaging.onMessage.listen(_logReceivedMessage);
        FirebaseMessaging.onMessageOpenedApp.listen(_logReceivedMessage);
        final initialMessage = await messaging.getInitialMessage();
        if (initialMessage != null) {
          _logReceivedMessage(initialMessage);
        }
        _listenersRegistered = true;
      }
      return PushStatus(
        title: token == null ? '未取得 FCM Token' : 'FCM 已就绪',
        detail: '通知权限：${permission.authorizationStatus.name}',
        token: token,
      );
    } catch (error) {
      return PushStatus(title: 'FCM 初始化失败', detail: error.toString());
    }
  }
}

@pragma('vm:entry-point')
Future<void> _backgroundMessageHandler(RemoteMessage message) async {
  final options = AppConfig.firebaseOptions;
  if (options != null && Firebase.apps.isEmpty) {
    await Firebase.initializeApp(options: options);
  }
  _logReceivedMessage(message);
}

void _logReceivedMessage(RemoteMessage message) {
  debugPrint(
    'CAMPUS_AI_FCM_RECEIVED ${jsonEncode({'message_id': message.messageId, 'event_key': message.data['event_key'], 'run_id': message.data['run_id'], 'sequence': message.data['sequence'], 'sent_at': message.data['sent_at'] ?? message.sentTime?.toUtc().toIso8601String(), 'received_at': DateTime.now().toUtc().toIso8601String()})}',
  );
}
