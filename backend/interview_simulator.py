import re
import json
import logging
import io
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from database import Candidate, Job, InterviewSession, InterviewQuestion

logger = logging.getLogger(__name__)


class AnswerEvaluation(BaseModel):
    relevance_score: float = Field(0.0, description="Technical accuracy and relevance (0-100)")
    clarity_score: float = Field(0.0, description="Communication clarity and structure (0-100)")
    confidence_score: float = Field(0.0, description="Estimated confidence and depth (0-100)")
    confidence_level: str = Field("Moderate", description="High, Moderate, or Developing")
    technical_feedback: str = Field("", description="Detailed feedback on technical content")
    communication_feedback: str = Field("", description="Feedback on communication, structure, tone")
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified in the answer")
    improvements: List[str] = Field(default_factory=list, description="Specific recommendations for improvement")
    follow_up_triggered: bool = Field(False, description="Whether a follow-up probe is recommended")
    suggested_follow_up: str = Field("", description="Dynamic follow-up question")


class SessionReport(BaseModel):
    total_score: float
    technical_score: float
    communication_score: float
    confidence_score: float
    confidence_level: str
    strengths: List[str]
    improvements: List[str]
    summary_report: str
    hiring_recommendation: str


# ==============================================================================
# AI EVALUATION ENGINE (LLM + DETERMINISTIC OFFLINE HEURISTIC)
# ==============================================================================

def evaluate_single_answer(
    question_text: str,
    target_skill: str,
    ideal_answer: str,
    candidate_response: str,
    provider: str = "google",
    api_key: Optional[str] = None,
) -> AnswerEvaluation:
    """
    Evaluates a candidate's single interview answer (text or voice transcript).
    Computes technical relevance, communication clarity, confidence, strengths, and improvement suggestions.
    """
    response_clean = candidate_response.strip()
    if not response_clean or len(response_clean) < 10:
        return AnswerEvaluation(
            relevance_score=15.0,
            clarity_score=20.0,
            confidence_score=15.0,
            confidence_level="Developing",
            technical_feedback="The response was too brief or incomplete to demonstrate required domain proficiency.",
            communication_feedback="Candidate provided minimal elaboration. Structure and detail are lacking.",
            strengths=["Attempted to address the question."],
            improvements=["Provide concrete examples, architectural context, and structured explanations."],
            follow_up_triggered=True,
            suggested_follow_up="Could you elaborate on how you have applied this concept in a real-world project?",
        )

    # 1. Attempt LLM Evaluation if API Key is configured
    if api_key:
        try:
            prompt = f"""
You are an expert technical interviewer and AI hiring assessor.
Evaluate the candidate's interview response against the question and ideal benchmark.

QUESTION: {question_text}
TARGET SKILL: {target_skill}
IDEAL BENCHMARK ANSWER: {ideal_answer}

CANDIDATE'S RESPONSE:
{response_clean}

Requirements:
1. Technical Relevance Score (0-100): Evaluate correctness, technical depth, and coverage of core concepts.
2. Communication Clarity Score (0-100): Evaluate structure, articulation, precision, and logical flow.
3. Confidence Score (0-100) and Level (High, Moderate, Developing): Assess certainty and authoritative phrasing.
4. Specific strengths demonstrated in the response (2-3 bullet points).
5. Actionable improvement suggestions (2-3 bullet points).
6. Recommend if a follow-up question is warranted and provide the follow-up question text.

Return a JSON object conforming to:
{{
  "relevance_score": 85.0,
  "clarity_score": 90.0,
  "confidence_score": 88.0,
  "confidence_level": "High",
  "technical_feedback": "...",
  "communication_feedback": "...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "follow_up_triggered": true,
  "suggested_follow_up": "..."
}}
"""
            if provider.lower() in ["google", "gemini"]:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=api_key)
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    return AnswerEvaluation(**json.loads(res.text))
                except Exception:
                    import google.generativeai as genai

                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    res = model.generate_content(
                        prompt, generation_config={"response_mime_type": "application/json"}
                    )
                    return AnswerEvaluation(**json.loads(res.text))

            elif provider.lower() in ["openai", "gpt-4"]:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert technical interviewer."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                return AnswerEvaluation(**json.loads(res.choices[0].message.content))

        except Exception as e:
            logger.warning(f"LLM answer evaluation failed: {e}. Falling back to deterministic engine.")

    # 2. Deterministic Offline Heuristic Evaluation Engine
    response_words = set(re.findall(r"\b\w{3,}\b", response_clean.lower()))
    word_count = len(response_clean.split())
    ideal_words = set(re.findall(r"\b\w{3,}\b", ideal_answer.lower()))

    # Calculate keyword coverage against benchmark
    matched_keywords = [w for w in ideal_words if w in response_words]
    keyword_ratio = (len(matched_keywords) / max(1, len(ideal_words))) if ideal_words else 0.6

    # Depth & Length bonus
    length_factor = min(1.0, word_count / 30.0)

    # Technical relevance calculation
    relevance_raw = (keyword_ratio * 70.0) + (length_factor * 30.0)
    relevance_score = round(max(30.0, min(98.0, relevance_raw)), 1)

    # Clarity calculation based on sentence structure and transitional words
    transitions = ["because", "therefore", "for example", "furthermore", "however", "additionally", "firstly", "in order to", "specifically"]
    trans_count = sum(1 for t in transitions if t in response_clean.lower())
    clarity_raw = 50.0 + min(35.0, trans_count * 10.0) + (15.0 if word_count >= 40 else 0.0)
    clarity_score = round(min(95.0, clarity_raw), 1)

    # Confidence calculation
    hesitations = ["maybe", "i think", "probably", "not sure", "guess", "kind of", "sort of"]
    hesitation_count = sum(1 for h in hesitations if h in response_clean.lower())
    confidence_raw = 85.0 - (hesitation_count * 12.0) + (10.0 if word_count >= 50 else -10.0)
    confidence_score = round(max(25.0, min(95.0, confidence_raw)), 1)

    if confidence_score >= 75.0:
        conf_level = "High"
    elif confidence_score >= 50.0:
        conf_level = "Moderate"
    else:
        conf_level = "Developing"

    # Feedback generation
    tech_feedback = (
        f"Demonstrated good awareness of {target_skill.title()} concepts. "
        f"Included key relevant terminology ({', '.join(matched_keywords[:3]) if matched_keywords else 'general concepts'}). "
        + ("Could elaborate further on underlying mechanics and edge-case handling." if relevance_score < 80 else "Strong conceptual grounding.")
    )

    comm_feedback = (
        f"Articulated answer with {word_count} words and clear phrasing. "
        + ("Well structured with logical connectors." if trans_count >= 2 else "Could enhance structure by using the STAR method or bullet points.")
    )

    strengths = [
        f"Directly engaged with the {target_skill.title()} problem domain.",
        "Demonstrated clear technical vocabulary and articulate reasoning." if word_count >= 40 else "Kept the response concise and focused.",
    ]

    improvements = [
        "Include more concrete architectural trade-offs or production lessons learned.",
        "Quantify business or performance impact (e.g. latency, throughput, memory reduction).",
    ]

    return AnswerEvaluation(
        relevance_score=relevance_score,
        clarity_score=clarity_score,
        confidence_score=confidence_score,
        confidence_level=conf_level,
        technical_feedback=tech_feedback,
        communication_feedback=comm_feedback,
        strengths=strengths,
        improvements=improvements,
        follow_up_triggered=relevance_score < 75.0 or len(response_clean) < 50,
        suggested_follow_up=f"Can you provide a specific production example where you applied {target_skill.title()} to solve a scalability or performance issue?",
    )


