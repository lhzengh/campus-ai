// Defines application routing, Material themes, localization, and navigation.

import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/features/inbox/inbox_page.dart';
import 'package:campus_ai_client/features/inbox/message_detail_page.dart';
import 'package:campus_ai_client/features/settings/settings_page.dart';
import 'package:campus_ai_client/features/sources/source_create_page.dart';
import 'package:campus_ai_client/features/sources/source_page.dart';
import 'package:campus_ai_client/services/push_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

final appRouter = GoRouter(
  routes: [
    ShellRoute(
      builder: (context, state, child) => AppShell(child: child),
      routes: [
        GoRoute(
          path: '/',
          pageBuilder: (context, state) =>
              _topLevelPage(state: state, child: const InboxPage()),
        ),
        GoRoute(
          path: '/messages/:id',
          pageBuilder: (context, state) => _detailPage(
            state: state,
            child: MessageDetailPage(messageId: state.pathParameters['id']!),
          ),
        ),
        GoRoute(
          path: '/sources',
          pageBuilder: (context, state) =>
              _topLevelPage(state: state, child: const SourcePage()),
        ),
        GoRoute(
          path: '/sources/new/:connectorId',
          pageBuilder: (context, state) => _detailPage(
            state: state,
            child: SourceCreatePage(
              connectorId: state.pathParameters['connectorId']!,
            ),
          ),
        ),
        GoRoute(
          path: '/sources/:sourceId/edit',
          pageBuilder: (context, state) => _detailPage(
            state: state,
            child: SourceCreatePage(
              sourceId: state.pathParameters['sourceId']!,
            ),
          ),
        ),
        GoRoute(
          path: '/settings',
          pageBuilder: (context, state) =>
              _topLevelPage(state: state, child: const SettingsPage()),
        ),
      ],
    ),
  ],
);

const _forwardTransitionDuration = Duration(milliseconds: 280);
const _reverseTransitionDuration = Duration(milliseconds: 240);

/// Keeps primary destinations stable while a deeper page pushes them aside.
CustomTransitionPage<void> _topLevelPage({
  required GoRouterState state,
  required Widget child,
}) => CustomTransitionPage<void>(
  key: state.pageKey,
  transitionDuration: _forwardTransitionDuration,
  reverseTransitionDuration: _reverseTransitionDuration,
  child: _RouteSurface(child: child),
  transitionsBuilder: (context, animation, secondaryAnimation, child) {
    return SlideTransition(
      position: _outgoingSlide(secondaryAnimation),
      child: child,
    );
  },
);

/// Slides detail and editing pages in from the trailing edge of their parent.
CustomTransitionPage<void> _detailPage({
  required GoRouterState state,
  required Widget child,
}) => CustomTransitionPage<void>(
  key: state.pageKey,
  transitionDuration: _forwardTransitionDuration,
  reverseTransitionDuration: _reverseTransitionDuration,
  child: _RouteSurface(child: child),
  transitionsBuilder: (context, animation, secondaryAnimation, child) {
    return SlideTransition(
      position: _outgoingSlide(secondaryAnimation),
      child: SlideTransition(position: _incomingSlide(animation), child: child),
    );
  },
);

Animation<Offset> _incomingSlide(Animation<double> animation) =>
    Tween<Offset>(begin: const Offset(1, 0), end: Offset.zero).animate(
      CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );

Animation<Offset> _outgoingSlide(Animation<double> animation) =>
    Tween<Offset>(begin: Offset.zero, end: const Offset(-1, 0)).animate(
      CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );

/// Paints an opaque surface so the previous route cannot bleed through.
class _RouteSurface extends StatelessWidget {
  const _RouteSurface({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: Theme.of(context).scaffoldBackgroundColor,
    child: child,
  );
}

/// Root Material application shared by desktop and Android builds.
class CampusAiApp extends ConsumerWidget {
  const CampusAiApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(pushStatusProvider);
    return MaterialApp.router(
      onGenerateTitle: (_) => 'Campus AI',
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        CampusStrings.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: CampusStrings.supportedLocales,
      localeResolutionCallback: (locale, supportedLocales) {
        if (locale?.languageCode == 'zh') return const Locale('zh');
        return const Locale('en');
      },
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF006B5F),
          brightness: Brightness.light,
        ),
        cardTheme: const CardThemeData(
          clipBehavior: Clip.antiAlias,
          margin: EdgeInsets.zero,
        ),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF57DBC8),
          brightness: Brightness.dark,
        ),
      ),
      themeMode: ThemeMode.system,
      routerConfig: appRouter,
    );
  }
}

/// Responsive top-level navigation shell for the primary destinations.
class AppShell extends StatelessWidget {
  const AppShell({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final path = GoRouterState.of(context).uri.path;
    final selectedIndex = path.startsWith('/sources')
        ? 1
        : path == '/settings'
        ? 2
        : 0;
    final title = switch (selectedIndex) {
      1 => context.strings.sourcesTitle,
      2 => context.strings.settingsTitle,
      _ => context.strings.inboxTitle,
    };

    void navigate(int index) => context.go(switch (index) {
      1 => '/sources',
      2 => '/settings',
      _ => '/',
    });

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= 720) {
          return Scaffold(
            appBar: AppBar(title: Text(title)),
            body: Row(
              children: [
                NavigationRail(
                  selectedIndex: selectedIndex,
                  onDestinationSelected: navigate,
                  labelType: NavigationRailLabelType.all,
                  destinations: [
                    NavigationRailDestination(
                      icon: const Icon(Icons.inbox_outlined),
                      selectedIcon: const Icon(Icons.inbox),
                      label: Text(context.strings.inbox),
                    ),
                    NavigationRailDestination(
                      icon: const Icon(Icons.hub_outlined),
                      selectedIcon: const Icon(Icons.hub),
                      label: Text(context.strings.sources),
                    ),
                    NavigationRailDestination(
                      icon: const Icon(Icons.settings_outlined),
                      selectedIcon: const Icon(Icons.settings),
                      label: Text(context.strings.settings),
                    ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: child),
              ],
            ),
          );
        }

        return Scaffold(
          appBar: AppBar(title: Text(title)),
          body: child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: selectedIndex,
            onDestinationSelected: navigate,
            destinations: [
              NavigationDestination(
                icon: const Icon(Icons.inbox_outlined),
                selectedIcon: const Icon(Icons.inbox),
                label: context.strings.inbox,
              ),
              NavigationDestination(
                icon: const Icon(Icons.hub_outlined),
                selectedIcon: const Icon(Icons.hub),
                label: context.strings.sources,
              ),
              NavigationDestination(
                icon: const Icon(Icons.settings_outlined),
                selectedIcon: const Icon(Icons.settings),
                label: context.strings.settings,
              ),
            ],
          ),
        );
      },
    );
  }
}
