import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from database import (
    init_db, get_db, authenticate_user, get_all_users, save_job, get_all_jobs,
    save_candidate, get_all_candidates, get_or_create_application,
    get_applications_for_candidate, update_application_stage,
    save_interview_session, get_interview_sessions_for_candidate,
    reset_database, Candidate, User, Job, Evaluation
)
from ats import get_ats_funnel_metrics
from sample_data import seed_default_users, seed_demo_data
from analytics import (
    plot_candidate_radar, plot_skills_gauge, plot_skills_donut
)
from question_generator import generate_interview_questions
from interview_simulator import evaluate_single_answer, generate_overall_interview_report

def run_tests():
    print("==================================================")
    print("🚀 RUNNING AUTOMATED AI RECRUITER PLATFORM TESTS")
    print("==================================================")

    db = next(get_db())

    # Test 1: Seed default users
    print("\n[Test 1] Testing Default User Seeding & Authentication...")
    seed_default_users(db)
    
    rec_user = authenticate_user(db, "recruiter_sarah", "recruiter123", expected_role="Recruiter")
    assert rec_user is not None, "Failed to authenticate Recruiter Sarah!"
    print("  ✅ Recruiter Sarah authenticated successfully.")

    from database import save_user
    save_user(db, {
        "username": "alex_mercer",
        "password": "candidate123",
        "full_name": "Dr. Alex Mercer",
        "email": "alex.mercer@ai-research.org",
        "role": "Candidate",
    })
    cand_user = authenticate_user(db, "alex_mercer", "candidate123", expected_role="Candidate")
    assert cand_user is not None, "Failed to authenticate Candidate Alex!"
    print("  ✅ Candidate Alex authenticated successfully.")

    admin_user = authenticate_user(db, "admin", "admin123", expected_role="Admin")
    assert admin_user is not None, "Failed to authenticate Superadmin!"
    print("  ✅ Superadmin authenticated successfully.")

    # Test 2: Role Authorization Gate
    print("\n[Test 2] Testing Role-based Access Gate...")
    fake_rec = authenticate_user(db, "alex_mercer", "candidate123", expected_role="Recruiter")
    assert fake_rec is None, "Security Error: Candidate logged into Recruiter role!"
    print("  ✅ Role authorization enforcement verified.")

    # Test 3: Candidate Application & Tracking Lifecycle
    print("\n[Test 3] Testing Application Creation & Stage Progression...")
    jobs = get_all_jobs(db)
    target_job = jobs[0] if jobs else save_job(db, {
        "title": "Lead AI Engineer",
        "role": "Senior AI Engineer",
        "required_skills": ["python", "pytorch", "transformers", "fastapi"],
        "min_experience": 4.0,
        "required_education": "Master's",
    })

    cand = save_candidate(db, {
        "full_name": "Dr. Alex Mercer",
        "email": "alex.mercer@ai-research.org",
        "phone": "+1 (555) 019-2834",
        "parsed_experience": 6.5,
        "skills": ["python", "pytorch", "transformers", "fastapi", "docker"],
    })

    app = get_or_create_application(db, cand.id, target_job.id, stage="Applied")
    assert app.stage == "Applied", f"Expected stage Applied, got {app.stage}"
    print("  ✅ Stage 1: Application submitted.")

    update_application_stage(db, app.id, "Screening")
    cand_apps = get_applications_for_candidate(db, cand.id)
    assert cand_apps[0].stage == "Screening", f"Expected Screening, got {cand_apps[0].stage}"
    print("  ✅ Stage 2: Application moved to Screening.")

    update_application_stage(db, app.id, "Interview")
    cand_apps = get_applications_for_candidate(db, cand.id)
    assert cand_apps[0].stage == "Interview", f"Expected Interview, got {cand_apps[0].stage}"
    print("  ✅ Stage 3: Interview scheduled.")

    update_application_stage(db, app.id, "Selected")
    cand_apps = get_applications_for_candidate(db, cand.id)
    assert cand_apps[0].stage == "Selected", f"Expected Selected, got {cand_apps[0].stage}"
    print("  ✅ Stage 4: Candidate Selected.")

    # Test 4: Interview Question Generation & Heuristic Simulation
    print("\n[Test 4] Testing AI Interview Question Generator & Evaluator...")
    q_set = generate_interview_questions(job=target_job, candidate=cand)
    assert len(q_set.technical_questions) > 0, "No technical questions generated!"
    print(f"  ✅ Generated {len(q_set.technical_questions)} tech and {len(q_set.behavioural_questions)} behavioral questions.")

    first_q = q_set.technical_questions[0]
    ev_res = evaluate_single_answer(
        question_text=first_q.question_text,
        target_skill=first_q.target_skill,
        ideal_answer=first_q.sample_ideal_answer,
        candidate_response=first_q.sample_ideal_answer,
    )
    assert ev_res.relevance_score >= 70.0, f"Expected good score, got {ev_res.relevance_score}"
    print(f"  ✅ Evaluated answer: Score {ev_res.relevance_score}% (Confidence: {ev_res.confidence_score}%)")

    # Test 5: Light Theme Visual Analytics
    print("\n[Test 5] Testing Light Theme Plotly Visualizations...")
    fig_r = plot_candidate_radar(cand.full_name, 90.0, 85.0, 88.0, 89.0)
    assert fig_r is not None, "Radar chart generation failed!"
    
    fig_g = plot_skills_gauge(88.0, 92.0)
    assert fig_g is not None, "Gauges chart generation failed!"

    fig_d = plot_skills_donut(10, 2, 3)
    assert fig_d is not None, "Donut chart generation failed!"
    print("  ✅ Radar, Gauges, and Donut charts generated with Light Layout.")

    # Test 6: Candidate Registration & Recruiter Resume Persistence
    print("\n[Test 6] Testing Candidate Registration & Recruiter Resume Persistence...")
    from database import clear_candidate_data
    from matcher import rank_and_save_evaluations_for_job
    
    # 1. Candidate registers
    new_cand = save_candidate(db, {
        "full_name": "Marcus Vance",
        "email": "marcus.vance@example.com",
        "phone": "+1 (555) 345-6789",
        "parsed_experience": 4.0,
        "parsed_education": ["Bachelor's"],
        "skills": ["python", "docker", "fastapi", "react"],
        "projects": ["Distributed Microservices", "Real-time Chat App"],
        "certifications": ["AWS Certified Developer"],
    })
    save_user(db, {
        "username": "marcus_vance",
        "password": "candidate123",
        "full_name": "Marcus Vance",
        "email": "marcus.vance@example.com",
        "role": "Candidate",
        "candidate_id": new_cand.id,
    })
    # Auto-match evaluations
    rank_and_save_evaluations_for_job(db, target_job.id, [new_cand], target_job)
    
    # Verify persisted in database
    retrieved_c = db.query(Candidate).filter(Candidate.email == "marcus.vance@example.com").first()
    assert retrieved_c is not None, "Candidate record was not saved to database!"
    assert "fastapi" in retrieved_c.skills, "Skills not preserved in candidate record!"
    
    user_cand = authenticate_user(db, "marcus_vance", "candidate123", expected_role="Candidate")
    assert user_cand is not None and user_cand.candidate_id == new_cand.id, "Candidate user not linked properly!"
    print("  ✅ Candidate registration and account linked in database.")

    # 2. Recruiter batch parses resume
    recruiter_parsed_cand = save_candidate(db, {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@analytics.io",
        "parsed_experience": 5.0,
        "parsed_education": ["Master's in Data Science"],
        "skills": ["python", "sql", "pytorch", "tableau", "fastapi"],
        "raw_text": "Experienced Data Scientist with 5 years in Python, SQL, and Deep Learning.",
    })
    rank_and_save_evaluations_for_job(db, target_job.id, [recruiter_parsed_cand], target_job)
    
    all_cands = get_all_candidates(db)
    cand_emails = [c.email for c in all_cands]
    assert "elena.rostova@analytics.io" in cand_emails, "Recruiter parsed candidate not in database!"
    assert "marcus.vance@example.com" in cand_emails, "Registered candidate not in database!"
    print(f"  ✅ Recruiter parsed resume and registered candidate persisted in database (Total: {len(all_cands)}).")

    # 3. Explicit clear database test
    clear_res = clear_candidate_data(db)
    assert clear_res["candidates"] >= 2, "Failed to clear candidate records on explicit request!"
    assert len(get_all_candidates(db)) == 0, "Candidate table not empty after clear!"
    print(f"  ✅ Database explicitly cleared {clear_res['candidates']} candidates only upon user request.")

    print("\n==================================================")
    print("🎉 ALL PLATFORM TESTS PASSED SUCCESSFULLY! (100%)")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
