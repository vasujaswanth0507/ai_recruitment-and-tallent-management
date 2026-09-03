import os
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    select,
    delete,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    Session,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "recruitment.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ==============================================================================
# USER & ACCESS CONTROL MODEL
# ==============================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), default="password123")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="Recruiter")  # Recruiter, Candidate, Admin
    candidate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped[Optional["Candidate"]] = relationship("Candidate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "candidate_id": self.candidate_id,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


# ==============================================================================
# CORE TALENT & JOB MODELS
# ==============================================================================

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="Engineering")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    min_experience: Mapped[float] = mapped_column(Float, default=0.0)
    required_education: Mapped[str] = mapped_column(String(255), default="Bachelor's")
    certifications: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    evaluations: Mapped[List["Evaluation"]] = relationship(
        "Evaluation", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="job", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "role": self.role,
            "department": self.department,
            "description": self.description,
            "required_skills": self.required_skills or [],
            "min_experience": self.min_experience,
            "required_education": self.required_education,
            "certifications": self.certifications or [],
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.created_at
            else "",
        }


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_experience: Mapped[float] = mapped_column(Float, default=0.0)
    parsed_education: Mapped[List[str]] = mapped_column(JSON, default=list)
    skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    projects: Mapped[List[str]] = mapped_column(JSON, default=list)
    certifications: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    evaluations: Mapped[List["Evaluation"]] = relationship(
        "Evaluation", back_populates="candidate", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="candidate", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email or "N/A",
            "phone": self.phone or "N/A",
            "parsed_experience": self.parsed_experience,
            "parsed_education": self.parsed_education or [],
            "skills": self.skills or [],
            "projects": self.projects or [],
            "certifications": self.certifications or [],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.created_at
            else "",
        }


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    skill_match_pct: Mapped[float] = mapped_column(Float, default=0.0)
    overall_hiring_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    additional_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="evaluations")
    job: Mapped["Job"] = relationship("Job", back_populates="evaluations")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "skill_match_pct": round(self.skill_match_pct, 2),
            "overall_hiring_score": round(self.overall_hiring_score, 2),
            "matched_skills": self.matched_skills or [],
            "missing_skills": self.missing_skills or [],
            "additional_skills": self.additional_skills or [],
            "rank": self.rank,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.created_at
            else "",
        }


