"""
AI Resume Matcher - Explainable Compatibility Analysis Engine
============================================================
Provides transparent, deterministic skill extraction, vocabulary analysis,
score calculation explanation, and actionable resume improvement recommendations.
"""

import re
from typing import Dict, List, Set, Tuple, Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================================
# Curated Skill Taxonomy & Canonical Normalization Dictionary
# ============================================================================

SKILL_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # Programming Languages
    "python": {"canonical": "Python", "category": "Programming Languages"},
    "javascript": {"canonical": "JavaScript", "category": "Programming Languages"},
    "typescript": {"canonical": "TypeScript", "category": "Programming Languages"},
    "java": {"canonical": "Java", "category": "Programming Languages"},
    "c++": {"canonical": "C++", "category": "Programming Languages"},
    "cpp": {"canonical": "C++", "category": "Programming Languages"},
    "c#": {"canonical": "C#", "category": "Programming Languages"},
    "csharp": {"canonical": "C#", "category": "Programming Languages"},
    "golang": {"canonical": "Go", "category": "Programming Languages"},
    "go": {"canonical": "Go", "category": "Programming Languages", "word_boundary": True},
    "rust": {"canonical": "Rust", "category": "Programming Languages"},
    "ruby": {"canonical": "Ruby", "category": "Programming Languages"},
    "php": {"canonical": "PHP", "category": "Programming Languages"},
    "swift": {"canonical": "Swift", "category": "Programming Languages"},
    "kotlin": {"canonical": "Kotlin", "category": "Programming Languages"},
    "scala": {"canonical": "Scala", "category": "Programming Languages"},
    "r": {"canonical": "R", "category": "Programming Languages", "exact_only": True},
    "matlab": {"canonical": "MATLAB", "category": "Programming Languages"},
    "sql": {"canonical": "SQL", "category": "Programming Languages"},
    "bash": {"canonical": "Bash", "category": "Programming Languages"},
    "shell": {"canonical": "Shell Scripting", "category": "Programming Languages"},
    "html": {"canonical": "HTML5", "category": "Web Technologies"},
    "html5": {"canonical": "HTML5", "category": "Web Technologies"},
    "css": {"canonical": "CSS3", "category": "Web Technologies"},
    "css3": {"canonical": "CSS3", "category": "Web Technologies"},
    "sass": {"canonical": "Sass/SCSS", "category": "Web Technologies"},

    # Frameworks & Libraries
    "react": {"canonical": "React", "category": "Frameworks & Libraries"},
    "reactjs": {"canonical": "React", "category": "Frameworks & Libraries"},
    "react.js": {"canonical": "React", "category": "Frameworks & Libraries"},
    "angular": {"canonical": "Angular", "category": "Frameworks & Libraries"},
    "angularjs": {"canonical": "Angular", "category": "Frameworks & Libraries"},
    "vue": {"canonical": "Vue.js", "category": "Frameworks & Libraries"},
    "vuejs": {"canonical": "Vue.js", "category": "Frameworks & Libraries"},
    "vue.js": {"canonical": "Vue.js", "category": "Frameworks & Libraries"},
    "next.js": {"canonical": "Next.js", "category": "Frameworks & Libraries"},
    "nextjs": {"canonical": "Next.js", "category": "Frameworks & Libraries"},
    "node.js": {"canonical": "Node.js", "category": "Frameworks & Libraries"},
    "nodejs": {"canonical": "Node.js", "category": "Frameworks & Libraries"},
    "express": {"canonical": "Express.js", "category": "Frameworks & Libraries"},
    "expressjs": {"canonical": "Express.js", "category": "Frameworks & Libraries"},
    "django": {"canonical": "Django", "category": "Frameworks & Libraries"},
    "flask": {"canonical": "Flask", "category": "Frameworks & Libraries"},
    "fastapi": {"canonical": "FastAPI", "category": "Frameworks & Libraries"},
    "spring": {"canonical": "Spring Boot", "category": "Frameworks & Libraries"},
    "spring boot": {"canonical": "Spring Boot", "category": "Frameworks & Libraries"},
    ".net": {"canonical": ".NET", "category": "Frameworks & Libraries"},
    "dotnet": {"canonical": ".NET", "category": "Frameworks & Libraries"},
    "asp.net": {"canonical": "ASP.NET", "category": "Frameworks & Libraries"},
    "ruby on rails": {"canonical": "Ruby on Rails", "category": "Frameworks & Libraries"},
    "rails": {"canonical": "Ruby on Rails", "category": "Frameworks & Libraries"},
    "tailwind": {"canonical": "Tailwind CSS", "category": "Frameworks & Libraries"},
    "tailwindcss": {"canonical": "Tailwind CSS", "category": "Frameworks & Libraries"},
    "bootstrap": {"canonical": "Bootstrap", "category": "Frameworks & Libraries"},

    # Machine Learning & AI
    "machine learning": {"canonical": "Machine Learning", "category": "AI & Data Science"},
    "ml": {"canonical": "Machine Learning", "category": "AI & Data Science", "word_boundary": True},
    "deep learning": {"canonical": "Deep Learning", "category": "AI & Data Science"},
    "dl": {"canonical": "Deep Learning", "category": "AI & Data Science", "word_boundary": True},
    "natural language processing": {"canonical": "Natural Language Processing (NLP)", "category": "AI & Data Science"},
    "nlp": {"canonical": "Natural Language Processing (NLP)", "category": "AI & Data Science", "word_boundary": True},
    "computer vision": {"canonical": "Computer Vision", "category": "AI & Data Science"},
    "cv": {"canonical": "Computer Vision", "category": "AI & Data Science", "word_boundary": True},
    "scikit-learn": {"canonical": "Scikit-Learn", "category": "AI & Data Science"},
    "sklearn": {"canonical": "Scikit-Learn", "category": "AI & Data Science"},
    "pandas": {"canonical": "Pandas", "category": "AI & Data Science"},
    "numpy": {"canonical": "NumPy", "category": "AI & Data Science"},
    "pytorch": {"canonical": "PyTorch", "category": "AI & Data Science"},
    "tensorflow": {"canonical": "TensorFlow", "category": "AI & Data Science"},
    "keras": {"canonical": "Keras", "category": "AI & Data Science"},
    "large language models": {"canonical": "LLMs", "category": "AI & Data Science"},
    "llm": {"canonical": "LLMs", "category": "AI & Data Science", "word_boundary": True},
    "llms": {"canonical": "LLMs", "category": "AI & Data Science"},
    "generative ai": {"canonical": "Generative AI", "category": "AI & Data Science"},
    "genai": {"canonical": "Generative AI", "category": "AI & Data Science"},
    "data science": {"canonical": "Data Science", "category": "AI & Data Science"},
    "data analysis": {"canonical": "Data Analysis", "category": "AI & Data Science"},

    # Databases & Big Data
    "postgresql": {"canonical": "PostgreSQL", "category": "Databases & Storage"},
    "postgres": {"canonical": "PostgreSQL", "category": "Databases & Storage"},
    "mysql": {"canonical": "MySQL", "category": "Databases & Storage"},
    "sqlite": {"canonical": "SQLite", "category": "Databases & Storage"},
    "mongodb": {"canonical": "MongoDB", "category": "Databases & Storage"},
    "mongo": {"canonical": "MongoDB", "category": "Databases & Storage"},
    "redis": {"canonical": "Redis", "category": "Databases & Storage"},
    "cassandra": {"canonical": "Cassandra", "category": "Databases & Storage"},
    "dynamodb": {"canonical": "DynamoDB", "category": "Databases & Storage"},
    "oracle": {"canonical": "Oracle DB", "category": "Databases & Storage"},
    "elasticsearch": {"canonical": "Elasticsearch", "category": "Databases & Storage"},
    "snowflake": {"canonical": "Snowflake", "category": "Databases & Storage"},
    "bigquery": {"canonical": "BigQuery", "category": "Databases & Storage"},
    "kafka": {"canonical": "Apache Kafka", "category": "Databases & Storage"},
    "spark": {"canonical": "Apache Spark", "category": "Databases & Storage"},
    "pyspark": {"canonical": "Apache Spark", "category": "Databases & Storage"},
    "hadoop": {"canonical": "Hadoop", "category": "Databases & Storage"},

    # Cloud & DevOps
    "aws": {"canonical": "AWS", "category": "Cloud & DevOps"},
    "amazon web services": {"canonical": "AWS", "category": "Cloud & DevOps"},
    "azure": {"canonical": "Microsoft Azure", "category": "Cloud & DevOps"},
    "gcp": {"canonical": "Google Cloud (GCP)", "category": "Cloud & DevOps"},
    "google cloud": {"canonical": "Google Cloud (GCP)", "category": "Cloud & DevOps"},
    "docker": {"canonical": "Docker", "category": "Cloud & DevOps"},
    "kubernetes": {"canonical": "Kubernetes", "category": "Cloud & DevOps"},
    "k8s": {"canonical": "Kubernetes", "category": "Cloud & DevOps"},
    "terraform": {"canonical": "Terraform", "category": "Cloud & DevOps"},
    "ansible": {"canonical": "Ansible", "category": "Cloud & DevOps"},
    "jenkins": {"canonical": "Jenkins", "category": "Cloud & DevOps"},
    "ci/cd": {"canonical": "CI/CD", "category": "Cloud & DevOps"},
    "github actions": {"canonical": "GitHub Actions", "category": "Cloud & DevOps"},
    "gitlab ci": {"canonical": "GitLab CI", "category": "Cloud & DevOps"},
    "linux": {"canonical": "Linux", "category": "Cloud & DevOps"},
    "nginx": {"canonical": "Nginx", "category": "Cloud & DevOps"},
    "git": {"canonical": "Git", "category": "Cloud & DevOps", "word_boundary": True},
    "github": {"canonical": "GitHub", "category": "Cloud & DevOps"},

    # Software Engineering & Architecture
    "rest api": {"canonical": "REST APIs", "category": "Architecture & Engineering"},
    "rest": {"canonical": "REST APIs", "category": "Architecture & Engineering", "word_boundary": True},
    "restful": {"canonical": "REST APIs", "category": "Architecture & Engineering"},
    "graphql": {"canonical": "GraphQL", "category": "Architecture & Engineering"},
    "microservices": {"canonical": "Microservices", "category": "Architecture & Engineering"},
    "system design": {"canonical": "System Design", "category": "Architecture & Engineering"},
    "oop": {"canonical": "Object-Oriented Programming (OOP)", "category": "Architecture & Engineering", "word_boundary": True},
    "object-oriented": {"canonical": "Object-Oriented Programming (OOP)", "category": "Architecture & Engineering"},
    "tdd": {"canonical": "Test-Driven Development (TDD)", "category": "Architecture & Engineering", "word_boundary": True},
    "unit testing": {"canonical": "Unit Testing", "category": "Architecture & Engineering"},
    "agile": {"canonical": "Agile Methodology", "category": "Methodologies"},
    "scrum": {"canonical": "Scrum", "category": "Methodologies"},
    "kanban": {"canonical": "Kanban", "category": "Methodologies"},

    # Soft Skills & Leadership
    "leadership": {"canonical": "Leadership", "category": "Soft Skills"},
    "team leadership": {"canonical": "Leadership", "category": "Soft Skills"},
    "communication": {"canonical": "Communication", "category": "Soft Skills"},
    "problem solving": {"canonical": "Problem Solving", "category": "Soft Skills"},
    "collaboration": {"canonical": "Cross-Functional Collaboration", "category": "Soft Skills"},
    "cross-functional": {"canonical": "Cross-Functional Collaboration", "category": "Soft Skills"},
    "project management": {"canonical": "Project Management", "category": "Soft Skills"},
    "mentorship": {"canonical": "Mentorship", "category": "Soft Skills"},
    "mentoring": {"canonical": "Mentorship", "category": "Soft Skills"}
}


