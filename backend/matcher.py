import re
from typing import Dict, List, Tuple, Any
from database import Candidate, Job, Evaluation, save_evaluation

DEGREE_HIERARCHY = {
    "doctorate": 4,
    "phd": 4,
    "ph.d": 4,
    "master": 3,
    "m.s": 3,
    "m.tech": 3,
    "m.a": 3,
    "bachelor": 2,
    "b.s": 2,
    "b.tech": 2,
    "b.e": 2,
    "b.a": 2,
    "associate": 1,
    "diploma": 1,
    "high school": 0,
}


def get_education_level_score(edu_text: str) -> int:
    """Returns education rank integer based on keywords."""
    if not edu_text:
        return 1
    edu_lower = edu_text.lower()
    for kw, score in DEGREE_HIERARCHY.items():
        if kw in edu_lower:
            return score
    return 1


def calculate_skill_match(
    candidate_skills: List[str], required_skills: List[str]
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Calculates Skill Match Percentage and categorizes skills.
    Skill Match Score = (|Matched Skills| / |Required Skills|) * 100
    Returns: (skill_match_pct, matched_skills, missing_skills, additional_skills)
    """
    cand_set = {s.strip().lower() for s in candidate_skills if s and s.strip()}
    req_set = {s.strip().lower() for s in required_skills if s and s.strip()}

    if not req_set:
        return 100.0, list(cand_set), [], list(cand_set)

    matched = list(cand_set.intersection(req_set))
    missing = list(req_set.difference(cand_set))
    additional = list(cand_set.difference(req_set))

    skill_match_pct = (len(matched) / len(req_set)) * 100.0
    return round(skill_match_pct, 2), sorted(matched), sorted(missing), sorted(additional)


def calculate_experience_match(
    candidate_exp: float, required_exp: float
) -> float:
    """
    Calculates Experience Match Score (0 to 100).
    100.0 if candidate_exp >= required_exp, scaled ratio otherwise.
    Prevents division by zero.
    """
    cand_exp = max(0.0, float(candidate_exp or 0.0))
    req_exp = max(0.0, float(required_exp or 0.0))

    if req_exp == 0.0:
        return 100.0

    if cand_exp >= req_exp:
        return 100.0
    else:
        return round((cand_exp / req_exp) * 100.0, 2)


def calculate_education_match(
    candidate_education: List[str], required_education: str
) -> float:
    """
    Calculates Education Alignment score (0 to 100) using level hierarchy and string overlap.
    """
    req_score = get_education_level_score(required_education)

    cand_str = " ".join(candidate_education) if isinstance(candidate_education, list) else str(candidate_education)
    cand_score = get_education_level_score(cand_str)

    if cand_score >= req_score:
        return 100.0
    else:
        # Penalize slightly per missing level
        diff = req_score - cand_score
        return max(50.0, 100.0 - (diff * 25.0))


def compute_hiring_score(
    skill_pct: float,
    exp_pct: float,
    edu_pct: float,
    weights: Tuple[float, float, float] = (0.50, 0.35, 0.15),
) -> float:
    """
    Computes overall composite hiring score using weighted sum formula:
    Hiring Score = w1*(Skill Match) + w2*(Experience Match) + w3*(Education Match)
    """
    w1, w2, w3 = weights
    # Normalize weights if sum != 1.0
    total_w = w1 + w2 + w3
    if total_w > 0:
        w1, w2, w3 = w1 / total_w, w2 / total_w, w3 / total_w

    score = (w1 * skill_pct) + (w2 * exp_pct) + (w3 * edu_pct)
    return round(score, 2)


def evaluate_candidate_for_job(
    db_session: Any,
    candidate: Candidate,
    job: Job,
    weights: Tuple[float, float, float] = (0.50, 0.35, 0.15),
) -> Evaluation:
    """
    Evaluates a candidate against a job, saves evaluation in DB, and returns the Evaluation model.
    """
    skill_pct, matched, missing, additional = calculate_skill_match(
        candidate.skills or [], job.required_skills or []
    )
    exp_pct = calculate_experience_match(
        candidate.parsed_experience, job.min_experience
    )
    edu_pct = calculate_education_match(
        candidate.parsed_education or [], job.required_education or "Bachelor's"
    )

    overall_score = compute_hiring_score(skill_pct, exp_pct, edu_pct, weights)

    eval_data = {
        "candidate_id": candidate.id,
        "job_id": job.id,
        "skill_match_pct": skill_pct,
        "overall_hiring_score": overall_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "additional_skills": additional,
        "rank": 0,
    }

    return save_evaluation(db_session, eval_data)


def rank_and_save_evaluations_for_job(
    db_session: Any,
    job_id: int,
    candidates: List[Candidate],
    job: Job,
    weights: Tuple[float, float, float] = (0.50, 0.35, 0.15),
) -> List[Evaluation]:
    """
    Evaluates all candidates for a target job, ranks them in descending order of hiring score,
    updates rank in DB, and returns sorted evaluations.
    """
    evaluations = []
    for cand in candidates:
        ev = evaluate_candidate_for_job(db_session, cand, job, weights)
        evaluations.append(ev)

    # Sort descending by overall_hiring_score
    evaluations.sort(key=lambda x: x.overall_hiring_score, reverse=True)

    # Update rank (1-indexed)
    for idx, ev in enumerate(evaluations, start=1):
        ev.rank = idx
        db_session.add(ev)

    db_session.commit()
    return evaluations
