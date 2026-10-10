# AI Resume & Job Matching System 🎯⚡

An intelligent, explainable AI web platform that calculates compatibility between candidate resumes and job descriptions using Natural Language Processing (NLP) and the TF-IDF Vector Space Model.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask%203.0-lightgrey.svg)
![Scikit-Learn](https://img.shields.io/badge/Machine%20Learning-Scikit--Learn-orange.svg)
![Streamlit](https://img.shields.io/badge/Alternative%20UI-Streamlit-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

- **Explainable AI Compatibility Scoring**: Uses TF-IDF (Term Frequency-Inverse Document Frequency) and Cosine Similarity to compute a mathematical match score, accompanied by an in-depth **"Why This Score?"** breakdown.
- **Detailed Skill Gap Analysis**:
  - 🟢 **Matching Skills**: Technical and domain proficiencies present in both the resume and the job posting.
  - 🔴 **Missing Required Skills**: Key qualifications detected in the job description that were absent from the candidate's resume.
  - 🔵 **Additional Candidate Strengths**: Unique skills and strengths found in the resume.
- **Enterprise-Grade Security & Authentication**:
  - Secure password hashing using modern `scrypt`.
  - CSRF protection on all forms via Flask-WTF.
  - IP-based rate limiting to prevent brute-force attacks.
  - Secure session cookies and path traversal prevention on file uploads.
- **Persistent User History**: Keep track of previous resume evaluations, compare results across multiple job descriptions, and audit match records.
- **Dual Interface**:
  - Full-featured **Flask Web Portal** with dashboards, login, and registration.
  - Rapid, interactive **Streamlit Dashboard** for quick testing.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask 3.0, Flask-Login, Flask-WTF
- **Machine Learning & NLP**: Scikit-Learn, PyPDF
- **Database**: SQLite3 (with indexed relationships and migrations)
- **Production Server**: Waitress WSGI
- **Frontend**: HTML5, Vanilla CSS3 (modern glassmorphism design), JavaScript
- **Testing**: Pytest

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/AI_Resume_Job_Matching.git
cd AI_Resume_Job_Matching
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 5. Run the Application

#### Option A: Flask Web App (Recommended)
```bash
python wsgi.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

#### Option B: Streamlit Dashboard
```bash
streamlit run streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest
```

---

## 📄 License
This project is licensed under the MIT License.
