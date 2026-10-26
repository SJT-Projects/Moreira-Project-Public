class QuizQuestion {
  const QuizQuestion({
    required this.id,
    required this.prompt,
    required this.options,
  });

  final String id;
  final String prompt;
  final List<String> options;

  factory QuizQuestion.fromJson(Map<String, dynamic> json) => QuizQuestion(
        id: json['id'] as String,
        prompt: json['prompt'] as String,
        options: (json['options'] as List).cast<String>(),
      );
}

class Quiz {
  const Quiz({required this.id, required this.title, required this.description, required this.questions});

  final String id;
  final String title;
  final String description;
  final List<QuizQuestion> questions;

  factory Quiz.fromJson(Map<String, dynamic> json) => Quiz(
        id: json['id'] as String,
        title: json['title'] as String,
        description: json['description'] as String,
        questions: (json['questions'] as List)
            .cast<Map<String, dynamic>>()
            .map(QuizQuestion.fromJson)
            .toList(growable: false),
      );
}

class QuizFeedback {
  const QuizFeedback({
    required this.questionId,
    required this.correct,
    required this.correctOption,
    required this.explanation,
  });

  final String questionId;
  final bool correct;
  final int correctOption;
  final String explanation;

  factory QuizFeedback.fromJson(Map<String, dynamic> json) => QuizFeedback(
        questionId: json['question_id'] as String,
        correct: json['correct'] as bool,
        correctOption: json['correct_option'] as int,
        explanation: json['explanation'] as String,
      );
}

class QuizAttemptResult {
  const QuizAttemptResult({
    required this.score,
    required this.correctAnswers,
    required this.totalQuestions,
    required this.feedback,
  });

  final int score;
  final int correctAnswers;
  final int totalQuestions;
  final List<QuizFeedback> feedback;

  factory QuizAttemptResult.fromJson(Map<String, dynamic> json) => QuizAttemptResult(
        score: json['score'] as int,
        correctAnswers: json['correct_answers'] as int,
        totalQuestions: json['total_questions'] as int,
        feedback: (json['feedback'] as List)
            .cast<Map<String, dynamic>>()
            .map(QuizFeedback.fromJson)
            .toList(growable: false),
      );
}

class QuizProgress {
  const QuizProgress({
    required this.completedAttempts,
    required this.bestScore,
    this.lastScore,
  });

  final int completedAttempts;
  final int bestScore;
  final int? lastScore;

  factory QuizProgress.fromJson(Map<String, dynamic> json) => QuizProgress(
        completedAttempts: json['completed_attempts'] as int? ?? 0,
        bestScore: json['best_score'] as int? ?? 0,
        lastScore: json['last_score'] as int?,
      );
}
