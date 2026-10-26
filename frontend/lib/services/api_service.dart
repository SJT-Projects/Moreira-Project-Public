import 'dart:async';
import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

import '../models/analisis_result.dart';
import '../models/quiz.dart';
import '../models/reporte_comunitario.dart';

enum ApiErrorKind {
  authentication,
  authorization,
  connectivity,
  timeout,
  firebase,
  firestore,
  service,
  validation,
  rateLimit,
  invalidResponse,
  unknown,
}

class ApiException implements Exception {
  const ApiException(
    this.message, {
    this.statusCode,
    this.code,
    this.kind = ApiErrorKind.unknown,
    this.retryable = false,
  });

  final String message;
  final int? statusCode;
  final String? code;
  final ApiErrorKind kind;
  final bool retryable;

  @override
  String toString() => message;
}

class ApiService {
  ApiService({http.Client? client, FirebaseAuth? auth})
    : _client = client ?? http.Client(),
      _auth = auth ?? FirebaseAuth.instance;

  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  final http.Client _client;
  final FirebaseAuth _auth;

  static Uri _requestUri(String path) {
    if (_configuredBaseUrl.isNotEmpty) {
      return Uri.parse('$_configuredBaseUrl$path');
    }

    final page = Uri.base;
    if (page.scheme == 'http' || page.scheme == 'https') {
      if (page.host == '127.0.0.1' || page.host == 'localhost') {
        return Uri.parse('http://127.0.0.1:8000$path');
      }
      return page.resolve(path);
    }
    return Uri.parse('http://127.0.0.1:8000$path');
  }