def generate_overall_interview_report(
    evaluations: List[AnswerEvaluation],
    candidate_name: str,
    job_title: str,
    provider: str = "google",
    api_key: Optional[str] = None,
) -> SessionReport:
    """
    Computes overall interview performance metrics, composite score, strengths, improvement areas, and hiring verdict.
    """
    if not evaluations:
        return SessionReport(
            total_score=0.0,
            technical_score=0.0,
            communication_score=0.0,
            confidence_score=0.0,
            confidence_level="N/A",
            strengths=[],
            improvements=[],
            summary_report="No interview answers recorded.",
            hiring_recommendation="Consider",
        )

    avg_rel = sum(e.relevance_score for e in evaluations) / len(evaluations)
    avg_clarity = sum(e.clarity_score for e in evaluations) / len(evaluations)
    avg_conf = sum(e.confidence_score for e in evaluations) / len(evaluations)

    # Composite interview score (50% technical relevance, 30% clarity, 20% confidence)
    total_score = (0.50 * avg_rel) + (0.30 * avg_clarity) + (0.20 * avg_conf)

    if avg_conf >= 75.0:
        conf_level = "High"
    elif avg_conf >= 50.0:
        conf_level = "Moderate"
    else:
        conf_level = "Developing"

    # Hiring Recommendation logic
    if total_score >= 82.0:
        recommendation = "Strong Hire"
    elif total_score >= 70.0:
        recommendation = "Hire"
    elif total_score >= 55.0:
        recommendation = "Consider"
    else:
        recommendation = "Do Not Hire"

    # Aggregate strengths & improvements
    all_strengths = []
    all_improvements = []
    for e in evaluations:
        all_strengths.extend(e.strengths)
        all_improvements.extend(e.improvements)

    unique_strengths = list(dict.fromkeys(all_strengths))[:4]
    unique_improvements = list(dict.fromkeys(all_improvements))[:4]

    summary = (
        f"Candidate {candidate_name} completed the AI Technical Interview Simulation for the position of '{job_title}'. "
        f"Overall Performance Score: {total_score:.1f}% (Technical Relevance: {avg_rel:.1f}%, Communication Clarity: {avg_clarity:.1f}%, Confidence: {avg_conf:.1f}%). "
        f"Assessment Outcome: {recommendation}."
    )

    return SessionReport(
        total_score=round(total_score, 1),
        technical_score=round(avg_rel, 1),
        communication_score=round(avg_clarity, 1),
        confidence_score=round(avg_conf, 1),
        confidence_level=conf_level,
        strengths=unique_strengths,
        improvements=unique_improvements,
        summary_report=summary,
        hiring_recommendation=recommendation,
    )


