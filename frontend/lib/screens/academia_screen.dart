import 'package:flutter/material.dart';

import '../models/quiz.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ui_calida.dart';

class AcademiaScreen extends StatefulWidget {
  const AcademiaScreen({super.key});

  @override
  State<AcademiaScreen> createState() => _AcademiaScreenState();
}

class _AcademiaScreenState extends State<AcademiaScreen> {
  final _api = ApiService();
  Quiz? _quiz;
  QuizProgress? _progress;
  QuizAttemptResult? _result;
  final Map<String, int> _answers = {};
  int _current = 0;
  bool _loading = true;
  bool _submitting = false;
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
      final quiz = await _api.obtenerCuestionario('anti-estafas');
      QuizProgress? progress;
      try {
        progress = await _api.obtenerProgresoAcademico();
      } catch (_) {
        // Reading the learning material should still work if stored progress is down.
      }
      if (!mounted) return;
      setState(() {
        _quiz = quiz;
        _progress = progress;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  Future<void> _finishQuiz() async {
    final quiz = _quiz;
    if (quiz == null || _answers.length != quiz.questions.length) return;
    setState(() => _submitting = true);
    try {
      final result = await _api.enviarIntento(quiz.id, _answers);
      QuizProgress? progress;
      try {
        progress = await _api.obtenerProgresoAcademico();
      } catch (_) {
        // The attempt response remains valid even when refreshing the summary fails.
      }
      if (!mounted) return;
      setState(() {
        _result = result;
        _progress = progress;
        _submitting = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _submitting = false;
      });
    }
  }

  void _restart() {
    setState(() {
      _answers.clear();
      _current = 0;
      _result = null;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const CenteredMessage(emoji: '⏳', message: 'Preparando las lecciones...');
    }
    if (_error != null && _quiz == null) {
      return CenteredMessage(
        emoji: '📚',
        message: _error!,
        action: FilledButton.icon(
          onPressed: _load,
          icon: const Icon(Icons.refresh),
          label: const Text('Reintentar'),
        ),
      );
    }
    final quiz = _quiz!;
    final result = _result;
    final theme = Theme.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const SectionHeader(
              emoji: '🎓',
              title: 'Academia Anti-Estafas',
              subtitle: 'Aprendé a reconocer engaños comunes y practicá cómo responder. ¡Sin apuro!',
            ),
            const SizedBox(height: 20),
            if (_progress case final progress?)
              Card(
                color: AppColors.mielClaro,
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Row(
                    children: [
                      const Emoji('🏅', size: 40),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Tu mejor puntaje: ${progress.bestScore}/100', style: theme.textTheme.titleMedium),
                            Text(
                              'Intentos completados: ${progress.completedAttempts}',
                              style: theme.textTheme.bodyLarge,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 8),
            Text('📖 Consejos rápidos', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            const _GuideCard(emoji: '🔑', title: 'Códigos y claves', text: 'No compartas códigos de verificación, PIN, claves ni tokens, aunque el pedido parezca urgente.'),
            const _GuideCard(emoji: '🔗', title: 'Enlaces y QR', text: 'Verificá el dominio y abrí los servicios desde su aplicación o dirección oficial.'),
            const _GuideCard(emoji: '💸', title: 'Pagos y premios', text: 'Desconfiá de depósitos para acceder a un trabajo, premio u oferta extraordinaria.'),
            const SizedBox(height: 24),
            Text('🧩 ${quiz.title}', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            if (_error != null) ...[
              InfoBanner(message: _error!, kind: BannerKind.error),
              const SizedBox(height: 12),
            ],
            if (result != null)
              _resultCard(quiz, result)
            else
              _questionCard(quiz),
          ],
        ),
      ),
    );
  }

  Widget _questionCard(Quiz quiz) {
    final theme = Theme.of(context);
    final question = quiz.questions[_current];
    final selected = _answers[question.id];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            'Pregunta ${_current + 1} de ${quiz.questions.length}',
            style: theme.textTheme.labelLarge?.copyWith(color: AppColors.terracota),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: (_current + 1) / quiz.questions.length,
              minHeight: 10,
              backgroundColor: AppColors.bordeSuave,
            ),
          ),
          const SizedBox(height: 16),
          Text(question.prompt, style: theme.textTheme.titleMedium),
          const SizedBox(height: 14),
          RadioGroup<int>(
            groupValue: selected,
            onChanged: (value) {
              if (_submitting || value == null) return;
              setState(() => _answers[question.id] = value);
            },
            child: Column(
              children: List.generate(question.options.length, (index) {
                final isSelected = selected == index;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Material(
                    color: isSelected ? AppColors.durazno : Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                      side: BorderSide(
                        color: isSelected ? AppColors.terracota : AppColors.bordeSuave,
                        width: isSelected ? 3 : 1.5,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: RadioListTile<int>(
                      value: index,
                      enabled: !_submitting,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      title: Text(
                        question.options[index],
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: isSelected ? FontWeight.w700 : FontWeight.normal,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            spacing: 12,
            runSpacing: 12,
            children: [
              if (_current > 0)
                OutlinedButton.icon(
                  onPressed: _submitting ? null : () => setState(() => _current--),
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Anterior'),
                ),
              if (_current + 1 < quiz.questions.length)
                FilledButton.icon(
                  onPressed: selected == null ? null : () => setState(() => _current++),
                  icon: const Icon(Icons.arrow_forward),
                  label: const Text('Siguiente'),
                )
              else
                FilledButton.icon(
                  onPressed: selected == null || _submitting ? null : _finishQuiz,
                  icon: _submitting
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 3, color: Colors.white),
                        )
                      : const Icon(Icons.check),
                  label: const Text('Enviar respuestas'),
                ),
            ],
          ),
          if (selected == null) ...[
            const SizedBox(height: 10),
            Text(
              '👆 Elegí una respuesta para seguir.',
              style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.textoSuave),
            ),
          ],
        ]),
      ),
    );
  }

  Widget _resultCard(Quiz quiz, QuizAttemptResult result) {
    final theme = Theme.of(context);
    final feedback = {for (final item in result.feedback) item.questionId: item};
    final (emoji, cheer) = switch (result.score) {
      >= 80 => ('🏆', '¡Excelente! Sabés detectar engaños.'),
      >= 50 => ('🌟', '¡Muy bien! Repasá las respuestas para seguir mejorando.'),
      _ => ('💪', '¡Buen intento! Leé las explicaciones y volvé a probar.'),
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(
            child: Column(children: [
              Emoji(emoji, size: 64),
              const SizedBox(height: 8),
              Text('${result.score}/100', style: theme.textTheme.headlineMedium),
              Text(
                '${result.correctAnswers} de ${result.totalQuestions} respuestas correctas',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: 6),
              Text(cheer, textAlign: TextAlign.center, style: theme.textTheme.titleSmall),
            ]),
          ),
          const Divider(height: 32),
          ...quiz.questions.map((question) {
            final answer = feedback[question.id]!;
            return Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: answer.correct ? AppColors.verdeFondo : AppColors.amarilloFondo,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(
                  answer.correct ? '✅ ¡Correcta!' : '💡 Para repasar',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: answer.correct ? AppColors.verde : AppColors.amarillo,
                  ),
                ),
                const SizedBox(height: 6),
                Text(question.prompt, style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                Text(
                  'Respuesta recomendada: ${question.options[answer.correctOption]}',
                  style: theme.textTheme.bodyLarge,
                ),
                Text(answer.explanation, style: theme.textTheme.bodyLarge),
              ]),
            );
          }),
          const SizedBox(height: 6),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _restart,
              icon: const Icon(Icons.refresh),
              label: const Text('Volver a intentar'),
            ),
          ),
        ]),
      ),
    );
  }
}

class _GuideCard extends StatelessWidget {
  const _GuideCard({required this.emoji, required this.title, required this.text});

  final String emoji;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            EmojiBadge(emoji, size: 56, background: AppColors.mielClaro),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: theme.textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(text, style: theme.textTheme.bodyLarge),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
