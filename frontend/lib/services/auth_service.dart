import 'package:firebase_auth/firebase_auth.dart';

class AuthService {
  AuthService({FirebaseAuth? auth}) : _auth = auth ?? FirebaseAuth.instance;

  final FirebaseAuth _auth;

  Stream<User?> get userChanges => _auth.userChanges();

  User? get currentUser => _auth.currentUser;

  Future<void> signIn({required String email, required String password}) async {
    await _auth.signInWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );
  }

  Future<void> register({required String email, required String password}) async {
    await _auth.createUserWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );
  }

  Future<void> sendPasswordReset(String email) async {
    await _auth.sendPasswordResetEmail(email: email.trim());
  }

  Future<void> signOut() => _auth.signOut();

  Future<bool> get isAdmin async {
    final user = _auth.currentUser;
    if (user == null) return false;
    final result = await user.getIdTokenResult();
    return result.claims?['admin'] == true;
  }

  Future<String> get freshIdToken async {
    final user = _auth.currentUser;
    if (user == null) throw StateError('Iniciá sesión para continuar.');
    final token = await user.getIdToken();
    if (token == null || token.isEmpty) {
      throw StateError('No se pudo verificar tu sesión. Volvé a iniciar sesión.');
    }
    return token;
  }
}