# ==============================================================================
# REPORTLAB PDF GENERATOR FOR INTERVIEW PERFORMANCE REPORT
# ==============================================================================

def export_interview_report_pdf(
    session: InterviewSession,
    candidate: Candidate,
    job: Job,
    questions: List[InterviewQuestion],
) -> bytes:
    """
    Generates a high-quality, professional executive PDF of the candidate's AI Interview Performance Report.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        leading=14,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_style = ParagraphStyle(
        "BoldBody",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("AI Recruitment Copilot — Interview Performance Report", title_style))
    story.append(Paragraph(f"Generated on {session.created_at.strftime('%B %d, %Y at %H:%M UTC')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=15))

    # Candidate & Role Summary Table
    meta_data = [
        [
            Paragraph("<b>Candidate Name:</b>", bold_style),
            Paragraph(candidate.full_name, body_style),
            Paragraph("<b>Target Role:</b>", bold_style),
            Paragraph(job.title, body_style),
        ],
        [
            Paragraph("<b>Email Address:</b>", bold_style),
            Paragraph(candidate.email or "N/A", body_style),
            Paragraph("<b>Overall Score:</b>", bold_style),
            Paragraph(f"<b>{session.total_score}%</b> ({session.hiring_recommendation})", bold_style),
        ],
        [
            Paragraph("<b>Experience:</b>", bold_style),
            Paragraph(f"{candidate.parsed_experience} years", body_style),
            Paragraph("<b>Confidence:</b>", bold_style),
            Paragraph(f"{session.confidence_level} ({session.confidence_score}%)", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[100, 160, 100, 160])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Performance Score Breakdown Table
    story.append(Paragraph("Competency & Performance Breakdown", section_style))
    score_data = [
        ["Evaluation Dimension", "Score", "Rating Benchmark", "Assessment Outcome"],
        ["Technical Accuracy & Relevance", f"{session.technical_score}%", "0 - 100%", "Demonstrated Domain Mastery"],
        ["Communication Clarity & Structure", f"{session.communication_score}%", "0 - 100%", "Articulation & STAR Format"],
        ["Confidence & Depth", f"{session.confidence_score}%", "0 - 100%", session.confidence_level],
        ["Composite Hiring Score", f"{session.total_score}%", "0 - 100%", session.hiring_recommendation],
    ]
    score_table = Table(score_data, colWidths=[180, 70, 110, 160])
    score_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(score_table)
    story.append(Spacer(1, 15))

    # Strengths & Improvement Areas
    story.append(Paragraph("Key Strengths & Growth Areas", section_style))
    strength_paragraphs = [Paragraph(f"• {s}", body_style) for s in (session.strengths or ["No specific strengths recorded."])]
    improvement_paragraphs = [Paragraph(f"• {i}", body_style) for i in (session.improvements or ["Continue maintaining standard best practices."])]
    
    col1_content = [Paragraph("<b>Identified Strengths:</b>", bold_style), Spacer(1, 4)] + strength_paragraphs
    col2_content = [Paragraph("<b>Areas for Improvement:</b>", bold_style), Spacer(1, 4)] + improvement_paragraphs

    si_table = Table([[col1_content, col2_content]], colWidths=[260, 260])
    si_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f0fdf4")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fef2f2")),
            ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#86efac")),
            ("BOX", (1, 0), (1, 0), 1, colors.HexColor("#fca5a5")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(si_table)
    story.append(Spacer(1, 15))

    # Question-by-Question Transcript & AI Evaluation
    story.append(Paragraph("Interview Question Transcript & AI Evaluations", section_style))
    if questions:
        for idx, q in enumerate(questions, 1):
            q_box = [
                [
                    Paragraph(f"<b>Q{idx}: {q.question_text}</b>", bold_style),
                    Paragraph(f"<b>Score:</b> {q.relevance_score}%", bold_style),
                ],
                [
                    Paragraph(f"<b>Candidate Answer:</b> {q.candidate_response or 'No answer provided.'}", body_style),
                    Paragraph(f"<b>Target:</b> {q.target_skill.title()} ({q.difficulty})", subtitle_style),
                ],
                [
                    Paragraph(f"<b>AI Feedback:</b> {q.ai_feedback or 'Evaluated successfully.'}", subtitle_style),
                    Paragraph("", subtitle_style),
                ],
            ]
            q_table = Table(q_box, colWidths=[420, 100])
            q_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            story.append(q_table)
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No detailed question records found.", body_style))

    # Executive Summary & Recommendation Footer
    story.append(Spacer(1, 10))
    story.append(Paragraph("Executive Hiring Recommendation", section_style))
    story.append(Paragraph(f"<b>Final Verdict: {session.hiring_recommendation.upper()}</b> — {session.summary_report}", body_style))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
