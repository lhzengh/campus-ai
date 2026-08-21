import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:campus_ai_client/features/sources/source_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('renders and returns a provider-neutral auth challenge', (
    tester,
  ) async {
    Map<String, String>? response;
    const challenge = AuthChallengeData(
      challengeId: 'challenge-1',
      kind: 'sms_code',
      title: 'Verify sign-in',
      instructions: 'Enter the code sent to your phone.',
      fields: [
        AuthChallengeFieldData(
          name: 'password',
          label: 'Password',
          inputType: 'password',
          secret: true,
          required: true,
        ),
        AuthChallengeFieldData(
          name: 'code',
          label: 'SMS code',
          inputType: 'sms_code',
          secret: true,
          required: true,
        ),
        AuthChallengeFieldData(
          name: 'confirmed',
          label: 'I completed sign-in',
          inputType: 'boolean',
          secret: false,
          required: true,
        ),
      ],
      metadata: {},
    );

    await tester.pumpWidget(
      _localizedApp(
        Builder(
          builder: (context) => FilledButton(
            onPressed: () async {
              response = await showDialog<Map<String, String>>(
                context: context,
                builder: (_) => const AuthChallengeDialog(challenge: challenge),
              );
            },
            child: const Text('Open'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    final fields = find.byType(TextFormField);
    final editableFields = find.byType(EditableText);
    expect(
      tester.widget<EditableText>(editableFields.first).obscureText,
      isTrue,
    );
    await tester.enterText(fields.at(0), 'secret');
    await tester.enterText(fields.at(1), '123456');
    await tester.tap(find.byType(Checkbox));
    await tester.tap(find.text('Submit'));
    await tester.pumpAndSettle();

    expect(response, {
      'password': 'secret',
      'code': '123456',
      'confirmed': 'true',
    });
  });

  testWidgets('uses optional Chinese strings only for the presentation layer', (
    tester,
  ) async {
    await tester.pumpWidget(
      _localizedApp(
        Builder(builder: (context) => Text(context.strings.addSource)),
        locale: const Locale('zh'),
      ),
    );

    expect(find.text('添加来源'), findsOneWidget);
  });
}

MaterialApp _localizedApp(Widget home, {Locale locale = const Locale('en')}) =>
    MaterialApp(
      locale: locale,
      localizationsDelegates: const [
        CampusStrings.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: CampusStrings.supportedLocales,
      home: Scaffold(body: Center(child: home)),
    );
