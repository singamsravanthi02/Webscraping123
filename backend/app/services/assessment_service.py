from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.prompts import (
    PROMPT_VERSION_ASSESSMENT_QUESTION_GENERATION,
    assessment_question_generation_prompt,
)
from app.domain.ai_orchestration.schemas import QuestionListSchema
from app.domain.assessments.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestionMap,
    AssessmentType,
    AttemptDetail,
    AttemptStatus,
    QuestionBank,
    QuestionType,
)
from app.domain.assessments.schemas import AssessmentSubmitRequest

logger = logging.getLogger(__name__)


class AssessmentService:
    def __init__(self, db: Session):
        self.db = db

    def get_assessments(self) -> List[Assessment]:
        return self.db.query(Assessment).all()

    def start_assessment(self, user_id: int, assessment_id: int) -> AssessmentAttempt:
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        questions = self.get_assessment_questions(assessment_id)
        if not questions:
            generated_payloads = []
            try:
                generated_payloads = self._generate_question_payloads(
                    user_id=user_id,
                    subject=assessment.title,
                    topic=assessment.title,
                    difficulty=5,
                    bloom_level="Apply",
                    company_pattern=None,
                    missing_count=5,
                    existing_questions=[],
                )
            except Exception as exc:
                logger.warning("Failed to auto-generate questions for assessment %s: %s", assessment_id, exc)

            for payload in generated_payloads:
                question = QuestionBank(
                    topic=payload.get("topic") or assessment.title,
                    subject=payload.get("subject") or assessment.title,
                    difficulty=int(payload.get("difficulty") or 5),
                    type=self._question_type_from_text(payload.get("type")),
                    content=payload.get("content") or "",
                    options=payload.get("options") or {},
                    correct_answer=payload.get("correct_answer"),
                    detailed_explanation=payload.get("detailed_explanation"),
                    hints=payload.get("hints") or [],
                    common_mistakes=payload.get("common_mistakes") or [],
                    company_tags=payload.get("company_tags") or [],
                    bloom_level=payload.get("bloom_level") or "Apply",
                    placement_relevance=payload.get("placement_relevance"),
                    interview_difficulty=payload.get("interview_difficulty"),
                    company_difficulty=payload.get("company_difficulty"),
                    estimated_time=payload.get("estimated_time"),
                    marks=float(payload.get("marks") or 1.0),
                    points=float(payload.get("marks") or 1.0),
                )
                self.db.add(question)
                self.db.flush()
                self.db.add(AssessmentQuestionMap(assessment_id=assessment.id, question_id=question.id))

            if generated_payloads:
                self.db.commit()
                questions = self.get_assessment_questions(assessment_id)

        if not questions:
            raise HTTPException(status_code=503, detail="No questions available for this assessment")

        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_id=assessment_id,
            status=AttemptStatus.IN_PROGRESS,
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_assessment_questions(self, assessment_id: int) -> List[QuestionBank]:
        return (
            self.db.query(QuestionBank)
            .join(AssessmentQuestionMap, QuestionBank.id == AssessmentQuestionMap.question_id)
            .filter(AssessmentQuestionMap.assessment_id == assessment_id)
            .all()
        )

    def submit_assessment(self, user_id: int, request: AssessmentSubmitRequest):
        attempt = (
            self.db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.id == request.attempt_id,
                AssessmentAttempt.user_id == user_id,
            )
            .first()
        )

        if not attempt or attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Invalid or already submitted attempt")

        assessment = attempt.assessment

        question_ids = [ans.question_id for ans in request.answers]
        questions = self.db.query(QuestionBank).filter(QuestionBank.id.in_(question_ids)).all()
        question_map = {q.id: q for q in questions}

        total_score = 0.0
        for ans in request.answers:
            question = question_map.get(ans.question_id)
            is_correct = False
            if question and question.correct_answer == ans.user_answer:
                is_correct = True
                total_score += question.points
            elif question and assessment.negative_mark_weight > 0:
                total_score -= question.points * assessment.negative_mark_weight

            detail = AttemptDetail(
                attempt_id=attempt.id,
                question_id=ans.question_id,
                user_answer=ans.user_answer,
                is_correct=is_correct,
                time_taken_seconds=ans.time_taken_seconds,
            )
            self.db.add(detail)

        attempt.score = total_score
        attempt.status = AttemptStatus.SUBMITTED
        attempt.end_time = datetime.now(timezone.utc)
        attempt.tab_switch_count = request.tab_switch_count
        attempt.fullscreen_violations = request.fullscreen_violations

        self.db.commit()

        return {
            "attempt_id": attempt.id,
            "score": total_score,
            "total_marks": assessment.total_marks,
            "status": attempt.status,
            "tab_switch_count": attempt.tab_switch_count,
            "ai_recommendations": [
                f"Your score: {total_score}/{assessment.total_marks}",
                "Review the topics you got wrong to improve next time.",
            ],
        }

    def _normalize(self, value: Any) -> str:
        return " ".join(str(value or "").split()).strip().lower()

    def _normalize_tags(self, tags: Any) -> list[str]:
        values = tags or []
        normalized = {self._normalize(tag) for tag in values if self._normalize(tag)}
        return sorted(normalized)

    def _question_payload(self, question: QuestionBank | dict[str, Any]) -> dict[str, Any]:
        if isinstance(question, dict):
            payload = dict(question)
        else:
            payload = {
                "subject": question.subject,
                "topic": question.topic,
                "type": getattr(question.type, "value", question.type),
                "difficulty": question.difficulty,
                "content": question.content,
                "options": question.options or {},
                "correct_answer": question.correct_answer,
                "bloom_level": question.bloom_level,
                "company_tags": question.company_tags or [],
                "hints": question.hints or [],
                "common_mistakes": question.common_mistakes or [],
                "detailed_explanation": question.detailed_explanation,
                "marks": question.marks or question.points or 1.0,
                "estimated_time": question.estimated_time,
                "placement_relevance": question.placement_relevance,
                "company_difficulty": question.company_difficulty,
                "interview_difficulty": question.interview_difficulty,
            }
        payload["company_tags"] = self._normalize_tags(payload.get("company_tags"))
        payload["options"] = payload.get("options") or {}
        payload["hints"] = list(payload.get("hints") or [])
        payload["common_mistakes"] = list(payload.get("common_mistakes") or [])
        return payload

    def _question_options(self, options: Any) -> list[str]:
        if isinstance(options, dict):
            return [str(value) for _, value in sorted(options.items()) if str(value).strip()]
        if isinstance(options, (list, tuple, set)):
            return [str(value) for value in options if str(value).strip()]
        if not options:
            return []
        if isinstance(options, str):
            try:
                parsed = json.loads(options)
            except Exception:
                return [options]
            return self._question_options(parsed)
        return [str(options)]

    def _question_response(self, question: QuestionBank | dict[str, Any]) -> dict[str, Any]:
        payload = self._question_payload(question)
        if not isinstance(question, dict):
            payload["id"] = question.id
        payload["options"] = self._question_options(payload.get("options"))
        return payload

    def _question_signature(self, payload: dict[str, Any]) -> str:
        normalized = {
            "subject": self._normalize(payload.get("subject")),
            "topic": self._normalize(payload.get("topic")),
            "type": self._normalize(payload.get("type") or "mcq"),
            "difficulty": int(payload.get("difficulty") or 0),
            "content": self._normalize(payload.get("content")),
            "correct_answer": self._normalize(payload.get("correct_answer")),
            "bloom_level": self._normalize(payload.get("bloom_level")),
            "company_tags": self._normalize_tags(payload.get("company_tags") or []),
            "options": payload.get("options") or {},
        }
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _question_type_from_text(self, value: Any) -> QuestionType:
        normalized = self._normalize(value)
        if normalized in {"coding", "code"}:
            return QuestionType.CODING
        if normalized in {"subjective", "essay", "short_answer"}:
            return QuestionType.SUBJECTIVE
        return QuestionType.MCQ

    def _matching_questions(
        self,
        *,
        subject: str | None,
        topic: str | None,
        difficulty: int | None,
        bloom_level: str | None,
        company_pattern: str | None,
    ) -> List[QuestionBank]:
        query = self.db.query(QuestionBank)
        if subject:
            query = query.filter(QuestionBank.subject.ilike(f"%{subject}%"))
        if topic:
            query = query.filter(QuestionBank.topic.ilike(f"%{topic}%"))
        if difficulty is not None:
            query = query.filter(QuestionBank.difficulty == difficulty)

        questions = query.order_by(QuestionBank.id.asc()).all()
        if not bloom_level and not company_pattern:
            return questions

        bloom_needle = self._normalize(bloom_level) if bloom_level else ""
        company_needle = self._normalize(company_pattern) if company_pattern else ""
        preferred: list[tuple[int, QuestionBank]] = []
        fallback: List[QuestionBank] = []
        for question in questions:
            payload = self._question_payload(question)
            score = 0
            if bloom_needle and bloom_needle in self._normalize(payload.get("bloom_level")):
                score += 1
            if company_needle and company_needle in self._normalize_tags(payload.get("company_tags") or []):
                score += 1
            if score:
                preferred.append((score, question))
            else:
                fallback.append(question)

        preferred.sort(key=lambda item: (-item[0], item[1].id))
        questions = [question for _, question in preferred] + fallback
        return questions

    def _generate_question_payloads(
        self,
        *,
        user_id: int,
        subject: str | None,
        topic: str | None,
        difficulty: int | None,
        bloom_level: str | None,
        company_pattern: str | None,
        missing_count: int,
        existing_questions: List[QuestionBank],
    ) -> List[dict[str, Any]]:
        prompt = assessment_question_generation_prompt(
            {
                "subject": subject or "General",
                "topic": topic or "General",
                "difficulty": difficulty or 5,
                "bloom_level": bloom_level or "Apply",
                "company_tags": [company_pattern] if company_pattern else [],
            },
            [self._question_payload(question) for question in existing_questions],
            missing_count,
        )
        response = gateway.generate_structured_response(
            prompt=prompt,
            schema_model=QuestionListSchema,
            use_pro=True,
            user_id=user_id,
            feature="assessment_question_generation",
            prompt_version=PROMPT_VERSION_ASSESSMENT_QUESTION_GENERATION,
        )

        seen = {self._question_signature(self._question_payload(question)) for question in existing_questions}
        payloads: List[dict[str, Any]] = []
        for item in response.questions:
            payload = self._question_payload(item.model_dump())
            signature = self._question_signature(payload)
            if signature in seen:
                continue
            seen.add(signature)
            payloads.append(payload)
            if len(payloads) >= missing_count:
                break
        return payloads

    def generate_dynamic_quiz(
        self,
        *,
        user_id: int,
        subject: str | None = None,
        topic: str | None = None,
        difficulty: int | None = None,
        bloom_level: str | None = None,
        company_pattern: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        existing_questions = self._matching_questions(
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            bloom_level=bloom_level,
            company_pattern=company_pattern,
        )

        selected_questions = list(existing_questions[:limit])
        missing_count = max(limit - len(selected_questions), 0)
        created_questions: List[QuestionBank] = []

        if missing_count > 0:
            try:
                generated_payloads = self._generate_question_payloads(
                    user_id=user_id,
                    subject=subject,
                    topic=topic,
                    difficulty=difficulty,
                    bloom_level=bloom_level,
                    company_pattern=company_pattern,
                    missing_count=missing_count,
                    existing_questions=existing_questions,
                )
            except Exception as exc:
                logger.warning("Assessment question generation failed; falling back to stored questions: %s", exc)
                generated_payloads = []

            if generated_payloads:
                try:
                    for payload in generated_payloads:
                        question = QuestionBank(
                            topic=payload.get("topic") or topic or "General",
                            subject=payload.get("subject") or subject or "General",
                            difficulty=int(payload.get("difficulty") or difficulty or 5),
                            type=self._question_type_from_text(payload.get("type")),
                            content=payload.get("content") or "",
                            options=payload.get("options") or {},
                            correct_answer=payload.get("correct_answer"),
                            detailed_explanation=payload.get("detailed_explanation"),
                            hints=payload.get("hints") or [],
                            common_mistakes=payload.get("common_mistakes") or [],
                            company_tags=payload.get("company_tags") or ([] if not company_pattern else [company_pattern]),
                            bloom_level=payload.get("bloom_level") or bloom_level,
                            placement_relevance=payload.get("placement_relevance"),
                            interview_difficulty=payload.get("interview_difficulty"),
                            company_difficulty=payload.get("company_difficulty"),
                            estimated_time=payload.get("estimated_time"),
                            marks=float(payload.get("marks") or 1.0),
                            points=float(payload.get("marks") or 1.0),
                        )
                        self.db.add(question)
                        created_questions.append(question)
                    self.db.commit()
                except Exception as exc:
                    self.db.rollback()
                    logger.warning("Failed to persist generated assessment questions: %s", exc)
                    created_questions = []

        selected_questions.extend(created_questions)
        if not selected_questions:
            raise HTTPException(status_code=503, detail="No questions available for this assessment")

        selected_questions = selected_questions[:limit]
        assessment = Assessment(
            title=f"Dynamic Quiz: {subject or topic or 'Mixed'}",
            type=AssessmentType.APTITUDE,
            duration_minutes=max(len(selected_questions), 1) * 2,
            total_marks=float(sum(float(question.points or 1.0) for question in selected_questions)),
        )
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)

        for question in selected_questions:
            self.db.add(AssessmentQuestionMap(assessment_id=assessment.id, question_id=question.id))
        self.db.commit()

        return {
            "assessment_id": assessment.id,
            "questions_count": len(selected_questions),
            "total_marks": assessment.total_marks,
            "message": "Quiz generated successfully. Use /start endpoint.",
        }
