from __future__ import annotations

from typing import Any

from app.schemas.academy import QuizAttemptCreate
from app.repositories.firestore_repository import RepositoryUnavailable


_QUIZ_ID = "anti-estafas"
_QUIZ = {
    "id": _QUIZ_ID,
    "title": "Desafío Anti-Estafas",
    "description": "Diez situaciones cotidianas para practicar cómo detectar fraudes.",
    "questions": [
        {"id": "q1", "prompt": "Una persona de tu banco llama y exige tu clave Token. ¿Qué hacés?", "options": ["Corto la llamada; el banco nunca pide claves o tokens.", "Se la entrego para asegurar mi dinero.", "Le pido que vuelva a llamar."], "explanation": "Ninguna entidad bancaria te pedirá tu contraseña, PIN o clave Token."},
        {"id": "q2", "prompt": "Un conocido por WhatsApp te pide dinero con urgencia. ¿Qué conviene hacer?", "options": ["Transferir de inmediato.", "Llamarlo o pedir una nota de voz para verificar.", "Ignorarlo y bloquearlo."], "explanation": "Las cuentas pueden ser clonadas. Confirmá la identidad por otro canal antes de transferir."},
        {"id": "q3", "prompt": "Alguien te pide reenviar un código de 6 dígitos de WhatsApp. ¿Qué hacés?", "options": ["Lo reenvío si dice que se equivocó.", "Lo publico para consultar.", "Jamás lo comparto; puede permitir el acceso a mi cuenta."], "explanation": "Ese código es una credencial de acceso exclusiva. No lo compartas."},
        {"id": "q4", "prompt": "Un supuesto soporte técnico pide instalar AnyDesk o TeamViewer en tu celular. ¿Qué hacés?", "options": ["La instalo para que me ayuden.", "Rechazo instalarla si no inicié yo una asistencia de confianza.", "Se la recomiendo a mis amigos."], "explanation": "El control remoto puede exponer la pantalla, las cuentas y las operaciones bancarias."},
        {"id": "q5", "prompt": "Una oferta increíble exige transferencia por adelantado. ¿Qué hacés?", "options": ["Desconfío y uso un método con protección al comprador.", "Transfiero antes de que se agote.", "Envío una foto de mi tarjeta."], "explanation": "Precios inverosímiles y pagos irreversibles por adelantado son señales de alerta."},
        {"id": "q6", "prompt": "Un correo de Netflix pide actualizar tu tarjeta mediante un enlace. ¿Qué hacés?", "options": ["Abro el enlace e ingreso los datos.", "Respondo adjuntando mis datos.", "No uso el enlace; verifico desde la aplicación o sitio oficial."], "explanation": "Los mensajes de phishing imitan servicios conocidos. Entrá por el canal oficial."},
        {"id": "q7", "prompt": "Te llaman diciendo que un familiar tuvo un accidente y piden dinero urgente. ¿Qué hacés?", "options": ["Entro en pánico y preparo el dinero.", "Corto y llamo directamente al familiar para verificar.", "Doy mi dirección."], "explanation": "La urgencia y el miedo buscan impedir que verifiques. Contactá a tu familiar por un número conocido."},
        {"id": "q8", "prompt": "Ofrecen pagar mucho por dar likes, pero piden un depósito inicial. ¿Qué es?", "options": ["Una estafa que puede quedarse con el depósito.", "Una oportunidad laboral segura.", "Un bono legítimo."], "explanation": "Un trabajo legítimo no te exige pagar para empezar o cobrar."},
        {"id": "q9", "prompt": "Un QR de un bar abre una página que pide la clave bancaria. ¿Qué hacés?", "options": ["Ingreso mis claves.", "Reinicio el celular.", "Cierro la página y no ingreso credenciales."], "explanation": "Un QR puede redirigir a un sitio falso. Un menú no necesita tus claves bancarias."},
        {"id": "q10", "prompt": "Te dicen que ganaste un premio, pero debés pagar gastos para retirarlo. ¿Qué hacés?", "options": ["Pago para recibir el premio.", "No pago; puede ser una estafa.", "Pido un préstamo."], "explanation": "Los premios falsos suelen exigir pagos previos por impuestos, trámites o envíos."},
    ],
    "answers": [0, 1, 2, 1, 0, 2, 1, 0, 2, 1],
}


class AcademyService:
    def __init__(self, repository: Any):
        self._repository = repository

    def get_quiz(self, quiz_id: str) -> dict[str, Any]:
        if quiz_id != _QUIZ_ID:
            raise KeyError(quiz_id)
        public = {key: value for key, value in _QUIZ.items() if key != "answers"}
        public["questions"] = [
            {key: value for key, value in question.items() if key != "explanation"}
            for question in _QUIZ["questions"]
        ]
        return public

    async def submit_attempt(self, uid: str, quiz_id: str, request: QuizAttemptCreate) -> dict[str, Any]:
        if quiz_id != _QUIZ_ID:
            raise KeyError(quiz_id)
        expected = {question["id"]: index for index, question in enumerate(_QUIZ["questions"])}
        supplied = {answer.question_id: answer.selected_option for answer in request.answers}
        if len(supplied) != len(request.answers) or set(supplied) != set(expected):
            raise ValueError("La respuesta debe incluir cada pregunta del cuestionario una sola vez.")

        feedback = []
        correct_count = 0
        for question_id, index in expected.items():
            question = _QUIZ["questions"][index]
            selected = supplied[question_id]
            if selected >= len(question["options"]):
                raise ValueError("Una de las opciones seleccionadas no es válida.")
            correct_option = _QUIZ["answers"][index]
            correct = selected == correct_option
            correct_count += int(correct)
            feedback.append({
                "question_id": question_id,
                "correct": correct,
                "correct_option": correct_option,
                "explanation": question["explanation"],
            })

        score = correct_count * 10
        try:
            return await self._repository.save_quiz_attempt(
                uid=uid, quiz_id=quiz_id, score=score,
                correct_answers=correct_count, total_questions=len(expected), feedback=feedback,
            )
        except RepositoryUnavailable:
            raise
