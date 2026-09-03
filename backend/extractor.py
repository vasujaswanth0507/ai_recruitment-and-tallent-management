import re
import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# --- Pydantic Models for Structured Outputs ---

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(?:\+?\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,5}[\s-]?\d{3,5}"


class CandidateProfile(BaseModel):
    full_name: str = Field(description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Candidate's email address")
    phone: Optional[str] = Field(None, description="Candidate's phone number")
    total_experience_years: float = Field(
        0.0,
        description="Total years of formal work experience or internship tenure. Calculate precisely from work history date ranges and explicit duration mentions. Return 0.0 for students or fresh graduates with 0 formal work/internship tenure. Do not guess experience.",
    )
    parsed_education: List[str] = Field(
        default_factory=list,
        description="Degrees, fields of study, or universities attended",
    )
    skills: List[str] = Field(
        default_factory=list,
        description="Technical and soft skills, normalized to lowercase",
    )
    projects: List[str] = Field(
        default_factory=list, description="Notable key projects mentioned"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Certifications or licenses earned"
    )

    @property
    def education(self) -> List[str]:
        """Backward-compatible alias for parsed_education."""
        return self.parsed_education

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        match = re.search(EMAIL_REGEX, v)
        return match.group(0) if match else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        match = re.search(PHONE_REGEX, v)
        if match:
            raw_phone = match.group(0).strip()
            # Clean up awkward parentheses or isolated symbols
            clean = re.sub(r"[^\d+]", " ", raw_phone)
            clean = " ".join(clean.split())
            return clean if len(re.sub(r"\D", "", clean)) >= 7 else None
        return None

    @field_validator("parsed_education", mode="before")
    @classmethod
    def clean_education(cls, v):
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, dict):
                    deg = item.get("degree") or item.get("institution") or str(item)
                    cleaned.append(deg)
                elif isinstance(item, str):
                    item_str = item.strip()
                    if item_str.startswith("{") and "degree" in item_str:
                        try:
                            data = json.loads(item_str)
                            cleaned.append(data.get("degree") or data.get("institution") or item_str)
                            continue
                        except Exception:
                            pass
                    cleaned.append(item_str)
            return cleaned
        return v

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.strip().lower()
            if s_clean and s_clean not in cleaned:
                cleaned.append(s_clean)
        return cleaned


class JobProfile(BaseModel):
    title: str = Field(description="Job title")
    role: str = Field(description="Specific role or designation")
    description: str = Field("", description="Detailed job description summary")
    required_skills: List[str] = Field(
        default_factory=list, description="Required technical and professional skills"
    )
    min_experience: float = Field(
        0.0, description="Minimum required experience in years"
    )
    required_education: str = Field(
        "Bachelor's", description="Required minimum education level"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Required or preferred certifications"
    )

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.strip().lower()
            if s_clean and s_clean not in cleaned:
                cleaned.append(s_clean)
        return cleaned


# --- Regex / Rule-Based Fallback Extractor ---

KNOWN_SKILLS = [
    "python", "java", "c++", "c#", "javascript", "typescript", "react", "angular", "vue",
    "node.js", "html", "css", "sql", "postgresql", "mysql", "sqlite", "mongodb", "redis",
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github", "ci/cd", "linux", "rest api",
    "graphql", "fastapi", "flask", "django", "streamlit", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "nlp", "spacy", "nltk", "opencv", "llm", "openai", "gemini",
    "gemini api", "gemini vision api", "prompt engineering", "generative ai", "vision-language models",
    "frontend development", "backend development", "full stack", "smtp", "smtp server",
    "langchain", "pydantic", "sqlalchemy", "spark", "hadoop", "tableau", "power bi",
    "agile", "scrum", "jira", "communication", "leadership", "problem solving"
]

DEGREE_KEYWORDS = [
    "bachelor", "b.s", "b.a", "b.tech", "b.e", "master", "m.s", "m.a", "m.tech", "m.e",
    "phd", "ph.d", "doctorate", "associate", "diploma", "degree", "computer science",
    "engineering", "data science", "information technology", "artificial intelligence"
]


