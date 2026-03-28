import os
from io import BytesIO

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
    page_title="Career Compass AI",
    page_icon="🎯",
    layout="wide",
)


DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "data.csv")

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
        "roadmap": "",
        "matched_skills": [],
        "missing_skills": [],
        "match_percentage": 0,
        "role_description": "",
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


def main():
    inject_custom_css()
    initialize_session()
    df = load_data()
    client = get_groq_client()
    student = st.session_state.student

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

    overview_tab, skills_tab, resume_tab, results_tab = st.tabs(
        ["Profile Setup", "Skills & Role", "Resume Review", "Results"]
    )

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

        if st.session_state.resume_analysis:
            st.markdown("#### ATS feedback")
            st.markdown(clean_markdown_response(st.session_state.resume_analysis))

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
