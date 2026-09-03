import io
import json
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import Candidate, Job, Evaluation

logger = logging.getLogger(__name__)

# --- Rule-Based Learning Path Map for Common Tech Skills ---
SKILL_COURSE_MAP = {
    "python": "Python for Everybody Specialization (Coursera / University of Michigan)",
    "sql": "Complete SQL Bootcamp (Udemy / Jose Portilla)",
    "postgresql": "PostgreSQL Mastery & Database Design (Udemy)",
    "aws": "AWS Certified Solutions Architect Associate (AWS Training / Udemy)",
    "docker": "Docker Mastery with Kubernetes (Udemy)",
    "kubernetes": "Certified Kubernetes Application Developer (CKAD) (Linux Foundation)",
    "react": "React - The Complete Guide (Udemy / Maximilian Schwarzmüller)",
    "fastapi": "FastAPI Web Development Bootcamp (Real Python)",
    "machine learning": "Machine Learning Specialization by Andrew Ng (Coursera)",
    "pytorch": "Deep Learning with PyTorch (PyTorch Official / Udacity)",
    "tensorflow": "TensorFlow Developer Professional Certificate (Coursera)",
    "nlp": "Natural Language Processing Specialization (DeepLearning.AI)",
    "spacy": "Advanced NLP with spaCy (spaCy Official Course)",
    "system design": "Grokking the System Design Interview (DesignGurus)",
    "git": "Git & GitHub - The Complete Guide (Udemy)",
    "tableau": "Tableau Desktop Specialist Certification (Tableau / Udemy)",
}


def calculate_skill_gap_pct(missing_skills: List[str], required_skills: List[str]) -> float:
    """Calculates Skill Gap % = (|Missing Skills| / |Total Required Skills|) * 100."""
    if not required_skills:
        return 0.0
    gap_pct = (len(missing_skills) / len(required_skills)) * 100.0
    return round(gap_pct, 2)