def extract_candidate_fallback(raw_text: str) -> CandidateProfile:
    """
    Extracts structured candidate info using advanced multi-section parsing and regex rules.
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    
    # 1. Name extraction heuristic: First non-contact, non-header line
    full_name = "Unknown Candidate"
    for line in lines[:5]:
        if not re.search(EMAIL_REGEX, line) and not re.search(PHONE_REGEX, line) and len(line) < 60:
            if not any(header in line.lower() for header in ["resume", "curriculum", "cv", "summary", "profile", "contact", "email", "phone"]):
                full_name = line
                break

    # 2. Email & Phone extraction
    email_match = re.search(EMAIL_REGEX, raw_text)
    email = email_match.group(0) if email_match else None

    phone_match = re.search(PHONE_REGEX, raw_text)
    phone = None
    if phone_match:
        p_raw = phone_match.group(0).strip()
        p_digits = re.sub(r"\D", "", p_raw)
        if len(p_digits) >= 8:
            phone = p_raw

    # 3. Section Segmentation (Education, Skills, Projects, Experience, Certifications)
    sections = {
        "education": [],
        "skills": [],
        "projects": [],
        "experience": [],
        "certifications": [],
    }
    current_sec = None

    sec_patterns = {
        "education": ["education", "academic background", "academic profile", "qualification"],
        "skills": ["skills", "technical skills", "skills & abilities", "tech stack", "technologies", "competencies", "skills & expertise"],
        "projects": ["projects", "key projects", "academic projects", "personal projects", "featured projects", "work & projects"],
        "experience": ["experience", "work experience", "employment history", "internships", "work history"],
        "certifications": ["certifications", "certificates", "licenses", "courses"],
    }

    for line in lines:
        line_clean = line.lower().strip(":-#*_ \t")
        matched_sec = None
        if len(line_clean) < 45:
            for sec_name, keywords in sec_patterns.items():
                if any(kw == line_clean or line_clean.startswith(kw) for kw in keywords):
                    matched_sec = sec_name
                    break

        if matched_sec:
            current_sec = matched_sec
            continue

        if current_sec:
            sections[current_sec].append(line)

    # 4. Skills Extraction
    found_skills = set()
    # a) Known skills dictionary matching
    text_lower = raw_text.lower()
    for skill in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill)

    # b) Dynamic extraction from Skills section lines
    for line in sections["skills"]:
        tokens = re.split(r"[,|•\*\:\t;]", line)
        for tok in tokens:
            tok_clean = tok.strip().lower()
            if tok_clean and len(tok_clean) <= 30 and not any(w in tok_clean for w in ["languages", "frameworks", "tools", "databases", "libraries"]):
                # Ensure token has valid characters
                if re.match(r"^[a-zA-Z0-9\s.+#/-]+$", tok_clean):
                    found_skills.add(tok_clean)

    # 5. Projects Extraction
    extracted_projects = []
    for line in sections["projects"]:
        if len(line) > 5 and not line.lower().endswith(":") and not any(kw in line.lower() for kw in ["education", "skills", "experience"]):
            extracted_projects.append(line)
            if len(extracted_projects) >= 6:
                break
    
    if not extracted_projects:
        for line in lines:
            if any(p_kw in line.lower() for p_kw in ["tech stack:", "built a", "developed a", "github.com", "system using", "app using", "api integration"]):
                extracted_projects.append(line[:120])

    # 6. Education Extraction
    extracted_edu = []
    summary_words = ["dedicated", "passionate", "experienced in", "seeking", "summary", "profile", "about me", "strong focus", "tech stack", "skills:"]
    
    # First search in Education section
    for line in sections["education"]:
        line_lower = line.lower()
        if len(line) < 140 and not any(sw in line_lower for sw in summary_words):
            extracted_edu.append(line)
    
    # Global fallback for Education if section was empty
    if not extracted_edu:
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in DEGREE_KEYWORDS) or any(deg in line_lower for deg in ["b.tech", "bachelor", "master", "m.tech", "phd", "gpa"]):
                if len(line) < 140 and not any(sw in line_lower for sw in summary_words):
                    extracted_edu.append(line)
    
    if not extracted_edu:
        extracted_edu = ["Degree details not specified"]

    # 7. Certifications Extraction
    extracted_certs = []
    for line in sections["certifications"]:
        if len(line) > 3:
            extracted_certs.append(line)
            
    if not extracted_certs:
        for line in lines:
            if any(kw in line.lower() for kw in ["certified", "certification", "aws certified", "pmp", "coursera", "udemy"]):
                extracted_certs.append(line)

    # 8. Experience Calculation (strictly from Work Experience section or explicit experience keywords)
    exp_years = 0.0
    
    # Text to analyze for work experience: prefer Experience section if populated
    exp_text = "\n".join(sections["experience"]) if sections["experience"] else raw_text
    
    # 1. Direct explicit years mention (e.g., "3+ years", "1.5 yrs experience")
    exp_matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|work|industry)", exp_text, re.IGNORECASE)
    if exp_matches:
        try:
            valid_vals = [float(x) for x in exp_matches if float(x) <= 45.0]
            if valid_vals:
                exp_years = max(valid_vals)
        except Exception:
            exp_years = 0.0

    # 2. Month-based internship/work duration (e.g., "6 months internship")
    if exp_years == 0.0:
        month_matches = re.findall(r"(\d+)\s*(?:months?|mos?)\s*(?:internship|experience|duration|tenure)?", exp_text, re.IGNORECASE)
        if month_matches:
            try:
                m_val = max(int(m) for m in month_matches if int(m) <= 48)
                exp_years = round(m_val / 12.0, 1)
            except Exception:
                exp_years = 0.0

    # 3. Precise date range calculation (only if Experience section is present or explicit job keywords exist)
    if exp_years == 0.0 and (sections["experience"] or any(k in raw_text.lower() for k in ["work history", "employment", "internship"])):
        target_text = "\n".join(sections["experience"]) if sections["experience"] else raw_text
        date_ranges = re.findall(r"\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?(20\d{2})\s*[-–—to]+\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?(20\d{2}|present|current)\b", target_text, re.IGNORECASE)
        total_months = 0
        current_year = 2026
        for start_str, end_str in date_ranges:
            start_y = int(start_str)
            end_y = current_year if end_str.lower() in ["present", "current"] else int(end_str)
            if 1990 <= start_y <= current_year and end_y >= start_y:
                diff = end_y - start_y
                if diff > 0 and diff <= 40:
                    total_months += diff * 12

        if total_months > 0:
            exp_years = round(total_months / 12.0, 1)

    return CandidateProfile(
        full_name=full_name,
        email=email,
        phone=phone,
        total_experience_years=exp_years,
        parsed_education=extracted_edu[:5],
        skills=list(found_skills),
        projects=extracted_projects[:6],
        certifications=extracted_certs[:5],
    )


# --- LLM Extraction Logic ---

PROMPT_TEMPLATE = """You are an expert AI Resume and Job Description Parser.
Extract structured information from the provided raw text according to the target schema.
Be concise, accurate, and return strictly valid JSON matching the schema.

