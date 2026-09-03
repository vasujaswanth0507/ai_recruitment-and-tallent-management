import logging
from datetime import datetime, timezone
from database import (
    init_db,
    get_db,
    save_job,
    save_candidate,
    get_all_jobs,
    get_all_candidates,
    get_or_create_application,
    update_application_details,
    save_interview_session,
    save_interview_question,
)
from matcher import rank_and_save_evaluations_for_job

logger = logging.getLogger(__name__)

SAMPLE_JOBS = [
    {
        "title": "Senior AI / ML Engineer",
        "role": "AI System Architect",
        "description": "We are seeking a Senior AI/ML Engineer to design scalable LLM applications, custom NLP pipelines, and computer vision models.",
        "required_skills": ["python", "pytorch", "tensorflow", "nlp", "llm", "fastapi", "docker", "aws", "sql", "spacy"],
        "min_experience": 4.0,
        "required_education": "Master's in Computer Science or AI",
        "certifications": ["AWS Certified Machine Learning Specialty"],
    },
    {
        "title": "Full-Stack Software Developer",
        "role": "Full-Stack Engineer",
        "description": "Looking for a versatile Full-Stack Developer to build modern web applications using React, Python, FastAPI, and PostgreSQL.",
        "required_skills": ["python", "react", "fastapi", "postgresql", "docker", "javascript", "typescript", "git", "rest api"],
        "min_experience": 3.0,
        "required_education": "Bachelor's in Computer Science",
        "certifications": [],
    },
    {
        "title": "Data Analyst & Business Intelligence Specialist",
        "role": "Data Analyst",
        "description": "Responsibilities include designing BI dashboards, writing complex SQL queries, and providing data-driven insights.",
        "required_skills": ["sql", "python", "pandas", "tableau", "power bi", "excel", "communication"],
        "min_experience": 2.0,
        "required_education": "Bachelor's degree",
        "certifications": ["Tableau Desktop Specialist"],
    },
]

SAMPLE_CANDIDATES = [
    {
        "full_name": "Dr. Alex Mercer",
        "email": "alex.mercer@ai-research.org",
        "phone": "+1 (555) 234-5678",
        "raw_text": "Dr. Alex Mercer\nalex.mercer@ai-research.org\n5+ years of experience building Deep Learning, LLM pipelines, and NLP architectures using Python, PyTorch, Transformers, spaCy, FastAPI, Docker, and AWS.",
        "parsed_experience": 5.5,
        "parsed_education": ["Ph.D. in Artificial Intelligence, Stanford University", "B.S. in Computer Science"],
        "skills": ["python", "pytorch", "nlp", "spacy", "llm", "fastapi", "docker", "aws", "sql", "git", "opencv"],
        "projects": ["Enterprise LLM Copilot Engine", "Multimodal Medical NLP Pipeline"],
        "certifications": ["AWS Certified Machine Learning Specialty"],
    },
    {
        "full_name": "Sarah Chen",
        "email": "sarah.chen@devstudio.io",
        "phone": "+1 (555) 987-6543",
        "raw_text": "Sarah Chen\nFull-Stack Engineer with 4 years experience in React, TypeScript, Python, FastAPI, PostgreSQL, Docker, and CI/CD pipelines.",
        "parsed_experience": 4.0,
        "parsed_education": ["B.S. in Computer Science, UC Berkeley"],
        "skills": ["python", "react", "fastapi", "postgresql", "docker", "javascript", "typescript", "git", "rest api", "sql"],
        "projects": ["Real-time Collaborative Dashboard", "Fintech Payment Gateway Integration"],
        "certifications": [],
    },
    {
        "full_name": "Marcus Vance",
        "email": "marcus.vance@analytics.co",
        "phone": "+1 (555) 456-7890",
        "raw_text": "Marcus Vance\nData Analyst with 2.5 years of experience in SQL, Python, Pandas, Tableau, and Power BI.",
        "parsed_experience": 2.5,
        "parsed_education": ["B.A. in Statistics & Economics, NYU"],
        "skills": ["sql", "python", "pandas", "tableau", "excel", "communication", "power bi"],
        "projects": ["E-Commerce Customer Churn Dashboard", "Automated Sales Forecasting Pipeline"],
        "certifications": ["Tableau Desktop Specialist"],
    },
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@cloudtech.com",
        "phone": "+1 (555) 321-7654",
        "raw_text": "Elena Rostova\nJunior Cloud Developer with 1 year experience in Python, AWS, Docker, and Linux.",
        "parsed_experience": 1.0,
        "parsed_education": ["B.S. in Information Technology"],
        "skills": ["python", "aws", "docker", "linux", "git", "sql"],
        "projects": ["Serverless Microservices API"],
        "certifications": ["AWS Certified Cloud Practitioner"],
    },
]