# ==============================================================================
# ATS APPLICATION & INTERVIEW MODELS
# ==============================================================================

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(50), default="Applied")  # Applied, Screening, Interview, Selected, Rejected
    interview_scheduled_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interview_mode: Mapped[str] = mapped_column(String(50), default="AI Mock Simulation")
    recruiter_notes: Mapped[str] = mapped_column(Text, default="")
    recruiter_feedback: Mapped[str] = mapped_column(Text, default="")
    recruiter_rating: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="application"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "stage": self.stage,
            "interview_scheduled_at": self.interview_scheduled_at or "Not Scheduled",
            "interview_mode": self.interview_mode,
            "recruiter_notes": self.recruiter_notes,
            "recruiter_feedback": self.recruiter_feedback,
            "recruiter_rating": self.recruiter_rating,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="completed")  # in_progress, completed
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    communication_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(50), default="Moderate")
    strengths: Mapped[List[str]] = mapped_column(JSON, default=list)
    improvements: Mapped[List[str]] = mapped_column(JSON, default=list)
    summary_report: Mapped[str] = mapped_column(Text, default="")
    hiring_recommendation: Mapped[str] = mapped_column(String(50), default="Hire")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="interview_sessions")
    job: Mapped["Job"] = relationship("Job", back_populates="interview_sessions")
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="interview_sessions")
    questions: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="session", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "application_id": self.application_id,
            "status": self.status,
            "total_score": round(self.total_score, 1),
            "technical_score": round(self.technical_score, 1),
            "communication_score": round(self.communication_score, 1),
            "confidence_score": round(self.confidence_score, 1),
            "confidence_level": self.confidence_level,
            "strengths": self.strengths or [],
            "improvements": self.improvements or [],
            "summary_report": self.summary_report,
            "hiring_recommendation": self.hiring_recommendation,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=True
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True
    )
    candidate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), default="technical")
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_skill: Mapped[str] = mapped_column(String(100), default="")
    sample_ideal_answer: Mapped[str] = mapped_column(Text, default="")
    follow_up_question: Mapped[str] = mapped_column(Text, default="")
    candidate_response: Mapped[str] = mapped_column(Text, default="")
    input_mode: Mapped[str] = mapped_column(String(20), default="text")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    clarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped[Optional["InterviewSession"]] = relationship("InterviewSession", back_populates="questions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "job_id": self.job_id,
            "candidate_id": self.candidate_id,
            "category": self.category,
            "difficulty": self.difficulty,
            "question_text": self.question_text,
            "target_skill": self.target_skill,
            "sample_ideal_answer": self.sample_ideal_answer,
            "follow_up_question": self.follow_up_question,
            "candidate_response": self.candidate_response,
            "input_mode": self.input_mode,
            "relevance_score": round(self.relevance_score, 1),
            "clarity_score": round(self.clarity_score, 1),
            "ai_feedback": self.ai_feedback,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


# ==============================================================================
# DATABASE INITIALIZATION & CRUD
# ==============================================================================

def init_db():
    """Initializes all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- User CRUD ---

def save_user(db: Session, user_data: dict[str, Any]) -> User:
    user = db.scalar(select(User).where(User.username == user_data["username"]))
    if not user:
        user = User(
            username=user_data["username"],
            password=user_data.get("password", "password123"),
            full_name=user_data.get("full_name", user_data["username"]),
            email=user_data.get("email", f"{user_data['username']}@company.com"),
            role=user_data.get("role", "Recruiter"),
            candidate_id=user_data.get("candidate_id"),
            is_active=user_data.get("is_active", True),
        )
        db.add(user)
    else:
        if "password" in user_data:
            user.password = user_data["password"]
        user.full_name = user_data.get("full_name", user.full_name)
        user.email = user_data.get("email", user.email)
        user.role = user_data.get("role", user.role)
        user.candidate_id = user_data.get("candidate_id", user.candidate_id)
        user.is_active = user_data.get("is_active", user.is_active)
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session, role: Optional[str] = None) -> List[User]:
    query = select(User)
    if role and role != "All":
        query = query.where(User.role == role)
    return list(db.scalars(query.order_by(User.created_at.desc())).all())


def delete_user(db: Session, user_id: int) -> bool:
    user = db.scalar(select(User).where(User.id == user_id))
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


def authenticate_user(
    db: Session, username: str, password: str, expected_role: Optional[str] = None
) -> Optional[User]:
    """Authenticates user with username & password, checking role if specified."""
    query = select(User).where(User.username == username.strip(), User.password == password.strip(), User.is_active == True)
    if expected_role:
        query = query.where(User.role == expected_role)
    return db.scalar(query)



# --- Job CRUD ---

def save_job(db: Session, job_data: dict[str, Any]) -> Job:
    job = Job(
        title=job_data["title"],
        role=job_data.get("role", job_data["title"]),
        department=job_data.get("department", "Engineering"),
        description=job_data.get("description", ""),
        required_skills=[s.strip().lower() for s in job_data.get("required_skills", [])],
        min_experience=float(job_data.get("min_experience", 0.0)),
        required_education=job_data.get("required_education", "Bachelor's"),
        certifications=job_data.get("certifications", []),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_all_jobs(db: Session, active_only: bool = False) -> List[Job]:
    query = select(Job)
    if active_only:
        query = query.where(Job.is_active == True)
    return list(db.scalars(query.order_by(Job.created_at.desc())).all())


def get_job_by_id(db: Session, job_id: int) -> Optional[Job]:
    return db.scalar(select(Job).where(Job.id == job_id))


def delete_job(db: Session, job_id: int) -> bool:
    job = get_job_by_id(db, job_id)
    if job:
        db.delete(job)
        db.commit()
        return True
    return False


# --- Candidate CRUD ---

def save_candidate(db: Session, candidate_data: dict[str, Any]) -> Candidate:
    candidate = Candidate(
        full_name=candidate_data.get("full_name", "Unknown Candidate"),
        email=candidate_data.get("email"),
        phone=candidate_data.get("phone"),
        raw_text=candidate_data.get("raw_text", ""),
        parsed_experience=float(candidate_data.get("parsed_experience", 0.0)),
        parsed_education=candidate_data.get("parsed_education", []),
        skills=[s.strip().lower() for s in candidate_data.get("skills", [])],
        projects=candidate_data.get("projects", []),
        certifications=candidate_data.get("certifications", []),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update_candidate(db: Session, candidate_id: int, update_data: dict[str, Any]) -> Optional[Candidate]:
    cand = get_candidate_by_id(db, candidate_id)
    if not cand:
        return None
    if "full_name" in update_data:
        cand.full_name = update_data["full_name"]
    if "email" in update_data:
        cand.email = update_data["email"]
    if "phone" in update_data:
        cand.phone = update_data["phone"]
    if "parsed_experience" in update_data:
        cand.parsed_experience = float(update_data["parsed_experience"])
    if "skills" in update_data:
        cand.skills = [s.strip().lower() for s in update_data["skills"]]
    if "projects" in update_data:
        cand.projects = update_data["projects"]
    if "certifications" in update_data:
        cand.certifications = update_data["certifications"]
    if "parsed_education" in update_data:
        cand.parsed_education = update_data["parsed_education"]
    if "raw_text" in update_data:
        cand.raw_text = update_data["raw_text"]
    db.commit()
    db.refresh(cand)
    return cand


def get_all_candidates(db: Session) -> List[Candidate]:
    return list(db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all())


def get_candidate_by_id(db: Session, candidate_id: int) -> Optional[Candidate]:
    return db.scalar(select(Candidate).where(Candidate.id == candidate_id))


def delete_candidate(db: Session, candidate_id: int) -> bool:
    cand = get_candidate_by_id(db, candidate_id)
    if cand:
        db.delete(cand)
        db.commit()
        return True
    return False


# --- Evaluation CRUD ---

def save_evaluation(db: Session, eval_data: dict[str, Any]) -> Evaluation:
    existing = db.scalar(
        select(Evaluation).where(
            Evaluation.candidate_id == eval_data["candidate_id"],
            Evaluation.job_id == eval_data["job_id"],
        )
    )
    if existing:
        existing.skill_match_pct = float(eval_data["skill_match_pct"])
        existing.overall_hiring_score = float(eval_data["overall_hiring_score"])
        existing.matched_skills = eval_data.get("matched_skills", [])
        existing.missing_skills = eval_data.get("missing_skills", [])
        existing.additional_skills = eval_data.get("additional_skills", [])
        existing.rank = int(eval_data.get("rank", 0))
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_eval = Evaluation(
            candidate_id=eval_data["candidate_id"],
            job_id=eval_data["job_id"],
            skill_match_pct=float(eval_data["skill_match_pct"]),
            overall_hiring_score=float(eval_data["overall_hiring_score"]),
            matched_skills=eval_data.get("matched_skills", []),
            missing_skills=eval_data.get("missing_skills", []),
            additional_skills=eval_data.get("additional_skills", []),
            rank=int(eval_data.get("rank", 0)),
        )
        db.add(new_eval)
        db.commit()
        db.refresh(new_eval)
        return new_eval


def get_evaluations_for_job(db: Session, job_id: int) -> List[Evaluation]:
    return list(
        db.scalars(
            select(Evaluation)
            .where(Evaluation.job_id == job_id)
            .order_by(Evaluation.overall_hiring_score.desc())
        ).all()
    )


def get_evaluations_for_candidate(db: Session, candidate_id: int) -> List[Evaluation]:
    return list(
        db.scalars(
            select(Evaluation)
            .where(Evaluation.candidate_id == candidate_id)
            .order_by(Evaluation.overall_hiring_score.desc())
        ).all()
    )


# --- ATS Application CRUD ---

def get_or_create_application(
    db: Session,
    candidate_id: int,
    job_id: int,
    stage: str = "Applied",
) -> Application:
    app = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
        )
    )
    if not app:
        app = Application(
            candidate_id=candidate_id,
            job_id=job_id,
            stage=stage,
            interview_mode="AI Mock Simulation",
        )
        db.add(app)
        db.commit()
        db.refresh(app)
    return app


def get_all_applications(
    db: Session,
    job_id: Optional[int] = None,
    stage: Optional[str] = None,
) -> List[Application]:
    query = select(Application)
    if job_id:
        query = query.where(Application.job_id == job_id)
    if stage and stage != "All Stages":
        query = query.where(Application.stage == stage)
    query = query.order_by(Application.updated_at.desc())
    return list(db.scalars(query).all())


def get_applications_for_candidate(db: Session, candidate_id: int) -> List[Application]:
    """Scoped query: returns applications for a specific candidate only."""
    return list(
        db.scalars(
            select(Application)
            .where(Application.candidate_id == candidate_id)
            .order_by(Application.updated_at.desc())
        ).all()
    )


def get_application_by_id(db: Session, app_id: int) -> Optional[Application]:
    return db.scalar(select(Application).where(Application.id == app_id))


def update_application_stage(db: Session, app_id: int, new_stage: str) -> Optional[Application]:
    app = get_application_by_id(db, app_id)
    if app:
        app.stage = new_stage
        app.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(app)
    return app


def update_application_details(
    db: Session,
    app_id: int,
    stage: Optional[str] = None,
    interview_scheduled_at: Optional[str] = None,
    interview_mode: Optional[str] = None,
    recruiter_notes: Optional[str] = None,
    recruiter_feedback: Optional[str] = None,
    recruiter_rating: Optional[float] = None,
) -> Optional[Application]:
    app = get_application_by_id(db, app_id)
    if not app:
        return None

    if stage is not None:
        app.stage = stage
    if interview_scheduled_at is not None:
        app.interview_scheduled_at = interview_scheduled_at
    if interview_mode is not None:
        app.interview_mode = interview_mode
    if recruiter_notes is not None:
        app.recruiter_notes = recruiter_notes
    if recruiter_feedback is not None:
        app.recruiter_feedback = recruiter_feedback
    if recruiter_rating is not None:
        app.recruiter_rating = recruiter_rating

    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    return app


def get_ats_pipeline_counts(db: Session, job_id: Optional[int] = None) -> Dict[str, int]:
    stages = ["Applied", "Screening", "Interview", "Selected", "Rejected"]
    counts = {s: 0 for s in stages}

    query = select(Application.stage, func.count(Application.id))
    if job_id:
        query = query.where(Application.job_id == job_id)
    query = query.group_by(Application.stage)

    results = db.execute(query).all()
    for stage_name, cnt in results:
        if stage_name in counts:
            counts[stage_name] = cnt

    return counts


# --- Interview Session CRUD ---

def save_interview_session(db: Session, session_data: dict[str, Any]) -> InterviewSession:
    session = InterviewSession(
        candidate_id=session_data["candidate_id"],
        job_id=session_data["job_id"],
        application_id=session_data.get("application_id"),
        status=session_data.get("status", "completed"),
        total_score=float(session_data.get("total_score", 0.0)),
        technical_score=float(session_data.get("technical_score", 0.0)),
        communication_score=float(session_data.get("communication_score", 0.0)),
        confidence_score=float(session_data.get("confidence_score", 0.0)),
        confidence_level=session_data.get("confidence_level", "Moderate"),
        strengths=session_data.get("strengths", []),
        improvements=session_data.get("improvements", []),
        summary_report=session_data.get("summary_report", ""),
        hiring_recommendation=session_data.get("hiring_recommendation", "Hire"),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_interview_sessions_for_candidate(
    db: Session, candidate_id: int, job_id: Optional[int] = None
) -> List[InterviewSession]:
    query = select(InterviewSession).where(InterviewSession.candidate_id == candidate_id)
    if job_id:
        query = query.where(InterviewSession.job_id == job_id)
    query = query.order_by(InterviewSession.created_at.desc())
    return list(db.scalars(query).all())


def get_all_interview_sessions(db: Session, limit: int = 50) -> List[InterviewSession]:
    return list(
        db.scalars(
            select(InterviewSession).order_by(InterviewSession.created_at.desc()).limit(limit)
        ).all()
    )


def get_interview_session_by_id(db: Session, session_id: int) -> Optional[InterviewSession]:
    return db.scalar(select(InterviewSession).where(InterviewSession.id == session_id))


def save_interview_question(db: Session, q_data: dict[str, Any]) -> InterviewQuestion:
    q = InterviewQuestion(
        session_id=q_data.get("session_id"),
        job_id=q_data.get("job_id"),
        candidate_id=q_data.get("candidate_id"),
        category=q_data.get("category", "technical"),
        difficulty=q_data.get("difficulty", "Intermediate"),
        question_text=q_data["question_text"],
        target_skill=q_data.get("target_skill", ""),
        sample_ideal_answer=q_data.get("sample_ideal_answer", ""),
        follow_up_question=q_data.get("follow_up_question", ""),
        candidate_response=q_data.get("candidate_response", ""),
        input_mode=q_data.get("input_mode", "text"),
        relevance_score=float(q_data.get("relevance_score", 0.0)),
        clarity_score=float(q_data.get("clarity_score", 0.0)),
        ai_feedback=q_data.get("ai_feedback", ""),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def get_questions_for_job_candidate(
    db: Session, job_id: int, candidate_id: Optional[int] = None
) -> List[InterviewQuestion]:
    query = select(InterviewQuestion).where(InterviewQuestion.job_id == job_id)
    if candidate_id:
        query = query.where(InterviewQuestion.candidate_id == candidate_id)
    query = query.order_by(InterviewQuestion.created_at.desc())
    return list(db.scalars(query).all())


def get_admin_system_metrics(db: Session) -> Dict[str, Any]:
    """Returns platform-wide metrics for Admin Dashboard."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_candidates = db.scalar(select(func.count(Candidate.id))) or 0
    total_jobs = db.scalar(select(func.count(Job.id))) or 0
    total_applications = db.scalar(select(func.count(Application.id))) or 0
    total_interviews = db.scalar(select(func.count(InterviewSession.id))) or 0
    
    return {
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "total_interviews": total_interviews,
    }


def clear_candidate_data(db: Session) -> Dict[str, int]:
    """Clears candidates, applications, evaluations, questions, and candidate accounts when explicitly requested."""
    del_evals = db.query(Evaluation).delete()
    del_qs = db.query(InterviewQuestion).delete()
    del_sess = db.query(InterviewSession).delete()
    del_apps = db.query(Application).delete()
    del_cands = db.query(Candidate).delete()
    del_users = db.query(User).filter(User.role == "Candidate").delete()
    db.commit()
    return {
        "candidates": del_cands,
        "applications": del_apps,
        "evaluations": del_evals,
        "sessions": del_sess,
        "users": del_users,
    }


def reset_database():
    """Resets all tables in the database cleanly."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
