import 'package:campus_ai_client/app.dart';
import 'package:campus_ai_client/core/app_config.dart';
import 'package:campus_ai_client/services/push_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  if (AppConfig.enableFcm && defaultTargetPlatform == TargetPlatform.android) {
    PushService.registerBackgroundHandler();
  }
  runApp(const ProviderScope(child: CampusAiApp()));
}
