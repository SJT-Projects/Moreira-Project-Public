from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuizAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=64)
    selected_option: int = Field(ge=0, le=5)


class QuizAttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[QuizAnswer] = Field(min_length=1, max_length=30)


class QuizOptionFeedback(BaseModel):
    question_id: str
    correct: bool
    correct_option: int
    explanation: str


class QuizAttemptResult(BaseModel):
    quiz_id: str
    score: int
    correct_answers: int
    total_questions: int
    completed_at: str
    feedback: list[QuizOptionFeedback]


class QuizProgress(BaseModel):
    completed_attempts: int = 0
    best_score: int = 0
    last_score: int | None = None
    last_completed_at: str | None = None
