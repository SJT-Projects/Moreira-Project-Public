class ReporteComunitario {
  const ReporteComunitario({
    required this.id,
    required this.author,
    required this.title,
    required this.description,
    required this.category,
    required this.moderationState,
    this.createdAt,
  });

  final String id;
  final String author;
  final String title;
  final String description;
  final String category;
  final String moderationState;
  final DateTime? createdAt;

  bool get isPublished => moderationState == 'aprobado';

  factory ReporteComunitario.fromJson(Map<String, dynamic> json) => ReporteComunitario(
        id: json['id'] as String? ?? '',
        author: json['autor'] as String? ?? 'Vecino',
        title: json['titulo'] as String? ?? 'Alerta comunitaria',
        description: json['descripcion'] as String? ?? '',
        category: json['categoria'] as String? ?? 'otro',
        moderationState: json['estado_moderacion'] as String? ?? 'pendiente',
        createdAt: DateTime.tryParse(json['creado_en'] as String? ?? ''),
      );
}

class ReporteRevision {
  const ReporteRevision({required this.report, required this.privateEvidence});

  final ReporteComunitario report;
  final Map<String, dynamic> privateEvidence;

  factory ReporteRevision.fromJson(Map<String, dynamic> json) {
    final rawReport = json['reporte'];
    final rawPrivate = json['evidencia_privada'];
    return ReporteRevision(
      report: ReporteComunitario.fromJson(
        rawReport is Map<String, dynamic> ? rawReport : const {},
      ),
      privateEvidence: rawPrivate is Map<String, dynamic> ? rawPrivate : const {},
    );
  }
}
