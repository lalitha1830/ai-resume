# 🍃 ResumeAI — AI-Powered Resume Analyzer

> Upload your resume. Paste a job description. Get instant, personalized AI insights.

![ResumeAI Dashboard](docs/screenshots/dashboard.png)
*Add your own screenshots to `docs/screenshots/` after running the app.*

---

## 📌 Overview

**ResumeAI** is a full-stack web application that uses Google Gemini to analyze your resume against a job description. It gives you:

- An **estimated match score** (0–100%) with a transparent calculation method
- A list of **matching skills** clearly demonstrated in your resume
- A list of **potentially missing skills** mentioned in the job posting
- **Resume strengths** and **areas for improvement**
- **Keyword analysis** and actionable **next steps**

Built with Python, Flask, SQLAlchemy, and the Google Gemini API. No JavaScript frameworks. No React. Just clean HTML, CSS, and server-side Python.

---

## 🎯 Problem Statement

Job seekers often don't know why their resume isn't getting responses. They spend hours guessing what to improve. ResumeAI gives you a clear, AI-powered comparison between your actual resume and a specific job description — so you know exactly what to improve.

---

## ✨ Main Features

| Feature | Description |
|---|---|
| 🔐 User accounts | Register, sign in, and sign out securely |
| 📄 Resume upload | PDF and DOCX, up to 5 MB |
| 🤖 AI analysis | Google Gemini analyses resume vs. job description |
| 📊 Match score | Transparent weighted calculation (not a random number) |
| ✅ Matching skills | Skills clearly demonstrated in your resume |
| ❌ Missing skills | Skills in the job description not found in your resume |
| 💪 Strengths | Positive findings from the analysis |
| 🔧 Improvements | Specific, actionable recommendations |
| 🔑 Keyword analysis | Important keywords present and missing |
| 📋 History | View and delete all your previous analyses |
| 👤 Profile | See your account information |

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3 |
| Database ORM | Flask-SQLAlchemy |
| Authentication | Flask-Login, Werkzeug |
| CSRF protection | Flask-WTF |
| Database | SQLite (local) |
| AI | Google Gemini via `google-genai` SDK |
| PDF parsing | PyMuPDF (`fitz`) |
| DOCX parsing | python-docx |
| Frontend | HTML5, CSS3, Jinja2 (no JavaScript frameworks) |
| Testing | pytest, pytest-flask |
| Config | python-dotenv |

---

## 🏗 Application Architecture

```
Browser (HTML forms)
       │
       ▼
Flask Routes (routes/)          ← handle HTTP requests
       │
       ├─► Auth routes          ← register, login, logout
       ├─► Main routes          ← landing, dashboard, history, profile
       └─► Analysis routes      ← form, results, delete
                │
                ├─► resume_parser.py    ← extract text from PDF/DOCX
                ├─► resume_analyzer.py  ← call Gemini API, parse JSON
                └─► scoring.py         ← calculate weighted match score
                         │
                         ▼
                   SQLite database      ← store users and analyses
                   (instance/resumeai.db)
```

---

## 📁 Project Structure

