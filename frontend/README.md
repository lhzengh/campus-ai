# Campus AI Client

The Campus AI client is a Flutter Material 3 application for Linux, Windows, and Android. It communicates only with the versioned Core Client API; institution-specific authentication and collection remain behind Core and Connector boundaries.

## Supported capabilities

- Browse normalized campus messages and message details.
- Manage Connector-backed source instances.
- Start source checks, authentication challenges, previews, and synchronization jobs.
- Poll durable job status without keeping the original request open.
- Cache messages locally with Drift/SQLite.
- Use English as the compatibility fallback and Simplified Chinese as an optional locale.
- Receive push notifications when a supported transport is configured.

## Run locally

Start Core first, then provide its URL at build time:

```bash
cd frontend
flutter pub get
flutter run -d linux \
  --dart-define=CAMPUS_AI_API_URL=http://127.0.0.1:8000
```

For an Android emulator, use `http://10.0.2.2:8000` to reach a Core service running on the host. A physical device must use an address reachable from that device.

## Optional Firebase configuration

Firebase is disabled unless explicitly enabled. Copy `firebase-config.example.json` to the ignored `firebase-config.json`, replace every placeholder locally, and pass the values through the project build configuration.

Never commit a real Firebase configuration, service account, device token, API key, portal credential, cookie, or verification code.

## Validation

```bash
cd frontend
flutter analyze
flutter test
```

The repository-level `make test` command also runs the supported client validation when Flutter is available.
