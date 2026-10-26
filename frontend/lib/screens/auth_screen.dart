import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ui_calida.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _auth = AuthService();
  bool _registering = false;
  bool _loading = false;
  bool _hidePassword = true;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      if (_registering) {
        await _auth.register(
          email: _emailController.text,
          password: _passwordController.text,
        );
      } else {
        await _auth.signIn(
          email: _emailController.text,
          password: _passwordController.text,
        );
      }
    } on FirebaseAuthException catch (error) {
      if (mounted) setState(() => _error = _translateError(error));
    } catch (error) {
      if (mounted) setState(() => _error = _translateError(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resetPassword() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(
        () => _error = 'Escribí primero tu correo para recuperar la clave.',
      );
      return;
    }
    try {
      await _auth.sendPasswordReset(email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Te enviamos un correo para restablecer tu clave.'),
        ),
      );
    } on FirebaseAuthException catch (error) {
      if (mounted) setState(() => _error = _translateError(error));
    }
  }

  static String _translateError(Object error) {
    if (error is FirebaseAuthException) {
      return switch (error.code) {
        'invalid-email' => 'Revisá el formato del correo.',
        'email-already-in-use' =>
          'Ese correo ya tiene una cuenta. Iniciá sesión.',
        'weak-password' => 'Elegí una clave de al menos seis caracteres.',
        'user-not-found' ||
        'wrong-password' ||
        'invalid-credential' => 'El correo o la clave no coinciden.',
        'network-request-failed' =>
          'No hay conexión. Revisá tu Internet y volvé a intentar.',
        'too-many-requests' =>
          'Hubo demasiados intentos. Esperá un momento y volvé a probar.',
        'user-disabled' => 'Esta cuenta fue deshabilitada en Firebase.',
        'quota-exceeded' => 'Firebase alcanzó temporalmente su límite de uso.',
        'internal-error' || 'service-unavailable' =>
          'Firebase Authentication no está disponible. Volvé a intentar en unos minutos.',
        'operation-not-allowed' =>
          'El inicio por correo todavía no está habilitado en Firebase Authentication.',
        _ => 'Firebase rechazó la operación (${error.code}).',
      };
    }
    return 'No se pudo conectar con Firebase. Revisá la configuración del frontend.';
  }

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
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Center(child: EmojiBadge('🛡️', size: 96)),
                      const SizedBox(height: 16),
                      Text(
                        _registering ? '¡Creá tu cuenta!' : '¡Te damos la bienvenida! 👋',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Tu cuenta permite analizar mensajes y compartir reportes comunitarios.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: AppColors.textoSuave,
                        ),
                      ),
                      const SizedBox(height: 24),
                      TextFormField(
                        controller: _emailController,
                        enabled: !_loading,
                        keyboardType: TextInputType.emailAddress,
                        style: Theme.of(context).textTheme.bodyLarge,
                        autofillHints: const [AutofillHints.email],
                        decoration: const InputDecoration(
                          labelText: 'Correo electrónico',
                          prefixIcon: Icon(Icons.email_outlined),
                        ),
                        validator: (value) {
                          final text = value?.trim() ?? '';
                          return text.contains('@')
                              ? null
                              : 'Ingresá un correo válido.';
                        },
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _passwordController,
                        enabled: !_loading,
                        obscureText: _hidePassword,
                        style: Theme.of(context).textTheme.bodyLarge,
                        autofillHints: _registering
                            ? const [AutofillHints.newPassword]
                            : const [AutofillHints.password],
                        decoration: InputDecoration(
                          labelText: 'Contraseña',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            tooltip: _hidePassword
                                ? 'Mostrar contraseña'
                                : 'Ocultar contraseña',
                            icon: Icon(
                              _hidePassword
                                  ? Icons.visibility
                                  : Icons.visibility_off,
                            ),
                            onPressed: () =>
                                setState(() => _hidePassword = !_hidePassword),
                          ),
                        ),
                        validator: (value) => (value?.length ?? 0) >= 6
                            ? null
                            : 'La contraseña debe tener al menos seis caracteres.',
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 16),
                        InfoBanner(message: _error!, kind: BannerKind.error),
                      ],
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
                        child: _loading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  strokeWidth: 3,
                                  color: Colors.white,
                                ),
                              )
                            : Text(_registering ? 'Crear cuenta' : 'Ingresar'),
                      ),
                      const SizedBox(height: 8),
                      if (!_registering)
                        TextButton(
                          onPressed: _loading ? null : _resetPassword,
                          child: const Text('Olvidé mi contraseña'),
                        ),
                      TextButton(
                        onPressed: _loading
                            ? null
                            : () => setState(() {
                                _registering = !_registering;
                                _error = null;
                              }),
                        child: Text(
                          _registering
                              ? 'Ya tengo cuenta · Ingresar'
                              : 'Crear una cuenta',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
