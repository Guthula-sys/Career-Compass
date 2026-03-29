import os
import json
import sqlite3
import hashlib
from io import BytesIO

import bcrypt
import docx
import pandas as pd
import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from streamlit.errors import StreamlitSecretNotFoundError


load_dotenv(encoding="utf-8-sig")

st.set_page_config(
    page_title="Career Recommendation System ",
    page_icon="🎯",
    layout="wide",
)


DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "data.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "career_compass.db")

ROADMAP_PROMPT_MARKDOWN = """
You are an expert career advisor and technical mentor.

Create a detailed personalized roadmap in markdown.

User Profile:
- Current Role: {current_role}
- Current Skills: {skills}
- Target Role: {target_role}
- Time Commitment: {time_commitment} hours/week

Include:
1. Skill gap analysis
2. Learning path
3. Projects
4. Certifications
5. Interview prep
6. Salary info

# Career Roadmap: {current_role} to {target_role}
"""


ATS_PROMPT = """
You are an ATS expert.

Analyze this resume for role: {role}

Provide:
1. ATS Score (out of 100)
2. Missing Keywords
3. Strengths
4. Improvements
5. Formatting Tips

Resume:
{resume_text}

Return in markdown.
"""


INTERVIEW_PROMPT = """
You are an expert technical interviewer and career coach.

Generate interview questions for this candidate profile.

Candidate details:
- Target Role: {target_role}
- Current Skills: {skills}
- Background: {background}

Create:
1. 5 technical interview questions
2. 3 project-based or scenario questions
3. 3 HR or behavioral questions
4. 3 short preparation tips

Return in clean markdown with clear headings and bullet points.
"""


INTERVIEW_EVAL_PROMPT = """
You are an expert interviewer evaluating a candidate's answer.

Candidate profile:
- Target Role: {target_role}
- Current Skills: {skills}

Interview Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer and provide:
1. Score out of 10
2. Strengths
3. Weaknesses or missing points
4. A stronger sample answer
5. 3 short improvement tips

Return in clean markdown with clear headings and bullet points.
"""


COURSE_PROMPT = """
You are a career learning advisor.

Create practical course and learning recommendations for this learner.

Learner profile:
- Target Role: {target_role}
- Current Skills: {skills}
- Missing Skills: {missing_skills}

Provide:
1. 5 recommended learning topics or course titles
2. Why each one matters for the role
3. A suggested learning order
4. 3 mini project ideas based on the missing skills

Return in clean markdown with clear headings and bullet points.
"""


RESUME_REWRITE_PROMPT = """
You are an expert resume writer and ATS optimization specialist.

Rewrite and improve this resume content for the target role below.

Target Role: {role}
Resume Text:
{resume_text}

Provide:
1. A stronger professional summary
2. 5 improved bullet points for skills/projects/experience
3. Keyword suggestions to include
4. 3 formatting improvements

Return in clean markdown with clear headings and bullet points.
"""


