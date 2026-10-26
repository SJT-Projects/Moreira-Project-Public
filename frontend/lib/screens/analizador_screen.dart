import 'package:flutter/material.dart';

import '../models/analisis_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ui_calida.dart';

class AnalizadorScreen extends StatefulWidget {
  const AnalizadorScreen({super.key});

  @override
  State<AnalizadorScreen> createState() => _AnalizadorScreenState();
}

class _AnalizadorScreenState extends State<AnalizadorScreen> {
  final _inputController = TextEditingController();
  final _api = ApiService();
  AnalisisResult? _result;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _analyze() async {
    final text = _inputController.text.trim();
    if (text.isEmpty) {
      setState(
        () => _error =
            'Pegá el mensaje, número, correo o enlace que quieras revisar.',
      );
      return;
    }
    if (text.length > 10000) {
      setState(
        () => _error = 'El texto no puede superar los 10.000 caracteres.',
      );
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      final result = await _api.analizar(text);
      if (mounted) setState(() => _result = result);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const SectionHeader(
              emoji: '👋',
              title: '¡Hola! Revisemos juntos ese mensaje',
              subtitle:
                  'Pegá acá el mensaje, número, correo o enlace que te llegó y te decimos si parece una estafa.',
            ),
            const SizedBox(height: 20),
            const InfoBanner(
              title: 'Mientras lo revisamos',
              message:
                  'No toques los enlaces del mensaje ni respondas. Nunca compartas claves ni códigos.',
            ),
            const SizedBox(height: 20),
            Text('✍️ Pegá el mensaje acá:', style: theme.textTheme.titleMedium),
            const SizedBox(height: 10),
            TextField(
              controller: _inputController,
              minLines: 5,
              maxLines: 10,
              maxLength: 10000,
              enabled: !_loading,
              style: theme.textTheme.bodyLarge,
              decoration: const InputDecoration(
                hintText:
                    'Ej.: Su cuenta está bloqueada. Mandanos el código que te llegó por SMS...',
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _loading ? null : _analyze,
              icon: _loading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 3,
                        color: Colors.white,
                      ),
                    )
                  : const Emoji('🔍', size: 26),
              label: Text(
                _loading ? 'Analizando, un momento...' : 'Analizar mensaje',
              ),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(68),
                textStyle: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              InfoBanner(message: _error!, kind: BannerKind.error),
            ],
            if (_result != null) ...[
              const SizedBox(height: 24),
              _buildResult(theme, _result!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResult(ThemeData theme, AnalisisResult result) {
    final style = RiskStyle.of(result.risk);
    final color = style.color;

    return Semantics(
      container: true,
      liveRegion: true,
      child: Card(
        color: AppColors.papel,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(color: color, width: 3),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Franja tipo semáforo: emoji + ícono + texto, nunca solo color.
            Container(
              color: style.background,
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Emoji(style.emoji, size: 44),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(style.icon, color: color, size: 30),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                result.riskLabel,
                                style: theme.textTheme.titleLarge?.copyWith(
                                  color: color,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          style.headline,
                          style: theme.textTheme.titleMedium?.copyWith(
                            color: color,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(result.summary, style: theme.textTheme.bodyLarge),
                  if (result.state != 'completo') ...[
                    const SizedBox(height: 14),
                    const InfoBanner(
                      kind: BannerKind.warning,
                      message:
                          'Este análisis quedó incompleto. Una comprobación externa no respondió; el resultado disponible no confirma que el mensaje sea seguro.',
                    ),
                  ],
                  const SizedBox(height: 18),
                  // Lo más importante para la persona: qué hacer ahora.
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.mielClaro,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('💡 Qué hacer', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 6),
                        Text(result.advice, style: theme.textTheme.bodyLarge),
                      ],
                    ),
                  ),
                  if (result.reasons.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    Text(
                      '🔎 Lo que encontramos',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    for (final reason in result.reasons)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Icon(
                                Icons.arrow_right_rounded,
                                size: 30,
                                color: color,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                reason.description,
                                style: theme.textTheme.bodyLarge,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                  if (result.indicators.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      '🤝 Lo que avisó la comunidad',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    for (final indicator in result.indicators)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.fingerprint, size: 30),
                        title: Text(indicator.maskedValue),
                        subtitle: Text(
                          '${_indicatorStatus(indicator.evidenceStatus)} · '
                          '${indicator.approvedReports} reporte(s) aprobado(s)',
                        ),
                      ),
                  ],
                  if (result.checks.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    const Divider(),
                    ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      title: Text(
                        'Ver detalles de las comprobaciones',
                        style: theme.textTheme.titleSmall,
                      ),
                      children: [
                        for (final entry in result.checks.entries)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              entry.value.status == 'realizada'
                                  ? Icons.check_circle_outline
                                  : entry.value.status == 'fallida'
                                  ? Icons.info_outline
                                  : Icons.remove_circle_outline,
                              size: 28,
                            ),
                            title: Text(_checkName(entry.key)),
                            subtitle: Text(entry.value.detail),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _indicatorStatus(String status) => switch (status) {
    'confirmado' => 'Evidencia revisada y confirmada',
    'en_revision' => 'En revisión',
    'no_verificado' => 'Reporte aprobado; evidencia no confirmada',
    'descartado' => 'Evidencia descartada',
    _ => 'Sin antecedentes',
  };

  static String _checkName(String name) => switch (name) {
    'firestore' => 'Reportes comunitarios',
    'reputacion_url' => 'Reputación de enlaces',
    'virustotal' => 'VirusTotal',
    'groq' => 'Análisis de contexto',
    _ => name,
  };
}
