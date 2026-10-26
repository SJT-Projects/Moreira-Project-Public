enum RiskLevel { high, medium, low, unknown }

class AnalysisEvidence {
  const AnalysisEvidence({
    required this.source,
    required this.code,
    required this.description,
  });

  final String source;
  final String code;
  final String description;

  factory AnalysisEvidence.fromJson(Map<String, dynamic> json) => AnalysisEvidence(
        source: json['fuente'] as String? ?? 'análisis',
        code: json['codigo'] as String? ?? '',
        description: json['descripcion'] as String? ?? '',
      );
}

class IndicatorFinding {
  const IndicatorFinding({
    required this.type,
    required this.maskedValue,
    required this.evidenceStatus,
    required this.approvedReports,
  });

  final String type;
  final String maskedValue;
  final String evidenceStatus;
  final int approvedReports;

  factory IndicatorFinding.fromJson(Map<String, dynamic> json) => IndicatorFinding(
        type: json['tipo'] as String? ?? '',
        maskedValue: json['valor'] as String? ?? '',
        evidenceStatus: json['estado'] as String? ?? 'sin_antecedentes',
        approvedReports: json['reportes_aprobados'] as int? ?? 0,
      );
}

class ServiceCheck {
  const ServiceCheck({required this.status, required this.detail});

  final String status;
  final String detail;

  factory ServiceCheck.fromJson(Map<String, dynamic> json) => ServiceCheck(
        status: json['estado'] as String? ?? 'fallida',
        detail: json['detalle'] as String? ?? '',
      );
}

class AnalisisResult {
  const AnalisisResult({
    required this.risk,
    required this.state,
    required this.summary,
    required this.reasons,
    required this.advice,
    required this.indicators,
    required this.checks,
  });

  final RiskLevel risk;
  final String state;
  final String summary;
  final List<AnalysisEvidence> reasons;
  final String advice;
  final List<IndicatorFinding> indicators;
  final Map<String, ServiceCheck> checks;

  String get riskLabel => switch (risk) {
        RiskLevel.high => 'ALTO RIESGO',
        RiskLevel.medium => 'RIESGO MEDIO',
        RiskLevel.low => 'SIN RIESGO DETECTADO',
        RiskLevel.unknown => 'ANÁLISIS INCOMPLETO',
      };

  factory AnalisisResult.fromJson(Map<String, dynamic> json) {
    final rawRisk = json['riesgo'] as String?;
    final risk = switch (rawRisk) {
      'alto' => RiskLevel.high,
      'medio' => RiskLevel.medium,
      'bajo' => RiskLevel.low,
      _ => RiskLevel.unknown,
    };

    final rawChecks = json['comprobaciones'];
    final rawEvidence = json['motivos'];
    final rawIndicators = json['indicadores'];

    return AnalisisResult(
      risk: risk,
      state: json['estado'] as String? ?? 'parcial',
      summary: json['resumen'] as String? ?? '',
      reasons: rawEvidence is List
          ? rawEvidence
              .whereType<Map<String, dynamic>>()
              .map(AnalysisEvidence.fromJson)
              .toList(growable: false)
          : const [],
      advice: json['consejo'] as String? ?? '',
      indicators: rawIndicators is List
          ? rawIndicators
              .whereType<Map<String, dynamic>>()
              .map(IndicatorFinding.fromJson)
              .toList(growable: false)
          : const [],
      checks: rawChecks is Map<String, dynamic>
          ? rawChecks.map(
              (key, value) => MapEntry(
                key,
                value is Map<String, dynamic>
                    ? ServiceCheck.fromJson(value)
                    : const ServiceCheck(status: 'fallida', detail: ''),
              ),
            )
          : const {},
    );
  }
}
