import 'package:flutter/material.dart';

import '../models/reporte_comunitario.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ui_calida.dart';

class ComunidadScreen extends StatefulWidget {
  const ComunidadScreen({super.key});

  @override
  State<ComunidadScreen> createState() => _ComunidadScreenState();
}

class _ComunidadScreenState extends State<ComunidadScreen> {
  final _api = ApiService();
  final _auth = AuthService();
  List<ReporteComunitario> _reports = const [];
  List<ReporteComunitario> _pending = const [];
  bool _isAdmin = false;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final reports = await _api.listarReportes();
      var isAdmin = false;
      var pending = const <ReporteComunitario>[];
      try {
        isAdmin = await _auth.isAdmin;
        if (isAdmin) pending = await _api.listarReportesPendientes();
      } catch (_) {
        isAdmin = false;
      }
      if (!mounted) return;
      setState(() {
        _reports = reports;
        _isAdmin = isAdmin;
        _pending = pending;
      });
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createReport() async {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    final formKey = GlobalKey<FormState>();
    var category = 'otro';
    var consent = false;
    var submitting = false;
    String? dialogError;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('📣 Compartir una alerta'),
          content: SizedBox(
            width: 520,
            child: Form(
              key: formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const InfoBanner(
                      message:
                          'Tu reporte queda pendiente hasta que un administrador lo revise. '
                          'El texto original y sus indicadores se guardan en un área privada para revisión. '
                          'Publicamos el texto con correos, teléfonos y enlaces ocultos; solo administradores autorizados ven la evidencia completa. '
                          'Nunca incluyas contraseñas ni códigos de acceso.',
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: titleController,
                      maxLength: 120,
                      decoration: const InputDecoration(
                        labelText: 'Título',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) => (value?.trim().length ?? 0) >= 5
                          ? null
                          : 'El título debe tener al menos cinco caracteres.',
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: descriptionController,
                      minLines: 3,
                      maxLines: 6,
                      maxLength: 4000,
                      decoration: const InputDecoration(
                        labelText: '¿Qué ocurrió?',
                        border: OutlineInputBorder(),
                        hintText: 'Describí la situación; no incluyas claves ni códigos.',
                      ),
                      validator: (value) => (value?.trim().length ?? 0) >= 20
                          ? null
                          : 'Agregá por lo menos 20 caracteres para explicar lo ocurrido.',
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: category,
                      isExpanded: true,
                      itemHeight: 56,
                      decoration: const InputDecoration(labelText: '¿Por dónde te llegó?'),
                      items: [
                        for (final value in const [
                          'whatsapp',
                          'sms',
                          'correo',
                          'llamada',
                          'sitio_web',
                          'compra',
                          'otro',
                        ])
                          DropdownMenuItem(
                            value: value,
                            child: Text('${_categoryEmoji(value)}  ${_categoryName(value)}'),
                          ),
                      ],
                      onChanged: (value) => setDialogState(() => category = value ?? 'otro'),
                    ),
                    const SizedBox(height: 8),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: consent,
                      onChanged: (value) => setDialogState(() => consent = value ?? false),
                      title: const Text('Entiendo cómo se revisa y publica este reporte.'),
                    ),
                    if (dialogError != null)
                      InfoBanner(message: dialogError!, kind: BannerKind.error),
                  ],
                ),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: submitting ? null : () => Navigator.pop(dialogContext),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: submitting
                  ? null
                  : () async {
                      if (!(formKey.currentState?.validate() ?? false)) return;
                      if (!consent) {
                        setDialogState(() => dialogError = 'Aceptá cómo se revisa y publica el reporte.');
                        return;
                      }
                      setDialogState(() {
                        submitting = true;
                        dialogError = null;
                      });
                      try {
                        await _api.crearReporte(
                          titulo: titleController.text.trim(),
                          descripcion: descriptionController.text.trim(),
                          categoria: category,
                        );
                        if (!dialogContext.mounted) return;
                        Navigator.pop(dialogContext);
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('✅ ¡Gracias! Recibimos tu reporte. Queda pendiente de revisión.')),
                          );
                        }
                        await _load();
                      } on ApiException catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            dialogError = error.message;
                            submitting = false;
                          });
                        }
                      }
                    },
              child: submitting
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 3, color: Colors.white),
                    )
                  : const Text('Enviar para revisión'),
            ),
          ],
        ),
      ),
    );

    titleController.dispose();
    descriptionController.dispose();
  }

  Future<void> _review(ReporteComunitario item) async {
    ReporteRevision? revision;
    try {
      revision = await _api.obtenerReporteAdmin(item.id);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
      return;
    }
    if (!mounted) return;

    final action = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(item.title),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Reporte de ${item.author} · ${_categoryName(item.category)}'),
                const Divider(height: 20),
                const Text('Texto original enviado por el usuario', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                SelectableText(
                  revision!.privateEvidence['texto_original'] as String? ?? '(Sin texto)',
                ),
                const SizedBox(height: 16),
                const Text('Indicadores informados', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                ..._privateIndicators(revision.privateEvidence['indicadores']),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Volver')),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, 'rechazado'),
            child: const Text('Rechazar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, 'aprobado'),
            child: const Text('Aprobar publicación'),
          ),
        ],
      ),
    );

    if (action == null) return;
    try {
      await _api.moderarReporte(item.id, action);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(action == 'aprobado' ? 'Reporte publicado.' : 'Reporte rechazado.')),
      );
      await _load();
    } on ApiException catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  List<Widget> _privateIndicators(dynamic raw) {
    if (raw is! List || raw.isEmpty) return const [Text('No se detectaron indicadores.')];
    return raw.whereType<Map<String, dynamic>>().map((item) {
      final type = item['tipo'] as String? ?? '';
      final value = item['valor'] as String? ?? '';
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SelectableText('${_indicatorTypeName(type)}: $value'),
          Wrap(spacing: 8, children: [
            TextButton.icon(
              onPressed: () => _setIndicatorState(type, value, 'confirmado'),
              icon: const Icon(Icons.verified_outlined),
              label: const Text('Confirmar indicador'),
            ),
            TextButton.icon(
              onPressed: () => _setIndicatorState(type, value, 'descartado'),
              icon: const Icon(Icons.remove_circle_outline),
              label: const Text('Descartar indicador'),
            ),
          ]),
        ]),
      );
    }).toList(growable: false);
  }

  Future<void> _setIndicatorState(String type, String value, String state) async {
    try {
      await _api.actualizarEvidencia(tipo: type, valor: value, estado: state);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state == 'confirmado' ? 'Indicador confirmado.' : 'Indicador descartado.')),
      );
    } on ApiException catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  static String _indicatorTypeName(String type) => switch (type) {
        'telefono' => 'Teléfono',
        'correo' => 'Correo',
        'url' => 'Enlace',
        'dominio' => 'Dominio',
        _ => 'Indicador',
      };

  static String _categoryEmoji(String category) => switch (category) {
        'whatsapp' => '💬',
        'sms' => '📱',
        'correo' => '✉️',
        'llamada' => '📞',
        'sitio_web' => '🌐',
        'compra' => '🛒',
        _ => '❓',
      };

  static String _categoryName(String category) => switch (category) {
        'whatsapp' => 'WhatsApp',
        'sms' => 'SMS',
        'correo' => 'Correo electrónico',
        'llamada' => 'Llamada',
        'sitio_web' => 'Sitio web',
        'compra' => 'Compra',
        _ => 'Otro',
      };

  Widget _reportCard(ReporteComunitario item, {bool pending = false}) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            EmojiBadge(
              _categoryEmoji(item.category),
              size: 56,
              background: pending ? AppColors.amarilloFondo : AppColors.durazno,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Chip(label: Text(_categoryName(item.category))),
                      if (pending)
                        const Chip(
                          avatar: Emoji('⏳', size: 18),
                          label: Text('Pendiente de revisión'),
                          backgroundColor: AppColors.amarilloFondo,
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(item.title, style: theme.textTheme.titleMedium),
                  const SizedBox(height: 6),
                  Text(item.description, style: theme.textTheme.bodyLarge),
                  const SizedBox(height: 8),
                  Text(
                    '👤 Compartido por ${item.author}',
                    style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.textoSuave),
                  ),
                  if (_isAdmin && pending) ...[
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: () => _review(item),
                      icon: const Icon(Icons.fact_check_outlined),
                      label: const Text('Revisar evidencia'),
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // El encabezado se desplaza junto con la lista para dejar más lugar a las
    // alertas en pantallas chicas.
    final header = Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionHeader(
            emoji: '🤝',
            title: _isAdmin ? 'Reportes revisados y pendientes' : 'Alertas de la comunidad',
            subtitle: 'Engaños que otras personas ya recibieron. Leelos para estar atento.',
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
              label: const Text('Actualizar'),
            ),
          ),
          if (_isAdmin && _pending.isNotEmpty) ...[
            const SizedBox(height: 12),
            InfoBanner(
              kind: BannerKind.warning,
              message: 'Hay ${_pending.length} reporte(s) por revisar.',
            ),
          ],
        ],
      ),
    );

    Widget withHeader(Widget child) => Column(
          children: [
            Padding(padding: const EdgeInsets.fromLTRB(20, 24, 20, 0), child: header),
            Expanded(child: child),
          ],
        );

    return Stack(
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: _loading && _reports.isEmpty
                ? withHeader(const CenteredMessage(emoji: '⏳', message: 'Cargando las alertas...'))
                : _error != null && _reports.isEmpty
                    ? withHeader(
                        CenteredMessage(
                          emoji: '📡',
                          message: _error!,
                          action: FilledButton.icon(
                            onPressed: _load,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Reintentar'),
                          ),
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.fromLTRB(20, 24, 20, 110),
                          children: [
                            header,
                            if (_error != null)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: InfoBanner(message: _error!, kind: BannerKind.error),
                              ),
                            if (_isAdmin && _pending.isNotEmpty) ...[
                              Text('⏳ Pendientes', style: theme.textTheme.titleLarge),
                              const SizedBox(height: 10),
                              for (final report in _pending) _reportCard(report, pending: true),
                              const Divider(height: 32),
                              Text('📢 Publicados', style: theme.textTheme.titleLarge),
                              const SizedBox(height: 10),
                            ],
                            if (_reports.isEmpty)
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 24),
                                child: CenteredMessage(
                                  emoji: '🌻',
                                  message: 'Todavía no hay alertas publicadas.',
                                ),
                              )
                            else
                              for (final report in _reports) _reportCard(report),
                          ],
                        ),
                      ),
          ),
        ),
        Positioned(
          right: 20,
          bottom: 20,
          child: FloatingActionButton.extended(
            onPressed: _createReport,
            icon: const Emoji('📣', size: 26),
            label: const Text('Reportar una estafa'),
          ),
        ),
      ],
    );
  }
}
