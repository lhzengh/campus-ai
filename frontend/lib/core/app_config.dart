import 'package:firebase_core/firebase_core.dart';

abstract final class AppConfig {
  static const apiBaseUrl = String.fromEnvironment('CAMPUS_AI_API_URL');

  static const enableFcm = bool.fromEnvironment(
    'ENABLE_FCM',
    defaultValue: false,
  );

  static const _firebaseApiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const _firebaseAppId = String.fromEnvironment('FIREBASE_APP_ID');
  static const _firebaseProjectId = String.fromEnvironment(
    'FIREBASE_PROJECT_ID',
  );
  static const _firebaseSenderId = String.fromEnvironment(
    'FIREBASE_MESSAGING_SENDER_ID',
  );

  static FirebaseOptions? get firebaseOptions {
    if (_firebaseApiKey.isEmpty ||
        _firebaseAppId.isEmpty ||
        _firebaseProjectId.isEmpty ||
        _firebaseSenderId.isEmpty) {
      return null;
    }
    return const FirebaseOptions(
      apiKey: _firebaseApiKey,
      appId: _firebaseAppId,
      messagingSenderId: _firebaseSenderId,
      projectId: _firebaseProjectId,
    );
  }
}