# ============================================================================
# Section Boundary Detection for Required vs Preferred Qualifications
# ============================================================================

REQUIRED_PATTERNS = [
    r'(?i)(?:basic|minimum|required|key|core)\s+(?:qualifications|requirements|skills)',
    r'(?i)what\s+you(?:\'ll)?\s+(?:need|bring)',
    r'(?i)must\s+have',
    r'(?i)requirements:'
]

PREFERRED_PATTERNS = [
    r'(?i)(?:preferred|desired|bonus|nice\s+to\s+have)\s+(?:qualifications|requirements|skills)',
    r'(?i)bonus\s+points',
    r'(?i)plusses?:',
    r'(?i)preferred:'
]


def partition_job_description(jd_text: str) -> Tuple[str, str]:
    """
    Split job description into 'required' and 'preferred' content sections if detectable.
    Returns (required_text, preferred_text).
    """
    req_split = -1
    pref_split = -1

    for pat in REQUIRED_PATTERNS:
        match = re.search(pat, jd_text)
        if match:
            req_split = match.start()
            break

    for pat in PREFERRED_PATTERNS:
        match = re.search(pat, jd_text)
        if match:
            pref_split = match.start()
            break

    if req_split != -1 and pref_split != -1 and pref_split > req_split:
        required_text = jd_text[req_split:pref_split]
        preferred_text = jd_text[pref_split:]
        return required_text, preferred_text
    elif pref_split != -1:
        # Before preferred is considered general/required
        return jd_text[:pref_split], jd_text[pref_split:]

    return jd_text, ""


