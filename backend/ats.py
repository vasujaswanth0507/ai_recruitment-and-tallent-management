import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database import (
    Application,
    Candidate,
    Job,
    Evaluation,
    get_or_create_application,
    get_all_applications,
    get_application_by_id,
    update_application_stage,
    update_application_details,
    get_ats_pipeline_counts,
    get_evaluations_for_job,
    get_all_candidates,
    get_all_jobs,
)

logger = logging.getLogger(__name__)

STAGES = ["Applied", "Screening", "Interview", "Selected", "Rejected"]

STAGE_COLORS = {
    "Applied": "#64748b",      # Slate
    "Screening": "#0284c7",    # Sky Blue
    "Interview": "#8b5cf6",    # Purple
    "Selected": "#10b981",     # Emerald Green
    "Rejected": "#ef4444",     # Red
}

STAGE_ICONS = {
    "Applied": "📥",
    "Screening": "🔍",
    "Interview": "🎙️",
    "Selected": "🎉",
    "Rejected": "🚫",
}


def sync_shortlisted_candidates_to_ats(
    db: Session, job_id: int, auto_promote_threshold: float = 75.0
) -> int:
    """
    Synchronizes evaluated candidates into the ATS pipeline for a job.
    Auto-promotes high-scoring candidates to 'Screening' or 'Interview'.
    """
    evaluations = get_evaluations_for_job(db, job_id)
    synced_count = 0

    for ev in evaluations:
        app = db.query(Application).filter(
            Application.candidate_id == ev.candidate_id,
            Application.job_id == job_id,
        ).first()

        if not app:
            initial_stage = "Screening" if ev.overall_hiring_score >= auto_promote_threshold else "Applied"
            app = Application(
                candidate_id=ev.candidate_id,
                job_id=job_id,
                stage=initial_stage,
                interview_mode="AI Mock Simulation",
                recruiter_notes=f"Auto-synced from Evaluation Matrix. Match Score: {ev.overall_hiring_score}%",
            )
            db.add(app)
            synced_count += 1

    db.commit()
    return synced_count


def get_kanban_pipeline_data(
    db: Session, job_id: Optional[int] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves all applications organized by stage for Kanban Board rendering.
    """
    applications = get_all_applications(db, job_id=job_id)
    pipeline: Dict[str, List[Dict[str, Any]]] = {stage: [] for stage in STAGES}

    for app in applications:
        cand = app.candidate
        job = app.job
        if not cand or not job:
            continue

        # Fetch candidate's evaluation for this job if available
        eval_record = db.query(Evaluation).filter(
            Evaluation.candidate_id == cand.id,
            Evaluation.job_id == job.id,
        ).first()

        score = eval_record.overall_hiring_score if eval_record else 0.0
        matched_skills = eval_record.matched_skills if eval_record else cand.skills[:4]

        card_info = {
            "app_id": app.id,
            "candidate_id": cand.id,
            "job_id": job.id,
            "candidate_name": cand.full_name,
            "email": cand.email or "N/A",
            "phone": cand.phone or "N/A",
            "job_title": job.title,
            "stage": app.stage,
            "hiring_score": score,
            "experience": cand.parsed_experience,
            "skills": cand.skills or [],
            "matched_skills": matched_skills or [],
            "interview_scheduled_at": app.interview_scheduled_at or "Not Scheduled",
            "interview_mode": app.interview_mode,
            "recruiter_notes": app.recruiter_notes or "",
            "recruiter_feedback": app.recruiter_feedback or "",
            "recruiter_rating": app.recruiter_rating,
            "updated_at": app.updated_at.strftime("%Y-%m-%d %H:%M") if app.updated_at else "",
        }

        if app.stage in pipeline:
            pipeline[app.stage].append(card_info)
        else:
            pipeline["Applied"].append(card_info)

    return pipeline


def advance_candidate_stage(db: Session, app_id: int, target_stage: str) -> Optional[Application]:
    """Moves a candidate application to a designated ATS stage."""
    if target_stage in STAGES:
        return update_application_stage(db, app_id, target_stage)
    return None


def schedule_interview(
    db: Session,
    app_id: int,
    scheduled_datetime: str,
    interview_mode: str = "AI Mock Simulation",
    recruiter_notes: Optional[str] = None,
) -> Optional[Application]:
    """Schedules an interview and advances stage to 'Interview'."""
    app = get_application_by_id(db, app_id)
    if not app:
        return None

    app.interview_scheduled_at = scheduled_datetime
    app.interview_mode = interview_mode
    app.stage = "Interview"
    if recruiter_notes:
        existing_notes = app.recruiter_notes or ""
        app.recruiter_notes = f"{existing_notes}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Scheduled: {scheduled_datetime} ({interview_mode}) - {recruiter_notes}".strip()
    
    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    return app


def record_recruiter_feedback(
    db: Session,
    app_id: int,
    feedback: str,
    rating: float = 0.0,
    new_stage: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Application]:
    """Records recruiter feedback, rating (1-5), and optional stage update."""
    app = get_application_by_id(db, app_id)
    if not app:
        return None

    app.recruiter_feedback = feedback
    app.recruiter_rating = rating
    if new_stage and new_stage in STAGES:
        app.stage = new_stage
    if notes:
        existing_notes = app.recruiter_notes or ""
        app.recruiter_notes = f"{existing_notes}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Recruiter Note: {notes}".strip()

    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    return app


def get_ats_funnel_metrics(db: Session, job_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Computes ATS recruiting funnel analytics: stage counts, conversion rates, and efficiency metrics.
    """
    counts = get_ats_pipeline_counts(db, job_id=job_id)
    total_pipeline = sum(counts.values())

    applied_count = counts.get("Applied", 0) + counts.get("Screening", 0) + counts.get("Interview", 0) + counts.get("Selected", 0) + counts.get("Rejected", 0)
    selected_count = counts.get("Selected", 0)
    interview_count = counts.get("Interview", 0)
    
    conversion_rate = (selected_count / applied_count * 100.0) if applied_count > 0 else 0.0
    interview_rate = (interview_count / applied_count * 100.0) if applied_count > 0 else 0.0

    return {
        "counts": counts,
        "total_active": total_pipeline,
        "selected_count": selected_count,
        "conversion_rate": round(conversion_rate, 1),
        "interview_rate": round(interview_rate, 1),
    }
