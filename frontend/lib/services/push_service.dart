// Initializes optional Android FCM support and reports diagnostic state.

import 'dart:convert';

import 'package:campus_ai_client/core/app_config.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final pushStatusProvider = FutureProvider<PushStatus>(
  (ref) => PushService().initialize(),
);

/// Presentation-neutral result of checking push notification readiness.
class PushStatus {
  const PushStatus({required this.kind, this.detail = '', this.token});

  /// Stable status code translated only by the presentation layer.
  final String kind;
  final String detail;
  final String? token;
}

/// Android-only Firebase Messaging lifecycle used by the diagnostics UI.
class PushService {
  static bool _listenersRegistered = false;

  /// Registers the Android background entry point before the app starts.
  static void registerBackgroundHandler() {
    FirebaseMessaging.onBackgroundMessage(_backgroundMessageHandler);
  }

  /// Initializes FCM when supported and returns a diagnostic result.
  Future<PushStatus> initialize() async {
    if (defaultTargetPlatform != TargetPlatform.android) {
      return const PushStatus(kind: 'unsupported_platform');
    }
    if (!AppConfig.enableFcm) {
      return const PushStatus(kind: 'disabled');
    }
    final options = AppConfig.firebaseOptions;
    if (options == null) {
      return const PushStatus(kind: 'incomplete');
    }

    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp(options: options);
      }
      final messaging = FirebaseMessaging.instance;
      final permission = await messaging.requestPermission();
      final token = await messaging.getToken();
      // Process-wide listeners are registered once even if Riverpod rebuilds.
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
        kind: token == null ? 'missing_token' : 'ready',
        detail: permission.authorizationStatus.name,
        token: token,
      );
    } catch (error) {
      return PushStatus(kind: 'failed', detail: error.toString());
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
