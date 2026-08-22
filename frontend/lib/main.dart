// Initializes platform services before launching the shared Flutter client.

import 'package:campus_ai_client/app.dart';
import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/services/push_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Starts Campus AI after registering platform-required background services.
void main() {
  // Background FCM registration must happen before the widget tree starts.
  WidgetsFlutterBinding.ensureInitialized();
  if (AppConfig.enableFcm && defaultTargetPlatform == TargetPlatform.android) {
    PushService.registerBackgroundHandler();
  }
  runApp(const ProviderScope(child: CampusAiApp()));
}