def seed_default_users(db):
    """Ensure core admin and recruiter login credentials exist."""
    from database import save_user
    save_user(db, {
        "username": "admin",
        "password": "admin123",
        "full_name": "System Administrator",
        "email": "admin@talentcopilot.ai",
        "role": "Admin",
    })
    save_user(db, {
        "username": "recruiter_sarah",
        "password": "recruiter123",
        "full_name": "Sarah Jenkins (Lead Recruiter)",
        "email": "sarah.jenkins@talentcopilot.ai",
        "role": "Recruiter",
    })
    save_user(db, {
        "username": "recruiter_david",
        "password": "recruiter123",
        "full_name": "David Sterling (Technical Sourcer)",
        "email": "david.sterling@talentcopilot.ai",
        "role": "Recruiter",
    })


def seed_database_if_empty():
    """Initializes the database tables and sets up core login accounts and default jobs cleanly."""
    init_db()
    db = next(get_db())
    seed_default_users(db)

    existing_jobs = get_all_jobs(db)
    if not existing_jobs:
        logger.info("Seeding initial Job Openings...")
        for j_data in SAMPLE_JOBS:
            save_job(db, j_data)


def seed_demo_data():
    """Seeds sample candidates, evaluations, ATS applications, and mock interview reports on demand."""
    init_db()
    db = next(get_db())
    seed_default_users(db)

    existing_jobs = get_all_jobs(db)
    if not existing_jobs:
        for j_data in SAMPLE_JOBS:
            save_job(db, j_data)

    existing_candidates = get_all_candidates(db)
    if not existing_candidates:
        logger.info("Seeding sample Candidates...")
        for c_data in SAMPLE_CANDIDATES:
            save_candidate(db, c_data)

    # Trigger evaluation matching for demo jobs
    jobs = get_all_jobs(db)
    candidates = get_all_candidates(db)
    if jobs and candidates:
        for job in jobs:
            rank_and_save_evaluations_for_job(db, job.id, candidates, job)

        # Seed ATS Applications across pipeline stages
        job_ai = jobs[0]
        job_fullstack = jobs[1] if len(jobs) > 1 else jobs[0]

        cand_alex = candidates[0]
        cand_sarah = candidates[1] if len(candidates) > 1 else candidates[0]
        cand_marcus = candidates[2] if len(candidates) > 2 else candidates[0]
        cand_elena = candidates[3] if len(candidates) > 3 else candidates[0]

        # 1. Alex Mercer -> Selected for Senior AI/ML Engineer
        app_alex = get_or_create_application(db, cand_alex.id, job_ai.id, stage="Selected")
        update_application_details(
            db,
            app_alex.id,
            stage="Selected",
            interview_scheduled_at="Completed (2026-08-25 14:00)",
            interview_mode="AI Mock Simulation",
            recruiter_notes="Strongest candidate in talent pool. Outstanding LLM pipeline design.",
            recruiter_feedback="Exceptional technical depth in PyTorch, NLP, and distributed systems. 100% cultural alignment.",
            recruiter_rating=5.0,
        )

        # 2. Sarah Chen -> Interview stage for Full-Stack Developer
        app_sarah = get_or_create_application(db, cand_sarah.id, job_fullstack.id, stage="Interview")
        update_application_details(
            db,
            app_sarah.id,
            stage="Interview",
            interview_scheduled_at="2026-08-28 10:30 AM",
            interview_mode="AI Mock Simulation",
            recruiter_notes="Screening passed with high marks in React and FastAPI.",
            recruiter_feedback="Great communication. Live coding round scheduled.",
            recruiter_rating=4.5,
        )

        # 3. Marcus Vance -> Screening stage
        app_marcus = get_or_create_application(db, cand_marcus.id, job_ai.id, stage="Screening")
        update_application_details(
            db,
            app_marcus.id,
            stage="Screening",
            interview_scheduled_at="2026-08-29 15:00 PM",
            interview_mode="Technical Screening",
            recruiter_notes="Good analytical background, reviewing NLP gap.",
            recruiter_rating=3.5,
        )

        # 4. Elena Rostova -> Applied stage
        app_elena = get_or_create_application(db, cand_elena.id, job_ai.id, stage="Applied")
        update_application_details(
            db,
            app_elena.id,
            stage="Applied",
            recruiter_notes="Entry-level applicant. Under review for junior cloud track.",
            recruiter_rating=3.0,
        )

        # Seed a completed Interview Session for Alex Mercer
        session_data = {
            "candidate_id": cand_alex.id,
            "job_id": job_ai.id,
            "application_id": app_alex.id,
            "status": "completed",
            "total_score": 92.5,
            "technical_score": 95.0,
            "communication_score": 90.0,
            "confidence_score": 92.0,
            "confidence_level": "High",
            "strengths": [
                "Mastery of PyTorch Autograd, dynamic computation graphs, and CUDA memory allocation.",
                "Deep understanding of distributed training with DDP and FSDP architectures.",
                "Excellent structural clarity using STAR method for complex system design.",
            ],
            "improvements": [
                "Could quantify business impact metrics more explicitly when discussing legacy refactors.",
            ],
            "summary_report": "Candidate demonstrated world-class expertise in AI/ML architectures, high concurrency FastAPI deployments, and distributed PyTorch pipelines. Unanimous Strong Hire recommendation.",
            "hiring_recommendation": "Strong Hire",
        }
        saved_session = save_interview_session(db, session_data)

        # Seed sample questions for this session
        q1_data = {
            "session_id": saved_session.id,
            "job_id": job_ai.id,
            "candidate_id": cand_alex.id,
            "category": "technical",
            "difficulty": "Advanced",
            "question_text": "How do DistributedDataParallel (DDP) and Fully Sharded Data Parallel (FSDP) optimize training throughput across multi-node GPU clusters?",
            "target_skill": "pytorch",
            "sample_ideal_answer": "DDP replicates model parameters and overlaps computation with AllReduce communication. FSDP shards parameters, gradients, and optimizer states across ranks.",
            "follow_up_question": "How would you handle tensor parallelism for a 70B parameter LLM?",
            "candidate_response": "DDP maintains model replicas across all GPU ranks and overlaps gradient synchronization with backward pass operations using AllReduce rings. When models exceed single-GPU VRAM, FSDP shards model parameters, gradients, and optimizer states across ranks using ZeRO-style sharding to reduce memory footprints drastically.",
            "input_mode": "voice",
            "relevance_score": 96.0,
            "clarity_score": 92.0,
            "ai_feedback": "Exceptional precision covering parameter sharding, AllReduce gradient overlaps, and ZeRO mechanics.",
        }
        save_interview_question(db, q1_data)

        q2_data = {
            "session_id": saved_session.id,
            "job_id": job_ai.id,
            "candidate_id": cand_alex.id,
            "category": "behavioural",
            "difficulty": "Intermediate",
            "question_text": "Describe a challenging technical project you delivered under tight deadlines. How did you prioritize requirements and manage technical debt?",
            "target_skill": "Agile Prioritization",
            "sample_ideal_answer": "Demonstrates STAR method, MVP scoping, architectural trade-offs, and debt remediation.",
            "follow_up_question": "What would you do differently if you built it again today?",
            "candidate_response": "While building our enterprise NLP copilot under a 6-week timeline, I prioritized the core vector search and streaming LLM pipeline as our MVP, while deferring auxiliary analytics to post-launch sprints. We held daily standups to unblock cross-functional dependencies and scheduled dedicated technical debt refactoring sprints right after deployment.",
            "input_mode": "text",
            "relevance_score": 90.0,
            "clarity_score": 92.0,
            "ai_feedback": "Strong structured explanation with realistic trade-offs and clear remediation strategy.",
        }
        # Seed sample User accounts for Admin, Recruiters, and Candidates
        from database import save_user
        save_user(db, {
            "username": "admin",
            "password": "admin123",
            "full_name": "System Administrator",
            "email": "admin@talentcopilot.ai",
            "role": "Admin",
        })
        save_user(db, {
            "username": "recruiter_sarah",
            "password": "recruiter123",
            "full_name": "Sarah Jenkins (Lead Recruiter)",
            "email": "sarah.jenkins@talentcopilot.ai",
            "role": "Recruiter",
        })
        save_user(db, {
            "username": "recruiter_david",
            "password": "recruiter123",
            "full_name": "David Sterling (Technical Sourcer)",
            "email": "david.sterling@talentcopilot.ai",
            "role": "Recruiter",
        })
        for c in [cand_alex, cand_sarah, cand_marcus, cand_elena]:
            save_user(db, {
                "username": c.full_name.lower().replace(" ", "_").replace("dr._", ""),
                "password": "candidate123",
                "full_name": c.full_name,
                "email": c.email or f"{c.full_name.lower().replace(' ', '_')}@candidate.org",
                "role": "Candidate",
                "candidate_id": c.id,
            })



if __name__ == "__main__":
    seed_demo_data()
    print("Demo data seeded successfully.")