```
ai-resume-analyzer/
│
├── app.py                  ← Flask application factory + entry point
├── config.py               ← Configuration for dev/prod/test
├── extensions.py           ← Shared extension instances (db, login, csrf)
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
├── .gitignore
├── README.md
│
├── models/
│   ├── __init__.py
│   └── user.py             ← User and Analysis database models
│
├── routes/
│   ├── __init__.py
│   ├── auth.py             ← /register /login /logout
│   ├── main.py             ← / /dashboard /history /profile
│   └── analysis.py         ← /analyze /analysis/<id> /delete
│
├── services/
│   ├── __init__.py
│   ├── resume_parser.py    ← PDF and DOCX text extraction
│   ├── resume_analyzer.py  ← Gemini API integration
│   └── scoring.py          ← Weighted match score calculation
│
├── templates/
│   ├── base.html
│   ├── index.html          ← Public landing page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── analyze.html
│   ├── results.html
│   ├── history.html
│   ├── profile.html
│   ├── delete_confirmation.html
│   └── errors/
│       ├── 403.html
│       ├── 404.html
│       └── 500.html
│
├── static/
│   └── css/
│       └── style.css       ← All styles — pastel design system
│
├── tests/
│   ├── conftest.py         ← Shared test fixtures
│   ├── test_auth.py        ← Authentication tests
│   ├── test_resume_parser.py
│   ├── test_analysis.py    ← AI analysis and scoring tests
│   └── test_routes.py      ← Route integration tests
│
└── instance/
    └── resumeai.db         ← Created automatically (excluded from Git)
```

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.10 or newer** — [Download here](https://www.python.org/downloads/)
- **A Google Gemini API key** — Free tier available at [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Git** (optional, for cloning)

---

### Step 1 — Get the code

```bash
# If you have Git:
git clone https://github.com/lalitha1830/ai-resume.git
cd ai-resume
```

---

### Step 2 — Create a virtual environment

A virtual environment keeps this project's packages separate from other Python projects.

**Windows (Command Prompt or PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt. This means the virtual environment is active.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, the Gemini SDK, PyMuPDF, and all other required packages.

---

### Step 4 — Configure environment variables

Copy the example file and fill in your real values:

**Windows:**
```powershell
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Now open `.env` in a text editor and set these values:

```
# Generate a strong secret key with this command:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=paste_your_generated_key_here

# Get your free API key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here

# Check supported models at https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL=gemini-2.0-flash

FLASK_ENV=development
FLASK_DEBUG=True
```

> ⚠️ **Never commit your `.env` file to Git.** It is already listed in `.gitignore`.

#### How to get a free Gemini API key:
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key and paste it into your `.env` file as `GEMINI_API_KEY`

---

### Step 5 — Initialize the database

The database is created automatically when you run the app for the first time. No manual setup needed.

```bash
python app.py
```

The `instance/resumeai.db` file will be created automatically.

---

### Step 6 — Run the application

```bash
python app.py
```

Open your browser and visit: **http://127.0.0.1:5000**

You should see the ResumeAI landing page.

---

## 🧪 Running Tests

Make sure the virtual environment is active, then:

```bash
pytest tests/ -v
```

To run a specific test file:
```bash
pytest tests/test_auth.py -v
pytest tests/test_resume_parser.py -v
pytest tests/test_analysis.py -v
pytest tests/test_routes.py -v
```

Tests use an **in-memory SQLite database** and **mock the Gemini API** — no real API key needed to run tests.

---

## 📖 How to Use ResumeAI

1. **Visit** `http://127.0.0.1:5000` and click **Sign Up**
2. **Create an account** with your name, email, and a password (min. 12 characters)
3. **Sign in** with your credentials
4. Click **New Analysis** or **Start New Analysis**
5. Optionally enter an **analysis label** (e.g. "Google SWE role") and **job title**
6. **Upload your resume** as PDF or DOCX (max 5 MB)
7. **Paste the full job description** into the text area
8. Click **Analyze My Resume**
9. Wait 10–30 seconds while Gemini processes your documents
10. **Review your results**: match score, skills, strengths, recommendations
11. All results are saved in **History** for future reference
12. Use **Delete** to remove any analysis you no longer need

---

## 🔒 Security & Privacy Notes

- Passwords are **hashed** using Werkzeug's `generate_password_hash` (scrypt/pbkdf2)
- Uploaded resume files are **read into memory only** — not written to disk
- Only the **analysis results** (not the resume content) are stored in the database
- All forms are protected against **CSRF attacks** using Flask-WTF tokens
- Each user can only access **their own** analyses (ownership verified on every request)
- API keys and secrets are loaded from **environment variables**, never hardcoded
- Error messages are **generic** to prevent user enumeration attacks

---

## ⚠️ Current Limitations

- **Image-only PDFs**: If your PDF was created by scanning a paper document, text cannot be extracted. Use a PDF with machine-readable text or convert to DOCX.
- **No password reset**: Forgot-password flow is not yet implemented.
- **No email verification**: Accounts are created without email confirmation.
- **Rate limits**: If you hit Gemini API rate limits, wait a minute and try again.
- **SQLite only**: The app uses SQLite for simplicity. For production use, switch to PostgreSQL.
- **No file storage**: Resume files are not stored — if you want to re-analyze, re-upload.
- **Score is approximate**: The match score is an AI estimate, not an official ATS score.

---

## 🔮 Future Improvements

- [ ] Password reset via email
- [ ] Email verification on signup
- [ ] Resume re-analysis without re-uploading
- [ ] OCR support for scanned PDFs
- [ ] Export results as PDF
- [ ] Multiple resume versions per user
- [ ] Side-by-side comparison of two analyses
- [ ] PostgreSQL support for production deployment
- [ ] Docker containerisation

---

## 📊 Match Score Methodology

The match score is **not** a random number generated by the AI. Here's how it works:

1. Gemini analyses the resume against the job description and returns **component scores** (0–10 scale) for:
   - **Skills** — how many required skills are clearly demonstrated
   - **Experience** — how well the experience matches job responsibilities
   - **Qualifications** — how well education/certs match requirements

2. These are converted to a percentage using **configurable weights**:
   - Skills: **50%**
   - Experience: **30%**
   - Qualifications: **20%**

3. Formula: `(skills/10 × 50) + (experience/10 × 30) + (qualifications/10 × 20)`

4. The result is clamped to **0–100**.

> This score is an approximate comparison. It is **not** an official ATS score and **not** a prediction of hiring success.

---

## 🤝 Contributing

This is a portfolio project. Feel free to fork and extend it. If you find a bug, open an issue.

---

## 📄 License

MIT License — free for personal and educational use.

---

*Built with ❤️ using Python, Flask, and Google Gemini.*