  Future<Map<String, String>> _headers({bool forceRefresh = false}) async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const ApiException(
        'Iniciá sesión para continuar.',
        code: 'auth_required',
        kind: ApiErrorKind.authentication,
      );
    }

    try {
      final token = await user.getIdToken(forceRefresh);
      if (token == null || token.isEmpty) {
        throw const ApiException(
          'No pudimos obtener una sesión válida. Volvé a iniciar sesión.',
          code: 'auth_token_missing',
          kind: ApiErrorKind.authentication,
        );
      }
      return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };
    } on FirebaseAuthException catch (error) {
      throw _firebaseAuthException(error);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException(
        'Firebase no pudo actualizar la sesión. Volvé a intentar.',
        code: 'auth_refresh_failed',
        kind: ApiErrorKind.firebase,
        retryable: true,
      );
    }
  }

  Future<http.Response> _request({
    required String method,
    required String path,
    bool authenticated = false,
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 20),
    String timeoutMessage = 'La operación tardó demasiado. Volvé a intentar.',
  }) async {
    Future<http.Response> send({bool forceRefresh = false}) async {
      final request = http.Request(method, _requestUri(path));
      if (authenticated) {
        request.headers.addAll(await _headers(forceRefresh: forceRefresh));
      } else if (body != null) {
        request.headers['Content-Type'] = 'application/json';
      }
      if (body != null) request.body = jsonEncode(body);
      final streamed = await _client.send(request);
      return http.Response.fromStream(streamed);
    }

    try {
      var response = await send().timeout(timeout);
      if (authenticated && response.statusCode == 401) {
        // Si el servidor recibió un token vencido, Firebase genera uno nuevo y
        // repetimos la solicitud una sola vez.
        response = await send(forceRefresh: true).timeout(timeout);
      }
      return response;
    } on TimeoutException {
      throw ApiException(
        timeoutMessage,
        code: 'request_timeout',
        kind: ApiErrorKind.timeout,
        retryable: true,
      );
    } on FirebaseAuthException catch (error) {
      throw _firebaseAuthException(error);
    } on ApiException {
      rethrow;
    } on http.ClientException {
      throw const ApiException(
        'No se pudo conectar con la API. Comprobá que el backend siga activo.',
        code: 'api_unreachable',
        kind: ApiErrorKind.connectivity,
        retryable: true,
      );
    } catch (_) {
      throw const ApiException(
        'Ocurrió un error de conexión inesperado. Revisá Internet y volvé a intentar.',
        code: 'connection_unknown',
        kind: ApiErrorKind.connectivity,
        retryable: true,
      );
    }
  }

  Future<AnalisisResult> analizar(String texto) async {
    final response = await _request(
      method: 'POST',
      path: '/v1/analisis',
      authenticated: true,
      body: {'texto': texto},
      timeout: const Duration(seconds: 30),
      timeoutMessage: 'El análisis tardó demasiado. Volvé a intentar.',
    );
    return AnalisisResult.fromJson(_decodeResponse(response));
  }

  Future<List<ReporteComunitario>> listarReportes() async {
    final response = await _request(
      method: 'GET',
      path: '/v1/reportes?page_size=30',
      timeoutMessage: 'La comunidad tardó demasiado en responder.',
    );
    return _reportsFromResponse(response);
  }

  Future<void> crearReporte({
    required String titulo,
    required String descripcion,
    required String categoria,
  }) async {
    final response = await _request(
      method: 'POST',
      path: '/v1/reportes',
      authenticated: true,
      body: {
        'titulo': titulo,
        'descripcion': descripcion,
        'categoria': categoria,
      },
      timeoutMessage: 'No se pudo guardar el reporte a tiempo.',
    );
    _decodeResponse(response);
  }

  Future<Map<String, dynamic>> _sendAdmin({
    required String method,
    required String path,
    required Map<String, dynamic> body,
  }) async {
    final response = await _request(
      method: method,
      path: path,
      authenticated: true,
      body: body,
      timeoutMessage: 'La acción administrativa tardó demasiado.',
    );
    return _decodeResponse(response);
  }

  Future<List<ReporteComunitario>> listarMisReportes() async {
    final response = await _request(
      method: 'GET',
      path: '/v1/reportes/mios?page_size=30',
      authenticated: true,
      timeoutMessage: 'Tus reportes tardaron demasiado en responder.',
    );
    return _reportsFromResponse(response);
  }

  Future<List<ReporteComunitario>> listarReportesPendientes() async {
    final response = await _request(
      method: 'GET',
      path: '/v1/admin/reportes-pendientes?page_size=30',
      authenticated: true,
      timeoutMessage: 'La moderación tardó demasiado en responder.',
    );
    return _reportsFromResponse(response);
  }

  Future<ReporteRevision> obtenerReporteAdmin(String id) async {
    final response = await _request(
      method: 'GET',
      path: '/v1/admin/reportes/${Uri.encodeComponent(id)}',
      authenticated: true,
      timeoutMessage: 'El detalle del reporte tardó demasiado en responder.',
    );
    return ReporteRevision.fromJson(_decodeResponse(response));
  }

  Future<void> moderarReporte(String id, String accion) async {
    await _sendAdmin(
      method: 'PATCH',
      path: '/v1/admin/reportes/${Uri.encodeComponent(id)}/moderacion',
      body: {'accion': accion},
    );
  }

  Future<void> actualizarEvidencia({
    required String tipo,
    required String valor,
    required String estado,
  }) async {
    await _sendAdmin(
      method: 'PATCH',
      path: '/v1/admin/indicadores/evidencia',
      body: {
        'indicador': {'type': tipo, 'value': valor},
        'estado': estado,
      },
    );
  }

  Future<Quiz> obtenerCuestionario(String id) async {
    final response = await _request(
      method: 'GET',
      path: '/v1/academia/cuestionarios/${Uri.encodeComponent(id)}',
      timeoutMessage: 'El cuestionario tardó demasiado en responder.',
    );
    return Quiz.fromJson(_decodeResponse(response));
  }

  Future<QuizAttemptResult> enviarIntento(
    String id,
    Map<String, int> answers,
  ) async {
    final response = await _request(
      method: 'POST',
      path: '/v1/academia/cuestionarios/${Uri.encodeComponent(id)}/intentos',
      authenticated: true,
      body: {
        'answers': answers.entries
            .map(
              (entry) => {
                'question_id': entry.key,
                'selected_option': entry.value,
              },
            )
            .toList(growable: false),
      },
      timeoutMessage: 'No se pudo guardar el resultado a tiempo.',
    );
    return QuizAttemptResult.fromJson(_decodeResponse(response));
  }

  Future<QuizProgress> obtenerProgresoAcademico() async {
    final response = await _request(
      method: 'GET',
      path: '/v1/academia/progreso',
      authenticated: true,
      timeoutMessage: 'El progreso tardó demasiado en responder.',
    );
    return QuizProgress.fromJson(_decodeResponse(response));
  }

  static List<ReporteComunitario> _reportsFromResponse(http.Response response) {
    final items = _decodeResponse(response)['items'];
    if (items is! List) {
      throw const ApiException(
        'La API devolvió reportes con un formato inválido.',
        code: 'invalid_reports_response',
        kind: ApiErrorKind.invalidResponse,
      );
    }
    return items
        .whereType<Map<String, dynamic>>()
        .map(ReporteComunitario.fromJson)
        .toList(growable: false);
  }

  static Map<String, dynamic> _decodeResponse(http.Response response) {
    Map<String, dynamic> payload;
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      payload = decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
    } on FormatException {
      throw ApiException(
        'La API devolvió una respuesta inválida.',
        statusCode: response.statusCode,
        code: 'invalid_api_response',
        kind: ApiErrorKind.invalidResponse,
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) return payload;

    final detail = payload['detail'];
    final code = detail is Map ? detail['code'] as String? : null;
    final detailMessage = detail is Map
        ? detail['message'] as String?
        : detail is String
        ? detail
        : null;

    final (message, kind, retryable) = switch ((response.statusCode, code)) {
      (401, 'auth_required') => (
        'Iniciá sesión para continuar.',
        ApiErrorKind.authentication,
        false,
      ),
      (401, 'auth_session_expired') || (401, 'auth_session_revoked') => (
        detailMessage ?? 'La sesión venció. Volvé a iniciar sesión.',
        ApiErrorKind.authentication,
        false,
      ),
      (401, _) => (
        detailMessage ??
            'No pudimos validar la sesión. Volvé a iniciar sesión.',
        ApiErrorKind.authentication,
        false,
      ),
      (403, 'auth_user_disabled') => (
        detailMessage ?? 'La cuenta está deshabilitada.',
        ApiErrorKind.authorization,
        false,
      ),
      (403, _) => (
        detailMessage ?? 'No tenés permisos para realizar esta acción.',
        ApiErrorKind.authorization,
        false,
      ),
      (503, 'auth_provider_unavailable') ||
      (503, 'auth_verification_failed') => (
        detailMessage ?? 'Firebase Authentication no está disponible.',
        ApiErrorKind.firebase,
        true,
      ),
      (503, 'admin_verification_failed') => (
        detailMessage ?? 'No se pudo verificar el rol de administrador.',
        ApiErrorKind.firebase,
        true,
      ),
      (422, _) => (
        detailMessage ?? 'Revisá los datos ingresados.',
        ApiErrorKind.validation,
        false,
      ),
      (429, _) => (
        detailMessage ??
            'Alcanzaste el límite de uso. Esperá y volvé a intentar.',
        ApiErrorKind.rateLimit,
        true,
      ),
      (>= 500, _) => (
        detailMessage ?? 'El servicio no está disponible. Volvé a intentar.',
        _looksLikeFirestore(detailMessage)
            ? ApiErrorKind.firestore
            : ApiErrorKind.service,
        true,
      ),
      (_, _) => (
        detailMessage ?? 'No se pudo completar la solicitud.',
        ApiErrorKind.unknown,
        false,
      ),
    };

    throw ApiException(
      message,
      statusCode: response.statusCode,
      code: code,
      kind: kind,
      retryable: retryable,
    );
  }

  static bool _looksLikeFirestore(String? message) {
    final normalized = message?.toLowerCase() ?? '';
    return normalized.contains('firestore') ||
        normalized.contains('base de datos');
  }

  static ApiException _firebaseAuthException(FirebaseAuthException error) {
    return switch (error.code) {
      'network-request-failed' => const ApiException(
        'No hay conexión a Internet o Firebase no responde.',
        code: 'firebase_network_error',
        kind: ApiErrorKind.connectivity,
        retryable: true,
      ),
      'user-disabled' => const ApiException(
        'La cuenta está deshabilitada.',
        code: 'auth_user_disabled',
        kind: ApiErrorKind.authorization,
      ),
      'too-many-requests' => const ApiException(
        'Firebase bloqueó temporalmente los intentos. Esperá unos minutos.',
        code: 'firebase_rate_limited',
        kind: ApiErrorKind.rateLimit,
        retryable: true,
      ),
      'requires-recent-login' => const ApiException(
        'Por seguridad, cerrá sesión e ingresá nuevamente.',
        code: 'auth_recent_login_required',
        kind: ApiErrorKind.authentication,
      ),
      _ => ApiException(
        'Firebase no pudo verificar la sesión (${error.code}).',
        code: error.code,
        kind: ApiErrorKind.firebase,
        retryable: true,
      ),
    };
  }
}