RAW TEXT:
---
{raw_text}
---
"""


def extract_candidate_with_llm(
    raw_text: str, provider: str = "google", api_key: Optional[str] = None
) -> CandidateProfile:
    """
    Extracts CandidateProfile using OpenAI or Gemini APIs with strict Pydantic parsing.
    Falls back to regex parsing on rate limits or API missing/failure.
    """
    if not api_key:
        logger.info("No API key provided. Using rule-based fallback parser.")
        return extract_candidate_fallback(raw_text)

    try:
        if provider.lower() in ["openai", "gpt-4", "gpt-3.5-turbo"]:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional HR Resume parser. Extract all candidate information accurately.",
                    },
                    {"role": "user", "content": raw_text},
                ],
                response_format=CandidateProfile,
            )
            return response.choices[0].message.parsed

        elif provider.lower() in ["google", "gemini"]:
            # Try google-genai SDK first
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                prompt = (
                    "Extract structured candidate information from the following resume text:\n\n"
                    + raw_text
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CandidateProfile,
                    ),
                )
                return CandidateProfile.model_validate_json(response.text)
            except ImportError:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = (
                    "Extract structured candidate info as JSON with keys: full_name, email, phone, "
                    "total_experience_years (float), parsed_education (list of str), skills (list of lowercase str), "
                    "projects (list of str), certifications (list of str).\n\nRESUME TEXT:\n"
                    + raw_text
                )
                res = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"},
                )
                data = json.loads(res.text)
                return CandidateProfile(**data)

    except Exception as e:
        logger.error(f"LLM extraction failed: {e}. Falling back to rule-based parser.")
        return extract_candidate_fallback(raw_text)

    return extract_candidate_fallback(raw_text)


def extract_job_fallback(raw_text: str) -> JobProfile:
    """
    Intelligent heuristic extractor for raw job descriptions copied from tools/sites (LinkedIn, Indeed, PDF, etc.).
    Extracts Title, Role, Required Skills, Min Experience, Education, and Certifications.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
    # 1. Job Title & Role heuristic
    title = "Software Engineer"
    role = "Software Engineer"
    for line in lines[:8]:
        # Check if line has Title: or Position: or Role:
        m = re.search(r"(?:job\s*title|position|role|title)\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if m:
            title = m.group(1).strip()[:70]
            role = title
            break
    if title == "Software Engineer" and lines:
        first_line = lines[0]
        if len(first_line) < 65 and not re.search(r"(about us|company|description|overview|requirements)", first_line, re.IGNORECASE):
            title = first_line.strip()
            role = title

    # 2. Required Skills Extraction
    found_skills = []
    text_lower = raw_text.lower()
    for s in KNOWN_SKILLS:
        if re.search(r"\b" + re.escape(s) + r"\b", text_lower):
            found_skills.append(s)

    # 3. Minimum Experience Extraction
    min_exp = 0.0
    exp_matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:to\s*\d+\s*)?years?(?:\s+of)?(?:\s+relevant|\s+work|\s+industry)?\s+experience",
        text_lower,
    )
    if exp_matches:
        try:
            min_exp = float(exp_matches[0])
        except Exception:
            min_exp = 2.0
    elif "senior" in title.lower() or "lead" in title.lower():
        min_exp = 5.0
    elif "junior" in title.lower() or "entry" in title.lower() or "intern" in title.lower():
        min_exp = 0.0
    else:
        min_exp = 2.0

    # 4. Education Extraction
    req_edu = "Bachelor's"
    if re.search(r"\b(ph\.?d|doctorate)\b", text_lower):
        req_edu = "Ph.D."
    elif re.search(r"\b(master'?s|m\.s|m\.tech|m\.e|mba)\b", text_lower):
        req_edu = "Master's"
    elif re.search(r"\b(bachelor'?s|b\.s|b\.tech|b\.e|undergraduate)\b", text_lower):
        req_edu = "Bachelor's"
    elif re.search(r"\b(diploma|associate)\b", text_lower):
        req_edu = "Associate / Diploma"

    # 5. Certifications
    certs = []
    if "aws" in text_lower and "certified" in text_lower:
        certs.append("AWS Certified")
    if "azure" in text_lower and "certified" in text_lower:
        certs.append("Microsoft Azure Certified")
    if "gcp" in text_lower and "certified" in text_lower:
        certs.append("Google Cloud Certified")
    if "pmp" in text_lower:
        certs.append("PMP")

    # 6. Description summary
    desc_summary = raw_text[:800].strip()

    return JobProfile(
        title=title,
        role=role,
        description=desc_summary,
        required_skills=found_skills,
        min_experience=min_exp,
        required_education=req_edu,
        certifications=certs,
    )


def extract_job_with_llm(
    raw_text: str, provider: str = "google", api_key: Optional[str] = None
) -> JobProfile:
    """
    Extracts structured JobProfile from raw job description text via LLM or robust fallback.
    """
    if not api_key:
        return extract_job_fallback(raw_text)

    try:
        if provider.lower() in ["openai", "gpt-4"]:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract structured job requirements from job description.",
                    },
                    {"role": "user", "content": raw_text},
                ],
                response_format=JobProfile,
            )
            return response.choices[0].message.parsed

        elif provider.lower() in ["google", "gemini"]:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents="Extract job profile details:\n" + raw_text,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=JobProfile,
                    ),
                )
                return JobProfile.model_validate_json(response.text)
            except ImportError:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = (
                    "Extract job profile as JSON with keys: title, role, description, required_skills (lowercase list), "
                    "min_experience (float), required_education (str), certifications (list).\n\nTEXT:\n"
                    + raw_text
                )
                res = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"},
                )
                return JobProfile(**json.loads(res.text))
    except Exception as e:
        logger.error(f"Job extraction failed: {e}. Falling back to rule-based extractor.")

    return extract_job_fallback(raw_text)