def generate_training_recommendations(
    missing_skills: List[str],
    provider: str = "google",
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generates automated course/learning recommendations for missing skills.
    Uses LLM if API key is provided, otherwise falls back to pre-defined mapping.
    """
    if not missing_skills:
        return {"Status": "No missing skills identified! Candidate meets all required technical skills."}

    recommendations = {}

    if api_key:
        try:
            prompt = (
                "Suggest 1 concise, highly-reputable online course or certification for each of these missing skills: "
                + ", ".join(missing_skills)
                + ". Return JSON object mapping skill -> course recommendation string."
            )
            if provider.lower() in ["google", "gemini"]:
                try:
                    from google import genai

                    client = genai.Client(api_key=api_key)
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config={"response_mime_type": "application/json"},
                    )
                    return json.loads(res.text)
                except Exception:
                    import google.generativeai as genai

                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    res = model.generate_content(
                        prompt, generation_config={"response_mime_type": "application/json"}
                    )
                    return json.loads(res.text)
            elif provider.lower() in ["openai", "gpt-4"]:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                return json.loads(res.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LLM course generation failed: {e}. Falling back to default map.")

    # Rule-based fallback
    for skill in missing_skills:
        skill_clean = skill.strip().lower()
        if skill_clean in SKILL_COURSE_MAP:
            recommendations[skill] = SKILL_COURSE_MAP[skill_clean]
        else:
            recommendations[skill] = f"Recommended: Search for top-rated '{skill}' courses on Coursera, Udemy, or official docs."

    return recommendations


# --- Plotly Chart Generators (Light Executive Theme) ---

LIGHT_LAYOUT = dict(
    paper_bgcolor="rgba(255, 255, 255, 0)",
    plot_bgcolor="rgba(255, 255, 255, 0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#0f172a"),
)


def plot_candidate_radar(
    cand_name: str,
    skill_pct: float,
    exp_pct: float,
    edu_pct: float,
    hiring_score: float,
) -> go.Figure:
    """Sleek light-theme Radar chart comparing Candidate performance across core metrics vs 100% target baseline."""
    categories = ["Skill Match", "Experience Match", "Education Fit", "Overall Hiring Score"]
    cand_values = [skill_pct, exp_pct, edu_pct, hiring_score]

    fig = go.Figure()

    # Baseline 100% target profile
    fig.add_trace(
        go.Scatterpolar(
            r=[100, 100, 100, 100, 100],
            theta=categories + [categories[0]],
            fill="toself",
            name="Target 100% Baseline",
            line=dict(color="rgba(148, 163, 184, 0.6)", width=1.5, dash="dash"),
            fillcolor="rgba(241, 245, 249, 0.4)",
            hoverinfo="skip",
        )
    )

    # Candidate profile
    fig.add_trace(
        go.Scatterpolar(
            r=cand_values + [cand_values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=f"{cand_name}",
            line=dict(color="#2563eb", width=3),
            fillcolor="rgba(37, 99, 235, 0.25)",
            marker=dict(size=8, color="#2563eb"),
            hovertemplate="<b>%{theta}</b>: %{r:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        polar=dict(
            bgcolor="rgba(248, 250, 252, 0.8)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="#64748b", size=9),
                gridcolor="rgba(203, 213, 225, 0.6)",
                linecolor="rgba(203, 213, 225, 0.8)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#0f172a", size=11, family="Plus Jakarta Sans", weight="bold"),
                gridcolor="rgba(203, 213, 225, 0.6)",
                linecolor="rgba(203, 213, 225, 0.8)",
            ),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5, font=dict(color="#334155")),
        title=dict(
            text=f"🎯 Competency Radar Profile: <b>{cand_name}</b>",
            font=dict(size=14, color="#0f172a"),
        ),
        height=380,
        margin=dict(l=30, r=30, t=40, b=40),
    )
    return fig


def plot_skills_gauge(skill_match_pct: float, hiring_score: float) -> go.Figure:
    """Dual gauge visual indicator for Skill Fit and Overall Hiring Score in Light Theme."""
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=skill_match_pct,
            title={"text": "<b>Skill Match %</b>", "font": {"size": 13, "color": "#475569"}},
            number={"suffix": "%", "font": {"size": 26, "color": "#2563eb"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#94a3b8", "tickwidth": 1},
                "bar": {"color": "#2563eb", "thickness": 0.3},
                "bgcolor": "rgba(241, 245, 249, 0.7)",
                "borderwidth": 1,
                "bordercolor": "rgba(226, 232, 240, 1)",
                "steps": [
                    {"range": [0, 50], "color": "rgba(254, 226, 226, 0.7)"},
                    {"range": [50, 75], "color": "rgba(254, 243, 199, 0.7)"},
                    {"range": [75, 100], "color": "rgba(209, 250, 229, 0.7)"},
                ],
            },
            domain={"x": [0, 0.48], "y": [0, 1]},
        )
    )

    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=hiring_score,
            title={"text": "<b>Overall Hiring Score</b>", "font": {"size": 13, "color": "#475569"}},
            number={"suffix": "%", "font": {"size": 26, "color": "#059669"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#94a3b8", "tickwidth": 1},
                "bar": {"color": "#059669", "thickness": 0.3},
                "bgcolor": "rgba(241, 245, 249, 0.7)",
                "borderwidth": 1,
                "bordercolor": "rgba(226, 232, 240, 1)",
                "steps": [
                    {"range": [0, 50], "color": "rgba(254, 226, 226, 0.7)"},
                    {"range": [50, 75], "color": "rgba(254, 243, 199, 0.7)"},
                    {"range": [75, 100], "color": "rgba(209, 250, 229, 0.7)"},
                ],
            },
            domain={"x": [0.52, 1], "y": [0, 1]},
        )
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        height=220,
        margin=dict(l=15, r=15, t=30, b=10),
    )
    return fig


def plot_skills_donut(matched_count: int, missing_count: int, additional_count: int) -> go.Figure:
    """Modern Donut chart showing distribution of matched, missing, and bonus skills."""
    labels = ["Matched Core Skills", "Missing Gap Skills", "Additional Bonus Skills"]
    values = [matched_count, missing_count, additional_count]
    colors_list = ["#10b981", "#f43f5e", "#8b5cf6"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors_list, line=dict(color="#ffffff", width=2)),
                textinfo="label+value",
                hoverinfo="label+value+percent",
                textfont=dict(color="#0f172a", size=11),
            )
        ]
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        title=dict(text="📊 Skill Portfolio Distribution", font=dict(size=14, color="#0f172a")),
        showlegend=False,
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_skill_coverage_matrix(evaluations: List[Evaluation], required_skills: List[str]) -> go.Figure:
    """
    Heatmap Matrix displaying which candidates possess which required skills.
    Rows: Candidate Names, Columns: Required Skills (1 = Possessed / Green, 0 = Missing / Slate).
    """
    if not evaluations or not required_skills:
        fig = go.Figure()
        fig.update_layout(**LIGHT_LAYOUT, title="No candidate evaluation data for matrix.")
        return fig

    candidates_names = []
    matrix = []

    for ev in evaluations:
        cand_name = ev.candidate.full_name if ev.candidate else f"Cand #{ev.candidate_id}"
        candidates_names.append(cand_name)
        
        matched_set = set(s.lower().strip() for s in (ev.matched_skills or []))
        row = [1 if skill.lower().strip() in matched_set else 0 for skill in required_skills]
        matrix.append(row)

    # Clean skill labels
    clean_skills = [s.title() for s in required_skills]

    # Custom discrete colorscale (0 = Light Slate Gray, 1 = Emerald Green)
    colorscale = [
        [0.0, "#e2e8f0"],    # Missing / Light Slate
        [0.5, "#e2e8f0"],
        [0.51, "#10b981"],  # Matched / Emerald Green
        [1.0, "#10b981"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=clean_skills,
            y=candidates_names,
            colorscale=colorscale,
            showscale=False,
            xgap=4,
            ygap=4,
            hovertemplate="<b>Candidate:</b> %{y}<br><b>Skill:</b> %{x}<br><b>Status:</b> %{customdata}<extra></extra>",
            customdata=[["✅ Covered" if val == 1 else "❌ Missing Gap" for val in row] for row in matrix],
        )
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        title=dict(text="🧩 Candidate Skill Coverage Heatmap Matrix", font=dict(size=14, color="#0f172a")),
        xaxis=dict(tickangle=-30, tickfont=dict(size=10, color="#475569")),
        yaxis=dict(tickfont=dict(size=11, color="#0f172a"), autorange="reversed"),
        height=max(260, len(candidates_names) * 45 + 100),
        margin=dict(l=40, r=20, t=50, b=60),
    )
    return fig


def plot_top_candidates_bar(evaluations: List[Evaluation]) -> go.Figure:
    """Horizontal stacked competency breakdown bar chart comparing all candidates."""
    if not evaluations:
        fig = go.Figure()
        fig.update_layout(**LIGHT_LAYOUT, title="No candidate evaluations available.")
        return fig

    cand_names = []
    skill_scores = []
    hiring_scores = []

    # Sort by overall hiring score
    sorted_evals = sorted(evaluations, key=lambda x: x.overall_hiring_score, reverse=False)

    for ev in sorted_evals:
        c_name = ev.candidate.full_name if ev.candidate else f"Cand #{ev.candidate_id}"
        cand_names.append(c_name)
        skill_scores.append(round(ev.skill_match_pct, 1))
        hiring_scores.append(round(ev.overall_hiring_score, 1))

    fig = go.Figure()

    # Skill Match Bar
    fig.add_trace(
        go.Bar(
            y=cand_names,
            x=skill_scores,
            name="Skill Match %",
            orientation="h",
            marker=dict(color="#3b82f6", line=dict(color="rgba(0,0,0,0.05)", width=1)),
            text=[f"{s}%" for s in skill_scores],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Skill Match: %{x}%<extra></extra>",
        )
    )

    # Overall Score Bar
    fig.add_trace(
        go.Bar(
            y=cand_names,
            x=hiring_scores,
            name="Overall Hiring Score %",
            orientation="h",
            marker=dict(color="#10b981", line=dict(color="rgba(0,0,0,0.05)", width=1)),
            text=[f"{h}%" for h in hiring_scores],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Composite Score: %{x}%<extra></extra>",
        )
    )

    fig.update_layout(
        **LIGHT_LAYOUT,
        barmode="group",
        title=dict(text="🏆 Candidate Ranking & Competency Comparison", font=dict(size=14, color="#0f172a")),
        xaxis=dict(range=[0, 105], title="Score (%)", gridcolor="rgba(226, 232, 240, 0.8)"),
        yaxis=dict(title="", tickfont=dict(color="#0f172a", size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(color="#334155")),
        height=max(320, len(cand_names) * 55 + 80),
        margin=dict(l=20, r=20, t=40, b=50),
    )
    return fig


def plot_skills_breakdown(matched_skills: List[str], missing_skills: List[str]) -> go.Figure:
    """Horizontal bar chart showing matched vs missing skills count."""
    return plot_skills_donut(len(matched_skills), len(missing_skills), 0)



# --- Report PDF & CSV Generation Helpers ---


def export_evaluation_pdf(
    candidate: Candidate, job: Job, evaluation: Evaluation
) -> bytes:
    """Generates a downloadable PDF summary report using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=15,
    )
    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = styles["Normal"]

    story = []

    # Title & Header
    story.append(Paragraph("AI Recruitment Copilot - Candidate Evaluation Report", title_style))
    story.append(Spacer(1, 10))

    # Candidate & Job Details Table
    details_data = [
        [Paragraph("<b>Candidate Name:</b>", body_style), Paragraph(candidate.full_name, body_style)],
        [Paragraph("<b>Target Job Role:</b>", body_style), Paragraph(job.title, body_style)],
        [Paragraph("<b>Overall Hiring Score:</b>", body_style), Paragraph(f"<b>{evaluation.overall_hiring_score}%</b> (Rank #{evaluation.rank})", body_style)],
        [Paragraph("<b>Skill Match %:</b>", body_style), Paragraph(f"{evaluation.skill_match_pct}%", body_style)],
        [Paragraph("<b>Experience:</b>", body_style), Paragraph(f"{candidate.parsed_experience} years (Req: {job.min_experience} yrs)", body_style)],
        [Paragraph("<b>Email / Contact:</b>", body_style), Paragraph(f"{candidate.email or 'N/A'} | {candidate.phone or 'N/A'}", body_style)],
    ]
    t = Table(details_data, colWidths=[150, 380])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(t)
    story.append(Spacer(1, 15))

    # Skills Analysis Section
    story.append(Paragraph("Skills Match Breakdown", h2_style))
    matched_str = ", ".join(evaluation.matched_skills) if evaluation.matched_skills else "None"
    missing_str = ", ".join(evaluation.missing_skills) if evaluation.missing_skills else "None"

    skills_data = [
        [Paragraph("<b>Matched Skills</b>", body_style), Paragraph(matched_str, body_style)],
        [Paragraph("<b>Missing Skills</b>", body_style), Paragraph(missing_str, body_style)],
    ]
    st = Table(skills_data, colWidths=[150, 380])
    st.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(st)
    story.append(Spacer(1, 15))

    # Automated Training Recommendations
    story.append(Paragraph("Skill Gap & Learning Path Recommendations", h2_style))
    recs = generate_training_recommendations(evaluation.missing_skills)
    for skill, course in recs.items():
        story.append(Paragraph(f"• <b>{skill}:</b> {course}", body_style))
        story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def export_evaluations_csv(evaluations: Any, job_title: Optional[str] = None) -> str:
    """Converts evaluation records (models, dicts, or dataframes) to a clean CSV string."""
    if not evaluations:
        return "Rank,Candidate Name,Overall Hiring Score,Skill Match %,Matched Skills,Missing Skills\n"

    rows = []
    for ev in evaluations:
        if hasattr(ev, "candidate"):
            cand = getattr(ev, "candidate", None)
            cand_name = cand.full_name if cand else f"Candidate #{getattr(ev, 'candidate_id', '')}"
            cand_email = cand.email if cand else "N/A"
            cand_exp = cand.parsed_experience if cand else 0.0
            rows.append({
                "Rank": getattr(ev, "rank", 0),
                "Candidate Name": cand_name,
                "Candidate Email": cand_email,
                "Experience (Years)": cand_exp,
                "Overall Hiring Score (%)": getattr(ev, "overall_hiring_score", 0.0),
                "Skill Match (%)": getattr(ev, "skill_match_pct", 0.0),
                "Matched Skills": "; ".join(getattr(ev, "matched_skills", []) or []),
                "Missing Skills": "; ".join(getattr(ev, "missing_skills", []) or []),
                "Job Title": job_title or (ev.job.title if hasattr(ev, "job") and ev.job else ""),
            })
        elif isinstance(ev, dict):
            rows.append(ev)
        else:
            rows.append({"Record": str(ev)})

    df = pd.DataFrame(rows)
    return df.to_csv(index=False)

