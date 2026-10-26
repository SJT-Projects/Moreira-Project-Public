import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';

import 'config/firebase_config.dart';
import 'screens/academia_screen.dart';
import 'screens/analizador_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/comunidad_screen.dart';
import 'services/auth_service.dart';
import 'theme/app_theme.dart';
import 'widgets/ui_calida.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  String? configurationError;

  final options = firebaseOptionsFromEnvironment();
  if (options == null) {
    // Sin opciones Firebase no se inicializa y FirebaseAuth.instance fallaría.
    configurationError = 'Faltan los datos de la aplicación web de Firebase.';
  } else {
    try {
      await Firebase.initializeApp(options: options);
    } catch (_) {
      configurationError =
          'Firebase no pudo iniciar. Confirmá la configuración de la aplicación web y Authentication.';
    }
  }

  runApp(AntiEstafasApp(configurationError: configurationError));
}

class AntiEstafasApp extends StatelessWidget {
  const AntiEstafasApp({super.key, this.configurationError});

  final String? configurationError;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Anti-Estafas',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: configurationError == null
          ? const AuthGate()
          : FirebaseSetupScreen(message: configurationError!),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: AuthService().userChanges,
      initialData: FirebaseAuth.instance.currentUser,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: CenteredMessage(emoji: '⏳', message: 'Cargando, un momento...'),
          );
        }
        return snapshot.data == null ? const AuthScreen() : const MainNavigationScreen();
      },
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  static const _screens = <Widget>[
    AnalizadorScreen(),
    ComunidadScreen(),
    AcademiaScreen(),
  ];

  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Emoji('🛡️', size: 30),
            SizedBox(width: 10),
            Flexible(child: Text('Moreira · Anti-Estafas')),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: TextButton.icon(
              style: TextButton.styleFrom(
                foregroundColor: Colors.white,
                textStyle: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              icon: const Icon(Icons.logout),
              label: const Text('Salir'),
              onPressed: () async {
                await AuthService().signOut();
              },
            ),
          ),
        ],
      ),
      body: IndexedStack(index: _selectedIndex, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Emoji('🔍', size: 30),
            label: 'Analizar',
            tooltip: 'Revisar un mensaje sospechoso',
          ),
          NavigationDestination(
            icon: Emoji('🤝', size: 30),
            label: 'Comunidad',
            tooltip: 'Alertas de otros vecinos',
          ),
          NavigationDestination(
            icon: Emoji('🎓', size: 30),
            label: 'Aprender',
            tooltip: 'Guías y preguntas para practicar',
          ),
        ],
      ),
    );
  }
}

class FirebaseSetupScreen extends StatelessWidget {
  const FirebaseSetupScreen({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Configurar la aplicación')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              children: [
                const EmojiBadge('🔧', size: 88),
                const SizedBox(height: 20),
                SelectableText(
                  '$message\n\nIniciá Flutter pasando FIREBASE_API_KEY, FIREBASE_APP_ID, '
                  'FIREBASE_MESSAGING_SENDER_ID y FIREBASE_PROJECT_ID en frontend/dart_defines.json '
                  '(o con --dart-define). Revisá docs/GUIA_EJECUCION_LOCAL.md.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
