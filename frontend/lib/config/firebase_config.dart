import 'package:firebase_core/firebase_core.dart';

/// Firebase Web publica estas opciones de cliente; Firebase Admin y las API
/// secretas permanecen exclusivamente en el servidor.
FirebaseOptions? firebaseOptionsFromEnvironment() {
  const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  const appId = String.fromEnvironment('FIREBASE_APP_ID');
  const senderId = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  const authDomain = String.fromEnvironment('FIREBASE_AUTH_DOMAIN');

  if (apiKey.isEmpty || appId.isEmpty || senderId.isEmpty || projectId.isEmpty) {
    return null;
  }

  return FirebaseOptions(
    apiKey: apiKey,
    appId: appId,
    messagingSenderId: senderId,
    projectId: projectId,
    authDomain: authDomain.isEmpty ? '$projectId.firebaseapp.com' : authDomain,
  );
}
