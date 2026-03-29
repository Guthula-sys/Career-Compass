# Career Recommendation System alias Career Compass AI

Career Compass AI is a Streamlit-based career guidance website that helps learners assess their skills, review resumes, explore target roles, and generate personalized roadmaps.

## What changed

- Website-style dashboard with a cleaner and more user-friendly interface
- Profile setup, skill extraction, resume review, and results organized into tabs
- Progress tracking in the sidebar
- Improved PDF export flow
- Safer API key loading from `.env` or Streamlit secrets instead of hardcoding credentials

## Features

- Learner profile setup
- AI-powered skill extraction
- Career role selection and skill match scoring
- Resume ATS analysis for PDF and DOCX files
- Personalized AI roadmap generation
- Downloadable PDF career report

## Installation

```bash
pip install -r requirements.txt
```

## Configure API Key

1. Copy `.env.example` to `.env`
2. Add your Groq API key:

```env
GROQ_API_KEY=your_actual_key_here
```

You can also store the same value in Streamlit secrets.

## Run the website

```bash
streamlit run app.py
```

## Deploy To A Public Link

The easiest way to get a public website link is Streamlit Community Cloud.

### Before you deploy

1. Make sure these files are in your GitHub repo:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `data/data.csv`
2. Do not upload your real `.env` file.
3. Keep your Groq API key ready so you can add it as a secret during deployment.

### Deployment steps

1. Create a GitHub repository and push this project.
2. Go to `https://share.streamlit.io/`
3. Sign in with GitHub.
4. Click `Create app`
5. Select your repository, branch, and `app.py`
6. Open `Advanced settings`
7. Add this secret:

```toml
GROQ_API_KEY="your_actual_groq_api_key_here"
```

8. Click `Deploy`

After deployment, Streamlit will generate a public link like:

```text
https://your-app-name.streamlit.app
```

### If you update the code later

Push changes to GitHub again and Streamlit Community Cloud will redeploy the app.

## Tech Stack

- Python
- Streamlit
- Pandas
- Groq API
- PyPDF2
- python-docx
- ReportLab
- python-dotenv