def inject_custom_css():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

            html, body, [class*="css"]  {
                font-family: 'Manrope', sans-serif;
            }

            html, body, .stApp, p, label, span, div, h1, h2, h3, h4, h5, h6 {
                color: #0f172a;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(11, 110, 79, 0.20), transparent 28%),
                    radial-gradient(circle at top right, rgba(255, 179, 71, 0.18), transparent 25%),
                    linear-gradient(180deg, #f6fbf8 0%, #eef6f2 100%);
            }

            [data-testid="stSidebar"] {
                background:
                    linear-gradient(180deg, #18352f 0%, #1f473d 55%, #294f45 100%);
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }

            [data-testid="stSidebar"] * {
                color: #f8fafc;
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] div {
                color: #f8fafc !important;
            }

            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                color: #f8fafc !important;
            }

            [data-testid="stSidebar"] .stProgress > div > div > div > div {
                background: linear-gradient(90deg, #f4a259 0%, #ff6b6b 100%);
            }

            [data-testid="stSidebar"] .stProgress > div > div > div {
                background: rgba(255, 255, 255, 0.12);
            }

            .block-container {
                padding-top: 2rem;
                padding-bottom: 2.5rem;
            }

            .hero-card {
                background: linear-gradient(135deg, #0b6e4f 0%, #1f8a70 55%, #f4a259 100%);
                color: #ffffff;
                border-radius: 24px;
                padding: 2rem;
                box-shadow: 0 24px 60px rgba(31, 138, 112, 0.18);
                margin-bottom: 1.5rem;
            }

            .hero-card h1 {
                font-size: 2.5rem;
                font-weight: 800;
                margin-bottom: 0.5rem;
            }

            .hero-card p {
                max-width: 700px;
                font-size: 1.02rem;
                line-height: 1.7;
                margin-bottom: 0;
            }

            .section-card {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid rgba(11, 110, 79, 0.09);
                border-radius: 20px;
                padding: 1.2rem 1.3rem;
                box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
                backdrop-filter: blur(6px);
                color: #0f172a;
            }

            [data-testid="stTabPanel"] {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(11, 110, 79, 0.09);
                border-radius: 24px;
                padding: 1.4rem 1.5rem 1.6rem 1.5rem;
                box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
                margin-top: 0.6rem;
            }

            .mini-stat {
                background: #ffffff;
                border: 1px solid rgba(11, 110, 79, 0.10);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
                min-height: 120px;
            }

            .mini-stat-label {
                color: #4b6358;
                font-size: 0.88rem;
                margin-bottom: 0.35rem;
            }

            .mini-stat-value {
                color: #0f172a;
                font-size: 1.8rem;
                font-weight: 800;
                margin-bottom: 0.2rem;
            }

            .chip {
                display: inline-block;
                padding: 0.4rem 0.75rem;
                border-radius: 999px;
                margin: 0.2rem 0.35rem 0.2rem 0;
                font-size: 0.92rem;
                font-weight: 600;
            }

            .chip.good {
                background: rgba(11, 110, 79, 0.12);
                color: #0b6e4f;
            }

            .chip.warn {
                background: rgba(217, 119, 6, 0.14);
                color: #b45309;
            }

            .sidebar-note {
                background: rgba(255,255,255,0.14);
                border-radius: 18px;
                padding: 1rem;
                border: 1px solid rgba(255, 255, 255, 0.16);
                color: #f8fafc;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
            }

            .stTabs [data-baseweb="tab-list"] button {
                color: #475569;
            }

            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                color: #ef4444;
            }

            .stMarkdown, .stText, .stCaption, .stSubheader, .stHeader {
                color: #0f172a;
            }

            [data-testid="stMetricValue"],
            [data-testid="stMetricLabel"],
            [data-testid="stMarkdownContainer"],
            [data-testid="stText"],
            [data-testid="stCaptionContainer"] {
                color: #0f172a;
            }

            [data-testid="stForm"] label,
            .stTextInput label,
            .stTextArea label,
            .stSelectbox label,
            .stSlider label,
            .stFileUploader label {
                color: #334155 !important;
                font-weight: 600;
            }

            .stTextInput input,
            .stTextArea textarea,
            .stSelectbox div[data-baseweb="select"] > div,
            .stFileUploader section {
                color: #0f172a !important;
                background: #ffffff !important;
            }

            div[role="listbox"] {
                background: #111827 !important;
                color: #f8fafc !important;
            }

            div[role="option"] {
                background: #111827 !important;
                color: #f8fafc !important;
            }

            div[role="listbox"] *,
            div[role="option"] *,
            ul[role="listbox"] *,
            li[role="option"] * {
                color: #f8fafc !important;
                fill: #f8fafc !important;
            }

            div[role="option"]:hover {
                background: #1f2937 !important;
                color: #ffffff !important;
            }

            div[role="option"][aria-selected="true"] {
                background: #374151 !important;
                color: #ffffff !important;
            }

            pre, code, .stCodeBlock, .stCode {
                background: #111827 !important;
                color: #f8fafc !important;
            }

            pre *, code * {
                color: #f8fafc !important;
            }

            .stMarkdown pre {
                background: #111827 !important;
                border-radius: 16px !important;
                border: 1px solid rgba(255, 255, 255, 0.06);
                padding: 1rem !important;
            }

            .stMarkdown pre code {
                color: #f8fafc !important;
                text-shadow: none !important;
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #94a3b8 !important;
            }

            .stButton > button,
            .stDownloadButton > button,
            .stFormSubmitButton > button {
                background: linear-gradient(135deg, #0b6e4f 0%, #1f8a70 100%) !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 14px !important;
                font-weight: 700 !important;
                padding: 0.7rem 1rem !important;
                box-shadow: 0 14px 30px rgba(31, 138, 112, 0.22) !important;
                transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover,
            .stFormSubmitButton > button:hover {
                transform: translateY(-1px);
                filter: brightness(1.03);
                box-shadow: 0 18px 34px rgba(31, 138, 112, 0.28) !important;
            }

            .stButton > button:focus,
            .stDownloadButton > button:focus,
            .stFormSubmitButton > button:focus {
                box-shadow: 0 0 0 0.2rem rgba(31, 138, 112, 0.18) !important;
            }

            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #ef7d57 0%, #f4a259 100%) !important;
                box-shadow: 0 16px 32px rgba(244, 162, 89, 0.26) !important;
            }

            .stButton > button[kind="primary"]:hover {
                box-shadow: 0 18px 36px rgba(244, 162, 89, 0.32) !important;
            }

            .stSlider [data-testid="stTickBarMin"],
            .stSlider [data-testid="stTickBarMax"] {
                color: #334155 !important;
            }

            .st-emotion-cache-16idsys p,
            .st-emotion-cache-16txtl3,
            .st-emotion-cache-10trblm,
            .st-emotion-cache-ue6h4q {
                color: #0f172a;
            }

            .feature-card {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(11, 110, 79, 0.10);
                border-radius: 20px;
                padding: 1.2rem;
                min-height: 180px;
                box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
            }

            .feature-kicker {
                display: inline-block;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #0b6e4f;
                margin-bottom: 0.65rem;
            }

            .feature-title {
                font-size: 1.2rem;
                font-weight: 800;
                color: #0f172a;
                margin-bottom: 0.45rem;
            }

            .feature-copy {
                color: #475569;
                line-height: 1.7;
                font-size: 0.96rem;
            }

            .footer-card {
                margin-top: 1.6rem;
                background: linear-gradient(135deg, rgba(11, 110, 79, 0.10), rgba(244, 162, 89, 0.14));
                border: 1px solid rgba(11, 110, 79, 0.10);
                border-radius: 22px;
                padding: 1.25rem 1.4rem;
                color: #1e293b;
            }

            .step-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.6rem;
                margin-bottom: 0.7rem;
                padding: 0.45rem 0.8rem;
                border-radius: 999px;
                background: linear-gradient(135deg, rgba(11, 110, 79, 0.10), rgba(244, 162, 89, 0.16));
                border: 1px solid rgba(11, 110, 79, 0.12);
                color: #0b6e4f;
                font-weight: 800;
                width: fit-content;
            }

            .step-number {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.9rem;
                height: 1.9rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #0b6e4f 0%, #1f8a70 100%);
                color: #ffffff;
                font-size: 0.92rem;
                box-shadow: 0 10px 22px rgba(31, 138, 112, 0.22);
            }

            .step-label {
                font-size: 0.88rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            .history-card {
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 0.75rem 0.85rem;
                margin-bottom: 0.7rem;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
            }

            .history-type {
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #f4d58d !important;
                margin-bottom: 0.25rem;
            }

            .history-title {
                font-size: 0.92rem;
                font-weight: 700;
                color: #ffffff !important;
                line-height: 1.45;
                margin-bottom: 0.25rem;
            }

            .history-date {
                font-size: 0.78rem;
                color: rgba(248, 250, 252, 0.8) !important;
            }

            .dashboard-history-card {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(11, 110, 79, 0.10);
                border-radius: 18px;
                padding: 1rem 1.05rem;
                box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
                min-height: 165px;
            }

            .dashboard-history-type {
                display: inline-block;
                padding: 0.3rem 0.55rem;
                border-radius: 999px;
                background: rgba(11, 110, 79, 0.10);
                color: #0b6e4f;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                margin-bottom: 0.65rem;
            }

            .dashboard-history-title {
                font-size: 1rem;
                font-weight: 800;
                color: #0f172a;
                line-height: 1.45;
                margin-bottom: 0.45rem;
            }

            .dashboard-history-date {
                color: #64748b;
                font-size: 0.84rem;
                margin-bottom: 0.7rem;
            }

            .dashboard-history-preview {
                color: #475569;
                font-size: 0.92rem;
                line-height: 1.6;
            }

            @media (max-width: 900px) {
                .block-container {
                    padding-top: 1rem;
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                    padding-bottom: 1.4rem;
                }

                .hero-card {
                    padding: 1.2rem;
                    border-radius: 20px;
                }

                .hero-card h1 {
                    font-size: 1.9rem;
                    line-height: 1.2;
                }

                .hero-card p {
                    font-size: 0.98rem;
                    line-height: 1.6;
                }

                .mini-stat {
                    min-height: auto;
                    padding: 0.95rem 1rem;
                }

                .feature-card {
                    min-height: auto;
                    padding: 1rem;
                }

                [data-testid="stTabPanel"] {
                    padding: 1rem;
                    border-radius: 18px;
                }

                .footer-card {
                    padding: 1rem 1.1rem;
                    border-radius: 18px;
                }

                .step-badge {
                    margin-bottom: 0.55rem;
                }

                .stButton > button,
                .stDownloadButton > button,
                .stFormSubmitButton > button {
                    min-height: 48px !important;
                }
            }

            @media (max-width: 640px) {
                .hero-card h1 {
                    font-size: 1.65rem;
                }

                .hero-card p {
                    font-size: 0.92rem;
                }

                .mini-stat-value {
                    font-size: 1.5rem;
                }

                .feature-title {
                    font-size: 1.05rem;
                }

                .feature-copy {
                    font-size: 0.9rem;
                }

                [data-testid="stTabPanel"] {
                    padding: 0.9rem;
                }

                .step-number {
                    width: 1.7rem;
                    height: 1.7rem;
                    font-size: 0.84rem;
                }

                .step-label {
                    font-size: 0.78rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_data():
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip().str.lower()
    return df


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, stored_hash):
    if not stored_hash:
        return False, None

    # Backward compatibility for earlier SHA-256 users.
    if stored_hash.startswith("$2"):
        is_valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        return is_valid, None

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if legacy_hash == stored_hash:
        upgraded_hash = hash_password(password)
        return True, upgraded_hash

    return False, None


def create_user(full_name, email, password):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name.strip(), email.strip().lower(), hash_password(password)),
        )
        conn.commit()
        user = conn.execute(
            "SELECT id, full_name, email FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        return dict(user), None
    except sqlite3.IntegrityError:
        return None, "An account with this email already exists."
    finally:
        conn.close()


def authenticate_user(email, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, full_name, email, password_hash FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    if not user:
        conn.close()
        return None

    is_valid, upgraded_hash = verify_password(password, user["password_hash"])
    if not is_valid:
        conn.close()
        return None

    if upgraded_hash:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (upgraded_hash, user["id"]),
        )
        conn.commit()

    conn.close()
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
    }


def save_history_entry(user_id, entry_type, title, payload):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO history (user_id, entry_type, title, payload) VALUES (?, ?, ?, ?)",
        (user_id, entry_type, title, json.dumps(payload)),
    )
    conn.commit()
    conn.close()


def get_user_history(user_id, limit=8):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, entry_type, title, payload, created_at
        FROM history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def summarize_history_payload(payload):
    data = json.loads(payload)
    student = data.get("student", {})
    role = student.get("role", "")
    skills = student.get("skills", [])
    score = data.get("match_percentage", 0)

    summary_parts = []
    if role:
        summary_parts.append(f"Role: {role.title()}")
    if skills:
        summary_parts.append(f"Skills: {len(skills)} tracked")
    if score:
        summary_parts.append(f"Match: {score}%")

    return " • ".join(summary_parts) if summary_parts else "Saved project activity snapshot"


def load_history_snapshot(payload):
    data = json.loads(payload)
    st.session_state.student = data.get("student", st.session_state.student)
    st.session_state.resume_analysis = data.get("resume_analysis", "")
    st.session_state.resume_text = data.get("resume_text", "")
    st.session_state.roadmap = data.get("roadmap", "")
    st.session_state.matched_skills = data.get("matched_skills", [])
    st.session_state.missing_skills = data.get("missing_skills", [])
    st.session_state.match_percentage = data.get("match_percentage", 0)
    st.session_state.role_description = data.get("role_description", "")
    st.session_state.interview_questions = data.get("interview_questions", "")
    st.session_state.interview_feedback = data.get("interview_feedback", "")
    st.session_state.course_recommendations = data.get("course_recommendations", "")
    st.session_state.resume_rewrite = data.get("resume_rewrite", "")


def current_snapshot():
    return {
        "student": st.session_state.student,
        "resume_analysis": st.session_state.resume_analysis,
        "resume_text": st.session_state.resume_text,
        "roadmap": st.session_state.roadmap,
        "matched_skills": st.session_state.matched_skills,
        "missing_skills": st.session_state.missing_skills,
        "match_percentage": st.session_state.match_percentage,
        "role_description": st.session_state.role_description,
        "interview_questions": st.session_state.interview_questions,
        "interview_feedback": st.session_state.interview_feedback,
        "course_recommendations": st.session_state.course_recommendations,
        "resume_rewrite": st.session_state.resume_rewrite,
    }


def get_groq_client():
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except StreamlitSecretNotFoundError:
        api_key = None

    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error(
            "Groq API key not found. Add `GROQ_API_KEY` to a `.env` file or Streamlit secrets."
        )
        st.stop()
    return Groq(api_key=api_key)


def initialize_session():
    defaults = {
        "student": {
            "name": "",
            "degree": "",
            "year": "",
            "time": 10,
            "skills": [],
            "role": "",
        },
        "resume_analysis": "",
        "resume_text": "",
        "roadmap": "",
        "matched_skills": [],
        "missing_skills": [],
        "match_percentage": 0,
        "role_description": "",
        "interview_questions": "",
        "interview_feedback": "",
        "course_recommendations": "",
        "resume_rewrite": "",
        "current_user": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def generate_ai_roadmap(client, current_role, skills, target_role, time_commitment):
    prompt = ROADMAP_PROMPT_MARKDOWN.format(
        current_role=current_role,
        skills=", ".join(skills),
        target_role=target_role,
        time_commitment=time_commitment,
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def extract_resume_text(file):
    text = ""

    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif (
        file.type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        doc_file = docx.Document(file)
        for para in doc_file.paragraphs:
            text += para.text + "\n"

    return text


def analyze_resume_ats(client, resume_text, role):
    prompt = ATS_PROMPT.format(role=role, resume_text=resume_text[:6000])
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def extract_skills_with_ai(client, text):
    prompt = f"""
    Extract technical skills only as a comma separated list.
    Keep the skills short and normalized.

    Text:
    {text}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )

    return [
        skill.strip().lower().replace(".", "").replace("-", " ")
        for skill in response.choices[0].message.content.split(",")
        if len(skill.strip()) > 1
    ]


def generate_interview_questions(client, student):
    prompt = INTERVIEW_PROMPT.format(
        target_role=student["role"].title(),
        skills=", ".join(student["skills"]) if student["skills"] else "No skills provided",
        background=student["degree"] or student["year"] or "Learner",
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def extract_question_list(markdown_text):
    questions = []
    if not markdown_text:
        return questions

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        candidate = None
        if line.startswith(("- ", "* ")):
            candidate = line[2:].strip()
        elif len(line) > 3 and line[0].isdigit() and ". " in line[:5]:
            candidate = line.split(". ", 1)[1].strip()

        if candidate and len(candidate) > 10 and "tip" not in candidate.lower():
            questions.append(candidate)

    seen = set()
    unique_questions = []
    for question in questions:
        if question not in seen:
            seen.add(question)
            unique_questions.append(question)
    return unique_questions


def evaluate_interview_answer(client, student, question, answer):
    prompt = INTERVIEW_EVAL_PROMPT.format(
        target_role=student["role"].title(),
        skills=", ".join(student["skills"]) if student["skills"] else "No skills provided",
        question=question,
        answer=answer,
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_course_recommendations(client, student, missing_skills):
    prompt = COURSE_PROMPT.format(
        target_role=student["role"].title(),
        skills=", ".join(student["skills"]) if student["skills"] else "No skills provided",
        missing_skills=", ".join(missing_skills) if missing_skills else "No major missing skills",
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_resume_rewrite(client, resume_text, role):
    prompt = RESUME_REWRITE_PROMPT.format(
        role=role,
        resume_text=resume_text[:6000],
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def compute_role_match(student, df):
    rows = df[df["label"].str.lower() == student["role"]]
    required = []

    for skills in rows["skills"]:
        required.extend([item.strip().lower() for item in skills.replace(";", ",").split(",")])

    required = sorted(set(filter(None, required)))
    matched = []
    missing = []

    for req in required:
        if any(req in skill or skill in req for skill in student["skills"]):
            matched.append(req)
        else:
            missing.append(req)

    matched = sorted(set(matched))
    missing = sorted(set(missing))
    match_percentage = int((len(matched) / len(required)) * 100) if required else 0
    description = rows["description"].iloc[0] if not rows.empty else ""

    return description, matched, missing, match_percentage


def get_custom_role_analysis(client, student):
    prompt = f"""
    You are a career advisor.

    A learner wants to prepare for this target role: {student["role"]}.
    Their current skills are: {", ".join(student["skills"]) if student["skills"] else "No skills provided"}.

    Return:
    1. A short role description in 2-3 sentences.
    2. A comma separated list of important skills for that role.

    Format exactly like this:
    DESCRIPTION: ...
    SKILLS: skill 1, skill 2, skill 3
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content

    description = ""
    required_skills = []

    for line in content.splitlines():
        if line.upper().startswith("DESCRIPTION:"):
            description = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SKILLS:"):
            required_skills = [
                item.strip().lower()
                for item in line.split(":", 1)[1].split(",")
                if item.strip()
            ]

    if not description:
        description = content.strip()

    return description, required_skills


def compute_custom_role_match(client, student):
    description, required = get_custom_role_analysis(client, student)
    matched = []
    missing = []

    for req in required:
        if any(req in skill or skill in req for skill in student["skills"]):
            matched.append(req)
        else:
            missing.append(req)

    matched = sorted(set(matched))
    missing = sorted(set(missing))
    match_percentage = int((len(matched) / len(required)) * 100) if required else 0

    return description, matched, missing, match_percentage


def build_pdf_bytes(student, role, desc, matched, missing, roadmap):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("Career Compass AI Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Name: {student['name']}", styles["Normal"]),
        Paragraph(f"Target Role: {role}", styles["Normal"]),
        Paragraph(f"Degree: {student['degree']}", styles["Normal"]),
        Paragraph(f"Study Time Per Week: {student['time']} hours", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Role Description", styles["Heading2"]),
        Paragraph(desc or "No description available.", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Matched Skills", styles["Heading2"]),
        Paragraph(", ".join(matched) if matched else "No matched skills yet.", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Missing Skills", styles["Heading2"]),
        Paragraph(", ".join(missing) if missing else "No missing skills.", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Career Roadmap", styles["Heading2"]),
        Paragraph((roadmap or "Roadmap not generated.").replace("\n", "<br/>"), styles["Normal"]),
    ]
    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()


def render_chip_list(items, kind):
    if not items:
        st.write("No items to show yet.")
        return

    chips = "".join([f'<span class="chip {kind}">{item}</span>' for item in items])
    st.markdown(chips, unsafe_allow_html=True)


def render_stat_card(label, value, caption):
    st.markdown(
        f"""
        <div class="mini-stat">
            <div class="mini-stat-label">{label}</div>
            <div class="mini-stat-value">{value}</div>
            <div>{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_badge(number, label):
    st.markdown(
        f"""
        <div class="step-badge">
            <span class="step-number">{number}</span>
            <span class="step-label">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_markdown_response(text):
    if not text:
        return text

    return text.replace("```markdown", "").replace("```md", "").replace("```", "").strip()


def render_dashboard_history_card(item):
    pretty_type = item["entry_type"].replace("-", " ").title()
    preview = summarize_history_payload(item["payload"])
    st.markdown(
        f"""
        <div class="dashboard-history-card">
            <div class="dashboard-history-type">{pretty_type}</div>
            <div class="dashboard-history-title">{item["title"]}</div>
            <div class="dashboard-history-date">{item["created_at"]}</div>
            <div class="dashboard-history-preview">{preview}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_screen():
    st.markdown(
        """
        <div class="hero-card">
            <h1>Career Compass AI</h1>
            <p>
                Create an account to save your career reports, ATS analysis, and interview prep history.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["Login", "Create Account"])

    with login_tab:
        st.subheader("Welcome back")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state.current_user = user
                st.success(f"Welcome back, {user['full_name']}.")
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with signup_tab:
        st.subheader("Create your account")
        with st.form("signup_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
        if submitted:
            if not full_name.strip() or not email.strip() or not password.strip():
                st.warning("Please complete all fields.")
            elif password != confirm_password:
                st.warning("Passwords do not match.")
            elif len(password) < 8:
                st.warning("Password should be at least 8 characters.")
            elif password.lower() == password or password.upper() == password:
                st.warning("Use a mix of uppercase and lowercase letters in the password.")
            elif not any(char.isdigit() for char in password):
                st.warning("Include at least one number in the password.")
            else:
                user, error = create_user(full_name, email, password)
                if error:
                    st.error(error)
                else:
                    st.session_state.current_user = user
                    st.success("Account created successfully.")
                    st.rerun()


def main():
    inject_custom_css()
    initialize_session()
    init_db()
    df = load_data()
    if not st.session_state.current_user:
        render_auth_screen()
        return
    client = get_groq_client()
    student = st.session_state.student
    current_user = st.session_state.current_user

    st.markdown(
        """
        <div class="hero-card">
            <h1>Career Compass AI</h1>
            <p>
                Plan your next role, measure your skills, improve your resume, and generate
                a focused learning roadmap from one friendly dashboard.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(f"### Hi, {current_user['full_name'].split()[0]}")
        st.caption(current_user["email"])
        if st.button("Logout", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

        st.markdown("### Your Progress")
        completed = sum(
            [
                bool(student["name"]),
                bool(student["skills"]),
                bool(student["role"]),
                bool(st.session_state.resume_analysis),
                bool(st.session_state.roadmap),
            ]
        )
        st.progress(completed / 5)
        st.caption(f"{completed} of 5 key steps completed")
        st.markdown(
            """
            <div class="sidebar-note">
                Fill in your profile, extract skills, choose a target role, check your resume,
                and then generate your personalized roadmap.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Saved History")
        history_items = get_user_history(current_user["id"])
        if not history_items:
            st.caption("Your saved reports and analyses will appear here.")
        else:
            for item in history_items:
                pretty_type = item["entry_type"].replace("-", " ").title()
                st.markdown(
                    f"""
                    <div class="history-card">
                        <div class="history-type">{pretty_type}</div>
                        <div class="history-title">{item["title"]}</div>
                        <div class="history-date">{item["created_at"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Load", key=f"load-history-{item['id']}", use_container_width=True):
                    load_history_snapshot(item["payload"])
                    st.success("Saved history loaded into the workspace.")
                    st.rerun()

    top_col1, top_col2, top_col3 = st.columns(3)
    with top_col1:
        render_stat_card("Career Tracks", df["label"].nunique(), "Roles you can explore")
    with top_col2:
        render_stat_card(
            "Current Skills",
            len(student["skills"]),
            "Skills extracted from your input",
        )
    with top_col3:
        render_stat_card(
            "Skill Match",
            f"{st.session_state.match_percentage}%",
            "Fit for your chosen role",
        )

    feature_col1, feature_col2, feature_col3 = st.columns(3)
    with feature_col1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-kicker">Discover</div>
                <div class="feature-title">Map skills to real career tracks</div>
                <div class="feature-copy">
                    Turn basic experience, coursework, and project work into a clearer picture
                    of which roles fit you now and what to build next.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with feature_col2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-kicker">Improve</div>
                <div class="feature-title">Strengthen your resume with ATS feedback</div>
                <div class="feature-copy">
                    Upload a PDF or DOCX resume and get focused feedback on keywords,
                    strengths, missing areas, and practical improvements.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with feature_col3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-kicker">Grow</div>
                <div class="feature-title">Follow a guided learning roadmap</div>
                <div class="feature-copy">
                    Get personalized next steps covering missing skills, projects,
                    certifications, and interview preparation in one plan.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    dashboard_tab, overview_tab, skills_tab, resume_tab, results_tab, interview_tab = st.tabs(
        ["My Dashboard", "Profile Setup", "Skills & Role", "Resume Review", "Results", "Interview Prep"]
    )

    with dashboard_tab:
        render_step_badge("0", "Dashboard")
        st.subheader("Your saved progress at a glance")
        st.write("Review recent activity, reload previous work, and keep your career planning in one place.")

        history_items = get_user_history(current_user["id"], limit=12)
        dash_col1, dash_col2, dash_col3 = st.columns(3)
        with dash_col1:
            render_stat_card("Saved Entries", len(history_items), "Recent actions stored")
        with dash_col2:
            render_stat_card("Current Role", student["role"].title() if student["role"] else "Not set", "Latest selected path")
        with dash_col3:
            render_stat_card("Interview Prep", "Ready" if st.session_state.interview_questions else "Pending", "Question set status")

        if not history_items:
            st.info("No saved activity yet. Start by filling your profile or generating a report.")
        else:
            card_cols = st.columns(2)
            for index, item in enumerate(history_items):
                with card_cols[index % 2]:
                    render_dashboard_history_card(item)
                    if st.button("Open This Snapshot", key=f"open-dashboard-history-{item['id']}", use_container_width=True):
                        load_history_snapshot(item["payload"])
                        st.success("Snapshot loaded successfully.")
                        st.rerun()

    with overview_tab:
        render_step_badge("1", "Profile Setup")
        st.subheader("Build your learner profile")
        st.write("Start with a few details so the recommendations feel more personal.")

        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name", value=student["name"])
                degree = st.text_input("Degree or Background", value=student["degree"])
            with col2:
                year = st.text_input("Year / Experience Level", value=student["year"])
                time = st.slider(
                    "Hours per week you can invest",
                    min_value=1,
                    max_value=40,
                    value=int(student["time"]),
                )

            submitted = st.form_submit_button("Save Profile", use_container_width=True)

        if submitted:
            st.session_state.student.update(
                {"name": name, "degree": degree, "year": year, "time": time}
            )
            save_history_entry(
                current_user["id"],
                "profile",
                f"Profile updated for {name or 'learner'}",
                current_snapshot(),
            )
            st.success("Profile saved. You can move to the next tab.")

    with skills_tab:
        render_step_badge("2", "Skills and Role")
        left, right = st.columns([1.2, 1])

        with left:
            st.subheader("Extract your skills")
            skill_text = st.text_area(
                "Describe your skills, coursework, tools, internships, or projects",
                height=220,
                placeholder="Example: Built a Python data dashboard, used SQL for analytics, created APIs with Flask...",
            )

            if st.button("Extract Skills with AI", use_container_width=True):
                if not skill_text.strip():
                    st.warning("Please add some background before extracting skills.")
                else:
                    with st.spinner("Finding your strongest technical skills..."):
                        st.session_state.student["skills"] = extract_skills_with_ai(client, skill_text)
                    st.success("Skills extracted successfully.")

            st.markdown("#### Current skill list")
            render_chip_list(student["skills"], "good")

        with right:
            st.subheader("Choose a target role")
            role_options = sorted(df["label"].unique())
            role_mode = st.radio(
                "How do you want to choose your role?",
                ["Choose from dataset", "Type my own role"],
                horizontal=True,
            )

            selected_role = None
            custom_role = ""

            if role_mode == "Choose from dataset":
                selected_role = st.selectbox(
                    "Career path",
                    role_options,
                    index=(
                        role_options.index(student["role"].title())
                        if student["role"] and student["role"].title() in role_options
                        else 0
                    ),
                )
            else:
                custom_role = st.text_input(
                    "Enter your target role",
                    value=student["role"].title() if student["role"] else "",
                    placeholder="Example: AI Engineer, Cybersecurity Analyst, UI/UX Designer",
                )

            if st.button("Save Target Role", use_container_width=True):
                final_role = selected_role if role_mode == "Choose from dataset" else custom_role
                if not final_role or not final_role.strip():
                    st.warning("Please choose or enter a target role.")
                else:
                    st.session_state.student["role"] = final_role.strip().lower()
                    save_history_entry(
                        current_user["id"],
                        "role",
                        f"Target role set to {final_role.strip()}",
                        current_snapshot(),
                    )
                    st.success(f"Target role set to {final_role.strip()}.")

            if st.session_state.student["role"]:
                role_rows = df[
                    df["label"].str.lower() == st.session_state.student["role"]
                ]
                if not role_rows.empty:
                    st.markdown("#### Role snapshot")
                    st.write(role_rows["description"].iloc[0])
                else:
                    st.markdown("#### Custom role")
                    st.write(
                        "This role is not in the dataset, but you can still use it for ATS analysis and roadmap generation."
                    )

    with resume_tab:
        render_step_badge("3", "Resume Review")
        st.subheader("Check your resume against ATS expectations")
        uploaded_file = st.file_uploader("Upload a PDF or DOCX resume", type=["pdf", "docx"])

        if not st.session_state.student["role"]:
            st.info("Choose your target role first so the resume review has context.")
        elif uploaded_file:
            with st.spinner("Reading your resume..."):
                resume_text = extract_resume_text(uploaded_file)
                st.session_state.resume_text = resume_text

            if len(resume_text.strip()) < 100:
                st.error("I could not extract enough text from that file. Try another resume version.")
            else:
                st.success("Resume text extracted successfully.")
                if st.button("Run ATS Analysis", use_container_width=True):
                    with st.spinner("Scoring your resume and checking keyword fit..."):
                        st.session_state.resume_analysis = analyze_resume_ats(
                            client,
                            resume_text,
                            st.session_state.student["role"].title(),
                        )
                    save_history_entry(
                        current_user["id"],
                        "ats",
                        f"ATS analysis for {st.session_state.student['role'].title()}",
                        current_snapshot(),
                    )

        if st.session_state.resume_analysis:
            st.markdown("#### ATS feedback")
            st.markdown(clean_markdown_response(st.session_state.resume_analysis))

            st.markdown("#### Resume rewrite suggestions")
            if st.button("Generate Resume Rewrite Suggestions", use_container_width=True):
                if not st.session_state.resume_text.strip():
                    st.warning("Please upload a resume first.")
                else:
                    with st.spinner("Rewriting your resume content for stronger impact..."):
                        st.session_state.resume_rewrite = generate_resume_rewrite(
                            client,
                            st.session_state.resume_text,
                            st.session_state.student["role"].title(),
                        )
                    save_history_entry(
                        current_user["id"],
                        "resume-rewrite",
                        f"Resume rewrite for {st.session_state.student['role'].title()}",
                        current_snapshot(),
                    )

            if st.session_state.resume_rewrite:
                st.markdown(clean_markdown_response(st.session_state.resume_rewrite))

    with results_tab:
        render_step_badge("4", "Results")
        st.subheader("See your recommendation and next steps")

        ready = (
            bool(student["name"])
            and bool(student["skills"])
            and bool(student["role"])
            and bool(student["time"])
        )

        if not ready:
            st.info("Complete your profile, add skills, and select a role to unlock recommendations.")
        else:
            if st.button("Generate Career Report", type="primary", use_container_width=True):
                with st.spinner("Comparing your profile with role requirements..."):
                    role_exists = any(
                        df["label"].str.lower() == student["role"]
                    )
                    if role_exists:
                        (
                            st.session_state.role_description,
                            st.session_state.matched_skills,
                            st.session_state.missing_skills,
                            st.session_state.match_percentage,
                        ) = compute_role_match(student, df)
                    else:
                        (
                            st.session_state.role_description,
                            st.session_state.matched_skills,
                            st.session_state.missing_skills,
                            st.session_state.match_percentage,
                        ) = compute_custom_role_match(client, student)

                with st.spinner("Creating your personalized AI roadmap..."):
                    st.session_state.roadmap = generate_ai_roadmap(
                        client,
                        student["degree"] or "Learner",
                        student["skills"],
                        student["role"].title(),
                        student["time"],
                    )
                save_history_entry(
                    current_user["id"],
                    "report",
                    f"Career report for {student['role'].title()}",
                    current_snapshot(),
                )

            if st.session_state.role_description:
                st.markdown(f"### {student['role'].title()}")
                st.write(st.session_state.role_description)
                st.metric("Skill Match Score", f"{st.session_state.match_percentage}%")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("#### Matched skills")
                    render_chip_list(st.session_state.matched_skills, "good")
                with col_b:
                    st.markdown("#### Missing skills")
                    render_chip_list(st.session_state.missing_skills, "warn")

            if st.session_state.roadmap:
                st.markdown("#### Personalized roadmap")
                st.markdown(st.session_state.roadmap, unsafe_allow_html=True)

                st.markdown("#### Course and learning recommendations")
                if st.button("Generate Course Recommendations", use_container_width=True):
                    with st.spinner("Finding the best learning path for your missing skills..."):
                        st.session_state.course_recommendations = generate_course_recommendations(
                            client,
                            student,
                            st.session_state.missing_skills,
                        )
                    save_history_entry(
                        current_user["id"],
                        "courses",
                        f"Learning plan for {student['role'].title()}",
                        current_snapshot(),
                    )

                if st.session_state.course_recommendations:
                    st.markdown(
                        clean_markdown_response(st.session_state.course_recommendations)
                    )

                pdf_bytes = build_pdf_bytes(
                    student,
                    student["role"].title(),
                    st.session_state.role_description,
                    st.session_state.matched_skills,
                    st.session_state.missing_skills,
                    st.session_state.roadmap,
                )
                st.download_button(
                    "Download PDF Report",
                    data=pdf_bytes,
                    file_name="career_compass_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    with interview_tab:
        render_step_badge("5", "Interview Prep")
        st.subheader("Practice interview questions for your target role")
        st.write(
            "Generate technical, scenario-based, and HR questions tailored to your chosen role and current skills."
        )

        role_ready = bool(student["role"])

        if not role_ready:
            st.info("Choose a target role first to generate interview questions.")
        else:
            prep_col1, prep_col2, prep_col3 = st.columns(3)
            with prep_col1:
                render_stat_card("Target Role", student["role"].title(), "Role used for practice")
            with prep_col2:
                render_stat_card("Skill Count", len(student["skills"]), "Current extracted skills")
            with prep_col3:
                render_stat_card(
                    "Readiness",
                    "Good to start" if student["skills"] else "Basic mode",
                    "Questions work even with few skills",
                )

            if st.button("Generate Interview Questions", use_container_width=True):
                with st.spinner("Preparing your interview practice set..."):
                    st.session_state.interview_questions = generate_interview_questions(
                        client, student
                    )
                save_history_entry(
                    current_user["id"],
                    "interview",
                    f"Interview prep for {student['role'].title()}",
                    current_snapshot(),
                )

            if st.session_state.interview_questions:
                st.markdown("#### Personalized interview set")
                st.markdown(clean_markdown_response(st.session_state.interview_questions))

                st.markdown("#### Practice your answer")
                extracted_questions = extract_question_list(
                    clean_markdown_response(st.session_state.interview_questions)
                )

                if extracted_questions:
                    selected_question = st.selectbox(
                        "Choose a question to answer",
                        extracted_questions,
                    )
                else:
                    selected_question = st.text_input(
                        "Enter the interview question",
                        placeholder="Paste or type a question here",
                    )

                answer_text = st.text_area(
                    "Write your answer",
                    height=180,
                    placeholder="Type your interview answer here...",
                )

                if st.button("Evaluate My Answer", use_container_width=True):
                    if not selected_question or not str(selected_question).strip():
                        st.warning("Please choose or enter a question first.")
                    elif not answer_text.strip():
                        st.warning("Please write your answer before evaluation.")
                    else:
                        with st.spinner("Reviewing your answer like an interviewer..."):
                            st.session_state.interview_feedback = evaluate_interview_answer(
                                client,
                                student,
                                str(selected_question).strip(),
                                answer_text.strip(),
                            )
                        save_history_entry(
                            current_user["id"],
                            "interview-feedback",
                            f"Interview answer review for {student['role'].title()}",
                            current_snapshot(),
                        )

                if st.session_state.interview_feedback:
                    st.markdown("#### Interview feedback")
                    st.markdown(
                        clean_markdown_response(st.session_state.interview_feedback)
                    )

    st.markdown(
        """
        <div class="footer-card">
            <strong>Career Compass AI</strong><br/>
            A student-friendly career planning workspace for exploring roles, improving resumes,
            and turning skill gaps into an action plan.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
