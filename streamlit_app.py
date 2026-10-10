import streamlit as st
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import get_user_by_username_or_email, init_db

# Ensure database tables exist
init_db()

# 1. Page Configuration
st.set_page_config(
    page_title="AI Resume Matcher",
    page_icon="⚡",
    layout="wide"
)

# 2. Custom CSS Styling
st.markdown("""
    <style>
    .main {
        background-color: #F9FAFB;
    }
    .score-badge {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 140px;
        height: 140px;
        border-radius: 50%;
        background: #EEF2FF;
        border: 4px solid #4F46E5;
        margin: 20px auto;
    }
    .score-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4F46E5;
    }
    .score-label {
        font-size: 0.75rem;
        color: #6B7280;
        text-transform: uppercase;
        font-weight: 600;
    }
    div.stButton > button {
        background-color: #4F46E5;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 8px;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #4338CA;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Authentication Flow
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.full_name = ""

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; margin-top: 40px;'>⚡ AI Resume Matcher</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280; margin-bottom: 30px;'>Please sign in with your registered account</p>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        with st.container(border=True):
            st.subheader("Sign In")
            identifier_input = st.text_input("Username or Email", placeholder="Enter username or email")
            password_input = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.button("Sign In"):
                if not identifier_input or not password_input:
                    st.error("Please enter both username/email and password.")
                else:
                    user = get_user_by_username_or_email(identifier_input)
                    if user and user.check_password(password_input):
                        if not user.is_active:
                            st.error("This account has been deactivated.")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.username = user.username
                            st.session_state.full_name = user.full_name
                            st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your details and try again.")
    st.stop()

# User is authenticated: Show sidebar with profile info & logout
with st.sidebar:
    st.markdown(f"### 👤 Logged in as: **{st.session_state.full_name}** (`@{st.session_state.username}`)")
    if st.button("Sign Out"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.full_name = ""
        st.rerun()

# 4. Text Extraction Function
def extract_text(file):
    text = ""
    if file.name.endswith('.pdf'):
        reader = PdfReader(file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    else:
        text = file.read().decode("utf-8", errors="ignore")
    return text

# 5. Cosine Similarity Matching Engine
def calculate_match_score(resume_text, job_description):
    if not resume_text.strip() or not job_description.strip():
        return 0.0
    documents = [resume_text, job_description]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)
    match_percentage = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
    return round(match_percentage, 2)

# 6. User Interface Layout
st.markdown("<h2>⚡ AI Resume & Job Matching System</h2>", unsafe_allow_html=True)
st.write(" ")

col1, col2 = st.columns(2, gap="medium")

with col1:
    with st.container(border=True):
        st.subheader("1. Job Description")
        job_description = st.text_area(
            label="Job Description",
            placeholder="Paste target job requirements here...",
            height=220,
            label_visibility="collapsed"
        )

with col2:
    with st.container(border=True):
        st.subheader("2. Candidate Resume")
        uploaded_file = st.file_uploader(
            label="Upload Resume",
            type=["pdf", "txt"],
            label_visibility="collapsed"
        )
        if uploaded_file:
            st.success(f"Loaded: {uploaded_file.name}")

# 7. Matching Execution & Display
if st.button("Analyze Resume Compatibility"):
    if not job_description.strip():
        st.warning("Please paste a job description first.")
    elif not uploaded_file:
        st.warning("Please upload a resume file first.")
    else:
        with st.spinner("Analyzing compatibility..."):
            resume_text = extract_text(uploaded_file)
            score = calculate_match_score(resume_text, job_description)

            st.markdown("---")
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center;'>Match Analysis Result</h3>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="score-badge">
                        <span class="score-number">{score}%</span>
                        <span class="score-label">Match Score</span>
                    </div>
                """, unsafe_allow_html=True)
                st.progress(score / 100)