# ============================================================================
# Skill Extraction and Normalization
# ============================================================================

def extract_skills_from_text(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract skills from text using boundary-safe regex pattern matching
    and normalize them into canonical representation.
    Returns dict mapping canonical_name -> {canonical, category, term_matched}.
    """
    if not text or not text.strip():
        return {}

    lowered = text.lower()
    detected: Dict[str, Dict[str, Any]] = {}

    for term, meta in SKILL_TAXONOMY.items():
        canonical = meta["canonical"]
        category = meta["category"]

        # Handle regex pattern matching based on token boundaries
        if meta.get("exact_only"):
            # Single letters like 'R' require strict word boundaries and uppercase in raw text
            pattern = rf'\b{re.escape(term.upper())}\b'
            if re.search(pattern, text):
                detected[canonical] = {
                    "canonical": canonical,
                    "category": category,
                    "term": term
                }
        elif meta.get("word_boundary") or len(term) <= 3:
            pattern = rf'(?<![a-zA-Z0-9_]){re.escape(term)}(?![a-zA-Z0-9_])'
            if re.search(pattern, lowered):
                detected[canonical] = {
                    "canonical": canonical,
                    "category": category,
                    "term": term
                }
        else:
            # Multi-word or distinctive names
            if term in lowered:
                detected[canonical] = {
                    "canonical": canonical,
                    "category": category,
                    "term": term
                }

    return detected


# ============================================================================
# Parse Quality Inspection
# ============================================================================

def inspect_parsing_quality(resume_text: str) -> Dict[str, Any]:
    """
    Analyze the extracted resume text for potential parsing flaws or warnings.
    """
    words = re.findall(r'\b\w+\b', resume_text)
    word_count = len(words)
    char_count = len(resume_text)

    warnings: List[str] = []

    if word_count == 0:
        warnings.append("No text could be extracted from the resume. The file may be empty or contain non-selectable scanned images.")
    elif word_count < 60:
        warnings.append("The extracted resume text contains fewer than 60 words. Ensure the document is not an image-only PDF.")
    elif word_count < 150:
        warnings.append("The resume content is relatively brief. A more detailed description of your achievements and tools can improve accuracy.")

    # Check for standard resume sections
    has_experience = bool(re.search(r'(?i)\b(experience|employment|work history|career)\b', resume_text))
    has_skills = bool(re.search(r'(?i)\b(skills|technical proficiencies|technologies|competencies)\b', resume_text))
    has_education = bool(re.search(r'(?i)\b(education|university|college|degree|academic)\b', resume_text))

    return {
        "word_count": word_count,
        "char_count": char_count,
        "has_experience_section": has_experience,
        "has_skills_section": has_skills,
        "has_education_section": has_education,
        "warnings": warnings,
        "is_sparse": word_count < 60
    }


# ============================================================================
# Complete Explainability and Compatibility Analysis
# ============================================================================

def analyze_compatibility(resume_text: str, job_description: str, score: Optional[float] = None) -> Dict[str, Any]:
    """
    Perform a complete, explainable compatibility analysis comparing
    the candidate resume against the job description.
    """
    # 1. Calculate TF-IDF Cosine Similarity score if not pre-computed
    if score is None:
        if not resume_text.strip() or not job_description.strip():
            score = 0.0
        else:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
            score = round(float(sim), 2)

    # 2. Parsing Quality Assessment
    parse_quality = inspect_parsing_quality(resume_text)

    # 3. Partition JD into required vs preferred text
    req_text, pref_text = partition_job_description(job_description)
    
    # 4. Extract skills from resume and job description
    resume_skills_map = extract_skills_from_text(resume_text)
    all_jd_skills_map = extract_skills_from_text(job_description)
    pref_skills_map = extract_skills_from_text(pref_text) if pref_text else {}

    # Required skills are those in JD not explicitly under preferred section
    # (or all JD skills if no preferred section exists)
    required_skills_set = set(all_jd_skills_map.keys()) - set(pref_skills_map.keys())
    preferred_skills_set = set(pref_skills_map.keys())

    # 5. Three Distinct Skill Categories
    matching_skills: List[Dict[str, Any]] = []
    missing_skills: List[Dict[str, Any]] = []
    additional_skills: List[Dict[str, Any]] = []

    for name, data in all_jd_skills_map.items():
        is_required = name in required_skills_set or (not preferred_skills_set)
        importance_label = "Required" if is_required else "Preferred"

        if name in resume_skills_map:
            matching_skills.append({
                "name": name,
                "category": data["category"],
                "importance": importance_label,
                "is_required": is_required
            })
        else:
            missing_skills.append({
                "name": name,
                "category": data["category"],
                "importance": importance_label,
                "is_required": is_required
            })

    for name, data in resume_skills_map.items():
        if name not in all_jd_skills_map:
            additional_skills.append({
                "name": name,
                "category": data["category"]
            })

    # Sort skills alphabetically
    matching_skills.sort(key=lambda x: (not x["is_required"], x["name"]))
    missing_skills.sort(key=lambda x: (not x["is_required"], x["name"]))
    additional_skills.sort(key=lambda x: x["name"])

    # 6. Quantitative Metrics
    total_jd_skills = len(all_jd_skills_map)
    matched_count = len(matching_skills)
    missing_count = len(missing_skills)
    
    total_required = len([s for s in missing_skills + matching_skills if s["is_required"]])
    matched_required = len([s for s in matching_skills if s["is_required"]])

    total_preferred = len([s for s in missing_skills + matching_skills if not s["is_required"]])
    matched_preferred = len([s for s in matching_skills if not s["is_required"]])

    skill_match_percentage = round((matched_count / total_jd_skills * 100), 1) if total_jd_skills > 0 else 0.0
    required_match_percentage = round((matched_required / total_required * 100), 1) if total_required > 0 else 0.0

    # 7. Generate Score Explanation & Factors
    explanation_data = generate_score_explanation(
        score=score,
        skill_match_percentage=skill_match_percentage,
        matched_count=matched_count,
        total_jd_skills=total_jd_skills,
        matched_required=matched_required,
        total_required=total_required,
        missing_skills=missing_skills,
        matching_skills=matching_skills,
        parse_quality=parse_quality
    )

    # 8. Generate Actionable Improvement Recommendations
    recommendations = generate_improvement_recommendations(
        missing_skills=missing_skills,
        parse_quality=parse_quality,
        matched_count=matched_count,
        total_jd_skills=total_jd_skills
    )

    return {
        "score": score,
        "algorithm_name": "TF-IDF Vector Space Model & Cosine Similarity",
        "parse_quality": parse_quality,
        "metrics": {
            "textual_similarity_score": score,
            "skill_match_percentage": skill_match_percentage,
            "required_match_percentage": required_match_percentage,
            "total_job_skills_count": total_jd_skills,
            "matching_skills_count": matched_count,
            "missing_skills_count": missing_count,
            "additional_skills_count": len(additional_skills),
            "matched_required": matched_required,
            "total_required": total_required,
            "matched_preferred": matched_preferred,
            "total_preferred": total_preferred
        },
        "skills": {
            "matching": matching_skills,
            "missing": missing_skills,
            "additional": additional_skills
        },
        "explanation": explanation_data,
        "recommendations": recommendations
    }


# ============================================================================
# Explanation Generator
# ============================================================================

def generate_score_explanation(score: float, skill_match_percentage: float,
                              matched_count: int, total_jd_skills: int,
                              matched_required: int, total_required: int,
                              missing_skills: List[Dict[str, Any]],
                              matching_skills: List[Dict[str, Any]],
                              parse_quality: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formulate a clear narrative explaining the reasons behind the score.
    """
    if score >= 70.0:
        verdict = "Strong Match"
        verdict_summary = "High textual compatibility with strong keyword and technical alignment."
    elif score >= 45.0:
        verdict = "Moderate Match"
        verdict_summary = "Good foundational alignment, with some key terms and specific requirements unrepresented."
    else:
        verdict = "Low Match"
        verdict_summary = "Significant textual and technical variance between the resume and target job requirements."

    # Identify primary drivers of the score
    factors: List[str] = []

    # Factor 1: Term / Lexical Overlap
    if score < 20.0:
        factors.append(f"Low vocabulary overlap ({score}% TF-IDF cosine similarity). The resume uses phrasing, terminology, or project focus distinct from the job posting.")
    elif score < 50.0:
        factors.append(f"Moderate vocabulary alignment ({score}% TF-IDF cosine similarity). Several key terms are shared, but notable document phrasing differences exist.")
    else:
        factors.append(f"High vocabulary alignment ({score}% TF-IDF cosine similarity). The resume closely mirrors the technical phrasing and keywords of the job description.")

    # Factor 2: Skill Overlap
    if total_jd_skills > 0:
        factors.append(f"Technical Skill Coverage: {matched_count} of {total_jd_skills} identified skills detected ({skill_match_percentage}%).")
        if total_required > 0:
            factors.append(f"Core Requirements: {matched_required} of {total_required} required competencies identified.")
    else:
        factors.append("No specific technology keywords from our taxonomy were identified in the job description.")

    # Factor 3: Document length & parsing
    if parse_quality["is_sparse"]:
        factors.append("Document length warning: The extracted resume text is unusually short, which severely penalizes vector overlap.")

    # Primary missing skills highlights
    missing_required_names = [s["name"] for s in missing_skills if s.get("is_required")][:5]
    matching_names = [s["name"] for s in matching_skills][:5]

    return {
        "verdict": verdict,
        "verdict_summary": verdict_summary,
        "factors": factors,
        "highlight_matching": matching_names,
        "highlight_missing": missing_required_names,
        "algorithm_explanation": (
            "The compatibility score is calculated using Term Frequency-Inverse Document Frequency (TF-IDF) "
            "with Cosine Similarity. This mathematical algorithm converts both documents into multi-dimensional "
            "vectors and evaluates the cosine of the angle between them. It specifically measures vocabulary "
            "and keyword overlap rather than an absolute assessment of your real-world capability."
        )
    }


# ============================================================================
# Actionable Improvement Recommendations Generator
# ============================================================================

def generate_improvement_recommendations(missing_skills: List[Dict[str, Any]],
                                        parse_quality: Dict[str, Any],
                                        matched_count: int,
                                        total_jd_skills: int) -> List[Dict[str, str]]:
    """
    Generate targeted recommendations tailored strictly to missing terms and document structure.
    """
    recommendations: List[Dict[str, str]] = []

    # Recommendation 1: Missing Required Skills
    req_missing = [s["name"] for s in missing_skills if s.get("is_required")]
    if req_missing:
        top_skills = ", ".join(req_missing[:4])
        recommendations.append({
            "title": "Address Unrepresented Core Skills",
            "category": "Skills & Experience",
            "advice": (
                f"The job posting explicitly emphasizes: {top_skills}. "
                "If you possess genuine experience with any of these technologies, detail them explicitly in your "
                "experience bullet points or technical skills section."
            )
        })

    # Recommendation 2: Contextualize with Projects & Outcomes
    if len(missing_skills) > 0:
        recommendations.append({
            "title": "Demonstrate Skills in Project Context",
            "category": "Impact & Depth",
            "advice": (
                "Avoid merely listing tools in a comma-separated list. Describe how you applied them to deliver results "
                "(e.g., 'Engineered microservices using Docker and deployed onto AWS to reduce build latency by 35%')."
            )
        })

    # Recommendation 3: Document Structure & Parser Accessibility
    if not parse_quality.get("has_skills_section"):
        recommendations.append({
            "title": "Add a Dedicated 'Skills' Section",
            "category": "Formatting",
            "advice": (
                "A distinct 'Skills' or 'Technical Competencies' heading makes it easier for both automated parsers "
                "and human recruiters to quickly identify your core technologies."
            )
        })

    if parse_quality.get("is_sparse"):
        recommendations.append({
            "title": "Expand Role Descriptions & Quantifiable Achievements",
            "category": "Content Depth",
            "advice": (
                "Your resume text appears concise. Expand on your key responsibilities, challenges solved, and "
                "technologies used in each position to give matching algorithms more relevant vocabulary to analyze."
            )
        })

    # Recommendation 4: Ethical Disclaimer
    recommendations.append({
        "title": "Maintain Authentic Experience",
        "category": "Best Practices",
        "advice": (
            "Never include qualifications or technologies you do not genuinely know. Aim to present your authentic "
            "background clearly using industry-standard terminology."
        )
    })

    return recommendations
