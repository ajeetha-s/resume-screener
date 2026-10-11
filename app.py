"""
Intelligent Resume Screening and Candidate Ranking System
=========================================================

A small, dependency-light Streamlit application that helps a recruiter:

1. Upload multiple PDF resumes and extract their text (PyMuPDF).
2. Paste a job description and extract the skills / keywords that matter.
3. Score and rank every candidate against that description (pure Python
   keyword matching -- no AI model, no paid API, no API key).
4. Preview and optionally send acknowledgement / status emails using only
   Python's standard library (smtplib + email).

IMPORTANT: This is a PROTOTYPE. Matching is deterministic keyword/skill
matching, not a trained machine-learning model and not an LLM. See README.md.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
import re
import smtplib
import ssl
from collections import Counter
from email.message import EmailMessage

import pandas as pd
import streamlit as st

try:  # PyMuPDF >= 1.23 exposes the package as "pymupdf"
    import pymupdf as fitz
except ImportError:  # pragma: no cover - older PyMuPDF releases
    import fitz


# --------------------------------------------------------------------------
# 1. Skill vocabulary
# --------------------------------------------------------------------------
# A curated, offline dictionary: canonical skill name -> list of aliases that
# may appear in a resume or a job description. Extend freely; nothing here is
# fetched from the network and no model is downloaded.

SKILLS: dict[str, list[str]] = {
    # Programming languages
    "Python": ["python", "python3"],
    "Java": ["java", "core java", "j2ee"],
    "JavaScript": ["javascript", "js", "ecmascript", "es6"],
    "TypeScript": ["typescript"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", "c sharp"],
    "C": ["c programming", "embedded c"],
    "Go": ["golang", "go lang", "go programming", "go language", "goroutines"],
    "Rust": ["rust"],
    "Kotlin": ["kotlin"],
    "Swift": ["swift", "swiftui"],
    "Objective-C": ["objective-c", "objective c"],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "Scala": ["scala"],
    "Perl": ["perl"],
    "R": ["r programming", "r language", "rstudio"],
    "MATLAB": ["matlab"],
    "Dart": ["dart", "flutter"],
    "Bash/Shell": ["bash", "shell scripting", "shell script", "zsh"],
    "PowerShell": ["powershell"],
    "SQL": ["sql", "sql queries", "structured query language"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "SAS": ["sas"],
    "VBA": ["vba", "visual basic"],

    # Web / backend frameworks
    "React": ["react", "reactjs", "react.js"],
    "Angular": ["angular", "angularjs"],
    "Vue": ["vue", "vuejs", "vue.js"],
    "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "Express": ["express", "expressjs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring": ["spring", "spring boot", "springboot"],
    "Ruby on Rails": ["ruby on rails", "rails"],
    "Laravel": ["laravel"],
    "ASP.NET": ["asp.net", "aspnet"],
    ".NET": [".net", "dotnet"],
    "jQuery": ["jquery"],
    "Bootstrap": ["bootstrap"],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "GraphQL": ["graphql"],
    "REST API": ["rest api", "restful", "rest apis", "web services", "restful api"],
    "gRPC": ["grpc"],
    "Microservices": ["microservices", "microservice"],
    "WebSockets": ["websocket", "websockets"],

    # Data science / machine learning
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "neural network", "neural networks"],
    "Natural Language Processing": ["natural language processing", "nlp"],
    "Computer Vision": ["computer vision", "image processing", "opencv"],
    "Data Science": ["data science", "data scientist"],
    "Data Analysis": ["data analysis", "data analyst", "data analytics"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "SciPy": ["scipy"],
    "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch", "torch"],
    "Keras": ["keras"],
    "XGBoost": ["xgboost", "lightgbm", "catboost"],
    "spaCy": ["spacy"],
    "NLTK": ["nltk"],
    "Hugging Face": ["huggingface", "hugging face"],
    "LLM": ["llm", "llms", "large language model", "large language models"],
    "Generative AI": ["generative ai", "genai", "gen ai"],
    "Transformers": ["transformers"],
    "MLOps": ["mlops"],
    "Statistics": ["statistics", "statistical"],
    "A/B Testing": ["a/b testing", "ab testing", "experimentation"],
    "Feature Engineering": ["feature engineering"],
    "Data Visualization": ["data visualization", "matplotlib", "seaborn", "plotly"],

    # Data engineering / databases
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Cassandra": ["cassandra"],
    "Oracle": ["oracle db", "oracle database", "pl/sql"],
    "SQL Server": ["sql server", "mssql", "t-sql"],
    "SQLite": ["sqlite"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    "Kafka": ["kafka"],
    "Spark": ["spark", "pyspark"],
    "Hadoop": ["hadoop"],
    "Hive": ["hive"],
    "Airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt"],
    "Snowflake": ["snowflake"],
    "BigQuery": ["bigquery"],
    "Redshift": ["redshift"],
    "ETL": ["etl", "elt", "data pipeline", "data pipelines"],
    "Data Warehousing": ["data warehouse", "data warehousing"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Looker": ["looker"],
    "Excel": ["excel", "spreadsheets", "vlookup"],

    # Cloud / DevOps
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure"],
    "Google Cloud": ["gcp", "google cloud", "google cloud platform"],
    "Docker": ["docker", "containerization", "containers"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],
    "Jenkins": ["jenkins"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"],
    "GitHub Actions": ["github actions"],
    "GitLab CI": ["gitlab ci", "gitlab-ci"],
    "Linux": ["linux", "unix"],
    "Nginx": ["nginx"],
    "Apache": ["apache http", "httpd"],
    "Serverless": ["serverless"],
    "Prometheus": ["prometheus"],
    "Grafana": ["grafana"],
    "OpenShift": ["openshift"],

    # Tools & engineering practice
    "Git": ["git", "version control"],
    "GitHub": ["github"],
    "GitLab": ["gitlab"],
    "Bitbucket": ["bitbucket"],
    "Jira": ["jira"],
    "Confluence": ["confluence"],
    "Agile": ["agile"],
    "Scrum": ["scrum"],
    "Kanban": ["kanban"],
    "TDD": ["tdd", "test-driven", "test driven development"],
    "Unit Testing": ["unit testing", "unit tests"],
    "PyTest": ["pytest"],
    "Jest": ["jest"],
    "Selenium": ["selenium"],
    "Cypress": ["cypress"],
    "Postman": ["postman"],
    "Swagger": ["swagger", "openapi"],
    "OAuth": ["oauth", "oauth2"],
    "JWT": ["jwt", "json web token"],
    "RabbitMQ": ["rabbitmq"],
    "Celery": ["celery"],
    "Data Structures": ["data structures", "data structure"],
    "Algorithms": ["algorithms", "algorithm"],
    "OOP": ["object-oriented", "object oriented", "oop", "object-oriented programming"],
    "Design Patterns": ["design patterns"],
    "System Design": ["system design", "architecture design", "solution architecture"],
    "Code Review": ["code review", "code reviews", "peer review"],
    "Debugging": ["debugging", "troubleshooting"],
    "Documentation": ["documentation", "technical writing"],
    "QA": ["qa", "quality assurance", "software testing", "test cases"],
    "Accessibility": ["accessibility", "wcag", "a11y"],
    "SEO": ["seo", "search engine optimization"],

    # Design / product
    "Figma": ["figma"],
    "UI/UX": ["ui/ux", "ux design", "ui design", "user experience"],
    "Photoshop": ["photoshop", "adobe creative", "illustrator"],
    "AutoCAD": ["autocad"],

    # Enterprise / domain software
    "Salesforce": ["salesforce"],
    "SAP": ["sap"],
    "ERP": ["erp"],
    "CRM": ["crm"],

    # Domains
    "Banking": ["banking"],
    "Finance": ["finance", "financial services"],
    "Fintech": ["fintech"],
    "Healthcare": ["healthcare", "health care"],
    "E-commerce": ["e-commerce", "ecommerce"],
    "Insurance": ["insurance"],
    "Telecom": ["telecom", "telecommunications"],
    "Retail": ["retail"],

    # Soft skills
    "Communication": ["communication", "verbal communication", "written communication"],
    "Leadership": ["leadership", "lead", "leading"],
    "Teamwork": ["teamwork", "team player", "collaborative"],
    "Problem Solving": ["problem solving", "problem-solving", "analytical thinking"],
    "Project Management": ["project management", "project manager"],
    "Mentoring": ["mentoring", "mentorship", "coaching"],
    "Collaboration": ["collaboration", "cross-functional", "cross functional"],
    "Adaptability": ["adaptability", "flexible", "fast learner"],
    "Time Management": ["time management", "prioritization"],
    "Critical Thinking": ["critical thinking"],
    "Presentation": ["presentation", "public speaking"],
    "Stakeholder Management": ["stakeholder management", "stakeholders"],
    "Attention to Detail": ["attention to detail", "detail-oriented"],

    # Education / certifications
    "Bachelor's Degree": ["bachelor", "bachelors", "b.tech", "b.e.", "b.sc", "undergraduate degree"],
    "Master's Degree": ["master", "masters", "m.tech", "m.sc", "m.s.", "graduate degree"],
    "PhD": ["ph.d", "phd", "doctorate"],
    "MBA": ["mba"],
}


def _compile(alias: str) -> re.Pattern[str]:
    """Turn one alias into a boundary-aware, case-insensitive regex.

    The look-around keeps short aliases honest: "C" does not match "C++" or
    "C#", "Java" does not match "JavaScript", "SQL" does not match "MySQL".
    """
    words = alias.split()
    if len(words) > 1:
        body = r"[\s\-_/]*".join(re.escape(w) for w in words)
    else:
        body = re.escape(alias)
    return re.compile(r"(?<![A-Za-z0-9+#.])" + body + r"(?![A-Za-z0-9+#])", re.IGNORECASE)


SKILL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, _compile(alias)) for name, aliases in SKILLS.items() for alias in aliases
]

# Words that carry no signal when building a keyword profile of a job ad.
STOPWORDS = set(
    """
a about above across after again against all also am an and any are aren't as at be because been
before being below between both but by can cannot could couldn't did didn't do does doesn't doing
don't down during each few for from further had hadn't has hasn't have haven't having he her here
hers herself him himself his how i if in into is isn't it its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves out over own same shan't
she should shouldn't so some such than that the their theirs them themselves then there these they
this those through to too under until up very was wasn't we were weren't what when where which while
who whom why with won't would wouldn't you your yours yourself yourselves
will shall may might must able
job description role candidate candidates company team teams work working works experience
experiences year years month months strong good great excellent new using use used ability
required require requires preferred plus nice must have responsibility responsibilities
looking hire hiring apply application position opportunity join joining help helping
please us our we you your they their within across etc including include includes
skills skill knowledge understanding familiarity familiar hands-on relevant
degree equivalent field related
opportunity benefits salary compensation
requirements requirement qualifications bonus ideal desirable expertise
responsibility duties tasks day-to-day everyday
""".split()
)


# --------------------------------------------------------------------------
# 2. PDF text extraction
# --------------------------------------------------------------------------

def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """Return (text, page_count) for a PDF given as raw bytes.

    Raises ValueError with a human readable message for encrypted, corrupt or
    empty files so the UI can report the problem per file and keep going.
    """
    if not data:
        raise ValueError("The file is empty (0 bytes).")
    if not data.startswith(b"%PDF") and b"%PDF" not in data[:2048]:
        raise ValueError("This does not look like a valid PDF file.")
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            if getattr(doc, "is_encrypted", False):
                try:
                    doc.authenticate("")
                except Exception:
                    raise ValueError("The PDF is password protected.")
                if doc.is_encrypted:
                    raise ValueError("The PDF is password protected.")
            if doc.page_count == 0:
                raise ValueError("The PDF contains no pages.")
            page_count = doc.page_count
            pages = [page.get_text("text") for page in doc]
    except ValueError:
        raise
    except Exception as exc:  # malformed file, unsupported object, ...
        raise ValueError(f"Could not read this PDF ({type(exc).__name__}: {exc}).")

    text = "\n".join(pages)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), page_count


# --------------------------------------------------------------------------
# 3. Candidate field extraction
# --------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w.])(?:\+\d{1,3}[\s\-.]?)?(?:\(\d{2,4}\)[\s\-.]?|\d{2,4}[\s\-.]?){2,4}\d{2,4}(?![\w.])")

# File extensions that sometimes look like e-mail addresses in a PDF's raw text.
FAKE_EMAIL_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "ico", "pdf", "css", "js"}

SECTION_WORDS = {
    "resume", "resumes", "curriculum", "vitae", "cv", "profile", "summary", "objective",
    "experience", "education", "skills", "contact", "projects", "certifications",
    "achievements", "work", "employment", "personal", "details", "about", "email",
    "phone", "mobile", "linkedin", "github", "address", "career", "professional",
    "technical", "interests", "references", "languages", "awards", "publications",
    "declaration", "internship", "internships", "training", "hobbies", "strengths",
    "overview", "background", "history", "statement", "portfolio", "website", "date",
    "birth", "nationality", "gender", "marital", "name", "candidate", "page",
}

NAME_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*\.?")


def extract_email(text: str) -> str:
    """Return the most plausible personal e-mail address found in the text.

    Real addresses win over reserved documentation domains such as `example.com`;
    the reserved one is only used when nothing else was found, so a sample resume
    is never silently treated as having no e-mail address at all.
    """
    placeholder = ""
    for match in EMAIL_RE.finditer(text):
        email = match.group(0).strip(".,;:()<>[]{}")
        local, _, domain = email.partition("@")
        if not local or domain.count(".") < 1:
            continue
        if domain.split(".")[-1].lower() in FAKE_EMAIL_EXTENSIONS:
            continue
        if domain.lower().startswith(("example.", "domain.", "email.", "test.", "sample.")):
            placeholder = placeholder or email
            continue
        return email
    return placeholder


def extract_phone(text: str) -> str:
    """Return a plausible phone number, or an empty string."""
    for match in PHONE_RE.finditer(text):
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 10 <= len(digits) <= 15 and len(set(digits)) > 2:
            return re.sub(r"\s{2,}", " ", raw).strip()
    return ""


def extract_name(text: str, fallback_filename: str = "") -> str:
    """Guess the candidate's name from the first lines of the resume.

    Looks for a short line of 2-4 capitalised words that is not a section
    heading. Falls back to a tidied version of the file name.
    """
    for raw_line in text.splitlines()[:30]:
        line = raw_line.strip().strip(" .,:|*_-–—\t")
        if not line or len(line) > 60:
            continue
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if ":" in line or "," in line or "|" in line:
            continue
        words = line.split()
        if not 2 <= len(words) <= 4:
            continue
        if not all(NAME_TOKEN_RE.fullmatch(w) for w in words):
            continue
        lowered = [w.lower().strip(".") for w in words]
        if any(w in SECTION_WORDS for w in lowered):
            continue
        if line.isupper():
            return " ".join(w.capitalize() for w in words)
        if all(w[:1].isupper() for w in words):
            return " ".join(w[:1].upper() + w[1:] for w in words)
    return name_from_filename(fallback_filename)


def name_from_filename(filename: str) -> str:
    """Build a readable fallback name such as 'Resume John Smith' -> 'Resume John Smith'."""
    stem = re.sub(r"\.[Pp][Dd][Ff]$", "", os.path.basename(filename or ""))
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = re.sub(r"\b(resume|cv|curriculum vitae|final|updated|new|v\d+|\d{4})\b", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s+", " ", stem).strip()
    if not stem:
        return "Unknown Candidate"
    return stem.title() if stem.isupper() or stem.islower() else stem


# --------------------------------------------------------------------------
# 4. Keyword / skill matching and scoring
# --------------------------------------------------------------------------

def find_skills(text: str) -> set[str]:
    """Return the set of canonical skills mentioned in `text`."""
    return {name for name, pattern in SKILL_PATTERNS if pattern.search(text)}


def _normalise_token(token: str) -> str:
    return token.strip(".-_'").lower()


def extract_keywords(text: str, exclude: set[str] | None = None, limit: int = 25) -> list[str]:
    """Rank the most frequent meaningful words of a text (excluding stopwords)."""
    exclude = exclude or set()
    counts: Counter[str] = Counter()
    for raw in re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", text):
        token = _normalise_token(raw)
        if len(token) < 3 or token in STOPWORDS or token.isdigit():
            continue
        if token in exclude:
            continue
        counts[token] += 1
    if not counts:
        return []
    # Frequent first, then alphabetical so the ordering is stable.
    return [word for word, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def keyword_hits(keywords: list[str], resume_text: str) -> list[str]:
    """Return the keywords of the job description that also appear in a resume."""
    lowered = resume_text.lower()
    return [kw for kw in keywords if re.search(r"(?<![A-Za-z0-9])" + re.escape(kw) + r"(?![A-Za-z0-9])", lowered)]


def score_candidate(
    resume_text: str,
    jd_skills: set[str],
    jd_keywords: list[str],
    skill_weight: float = 0.7,
) -> dict:
    """Score one resume against the job description.

    The final percentage blends two 0-1 ratios:
      * skill_score   - share of the job's required skills found in the resume
      * keyword_score - share of the job's most frequent keywords found
    """
    resume_skills = find_skills(resume_text)
    matched_skills = sorted(jd_skills & resume_skills)
    missing_skills = sorted(jd_skills - resume_skills)

    matched_keywords = keyword_hits(jd_keywords, resume_text)
    missing_keywords = [kw for kw in jd_keywords if kw not in matched_keywords]

    if jd_skills:
        skill_score = len(matched_skills) / len(jd_skills)
    else:
        skill_score = 0.0
    if jd_keywords:
        keyword_score = len(matched_keywords) / len(jd_keywords)
    else:
        keyword_score = 0.0

    if jd_skills and jd_keywords:
        total = skill_weight * skill_score + (1.0 - skill_weight) * keyword_score
    else:
        total = skill_score or keyword_score

    return {
        "score": round(100.0 * max(0.0, min(1.0, total)), 1),
        "skill_score": round(100.0 * skill_score, 1),
        "keyword_score": round(100.0 * keyword_score, 1),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "all_skills": sorted(resume_skills),
    }


# --------------------------------------------------------------------------
# 5. E-mail templates and delivery (standard library only)
# --------------------------------------------------------------------------

def build_email(
    template: str,
    *,
    candidate_name: str,
    job_title: str,
    company: str,
    recruiter: str,
    status: str = "",
    feedback: str = "",
) -> tuple[str, str]:
    """Return (subject, body) for one of the two supported templates."""
    name = candidate_name or "Candidate"
    title = job_title.strip()
    role = title or "the position"                      # used on its own (subject line)
    role_phrase = f"the {title} position" if title else "the position"  # inside a sentence
    org = company.strip() or "our organisation"
    signer = recruiter.strip() or "The Hiring Team"
    notes = feedback.strip()

    if template == "acknowledgement":
        subject = f"Application received - {role}"
        body = (
            f"Dear {name},\n\n"
            f"Thank you for applying for {role_phrase} at {org}. "
            f"This message confirms that we have received your application and "
            f"your resume is now with our recruitment team.\n\n"
            f"Our team is reviewing all applications carefully. If your profile "
            f"matches what we are looking for, we will contact you with the next "
            f"steps. We appreciate your patience while the review is in progress.\n\n"
        )
        if notes:
            body += f"Note from the recruiter:\n{notes}\n\n"
        body += (
            f"If you have any questions in the meantime, simply reply to this e-mail.\n\n"
            f"Kind regards,\n{signer}\n{org}"
        )
        return subject, body

    # status notification (selected / rejected)
    if status == "Selected":
        subject = f"Update on your application - {role}"
        body = (
            f"Dear {name},\n\n"
            f"Thank you for your interest in {role_phrase} at {org} and for "
            f"the time you invested in the application process.\n\n"
            f"We are pleased to let you know that we would like to move forward "
            f"with your application.\n\n"
        )
        if notes:
            body += f"Feedback from our review:\n{notes}\n\n"
        else:
            body += (
                "Your background and the skills in your resume are a strong match "
                "for what this role requires.\n\n"
            )
        body += (
            f"We will contact you shortly with the next steps and to schedule the "
            f"following conversations.\n\n"
            f"Congratulations, and we look forward to speaking with you.\n\n"
            f"Kind regards,\n{signer}\n{org}"
        )
        return subject, body

    subject = f"Update on your application - {role}"
    body = (
        f"Dear {name},\n\n"
        f"Thank you for applying for {role_phrase} at {org} and for the "
        f"time and effort you put into your application.\n\n"
        f"After careful consideration we have decided not to move forward with "
        f"your application on this occasion. This was a difficult decision, as we "
        f"received many strong applications.\n\n"
    )
    if notes:
        body += f"Feedback from our review:\n{notes}\n\n"
    else:
        body += (
            "While we were impressed by your background, we have chosen to proceed "
            "with candidates whose experience more closely matches the specific "
            "requirements of this role.\n\n"
        )
    body += (
        f"We would be glad to consider you for future openings that match your "
        f"profile, and we wish you every success in your job search.\n\n"
        f"Kind regards,\n{signer}\n{org}"
    )
    return subject, body


SMTP_ENV_VARS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD")


def get_smtp_config() -> tuple[dict, list[str]]:
    """Read the SMTP settings from environment variables. Never hardcodes secrets."""
    host = (os.environ.get("SMTP_HOST") or "").strip()
    port_raw = (os.environ.get("SMTP_PORT") or "587").strip()
    username = (os.environ.get("SMTP_USERNAME") or "").strip()
    password = os.environ.get("SMTP_PASSWORD") or ""
    sender = (os.environ.get("SMTP_FROM") or "").strip() or username
    use_ssl = (os.environ.get("SMTP_USE_SSL") or "").strip().lower() in {"1", "true", "yes"}
    use_tls = (os.environ.get("SMTP_USE_TLS") or "true").strip().lower() not in {"0", "false", "no"}
    timeout_raw = (os.environ.get("SMTP_TIMEOUT") or "25").strip()

    try:
        port = int(port_raw)
    except ValueError:
        port = 587
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 25.0

    if port == 465:
        use_ssl = True

    missing = [name for name in SMTP_ENV_VARS if not (os.environ.get(name) or "").strip()]
    if username and not password:
        missing.append("SMTP_PASSWORD")

    config = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "use_ssl": use_ssl,
        "use_tls": use_tls,
        "timeout": timeout,
    }
    return config, sorted(set(missing))


def send_email(config: dict, to_address: str, subject: str, body: str) -> tuple[bool, str]:
    """Send one plain-text e-mail. Returns (success, detail_message)."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["sender"]
    message["To"] = to_address
    message.set_content(body)

    try:
        if config["use_ssl"]:
            server = smtplib.SMTP_SSL(
                config["host"], config["port"], timeout=config["timeout"],
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=config["timeout"])

        with server:
            server.ehlo()
            if not config["use_ssl"] and config["use_tls"]:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if config["username"] and config["password"]:
                server.login(config["username"], config["password"])
            server.send_message(message)
        return True, "Delivered to the mail server."
    except Exception as exc:  # network, auth, protocol errors ...
        return False, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# 6. Streamlit user interface
# --------------------------------------------------------------------------

DEMO_JOB_DESCRIPTION = """We are hiring a Senior Python Data Engineer to join our analytics platform team.

Requirements:
- 5+ years of professional experience with Python and SQL.
- Strong experience building ETL data pipelines and data warehousing solutions.
- Hands-on experience with Apache Airflow, Apache Spark and dbt.
- Solid knowledge of AWS cloud services, Docker and Kubernetes.
- Experience with PostgreSQL or Snowflake, and with CI/CD using GitHub Actions.
- Familiarity with machine learning workflows and MLOps is a strong plus.
- Excellent communication, problem solving and stakeholder management skills.
- Experience with Kafka, Terraform and data visualization (Tableau or Power BI) is a plus.
"""


def _short_list(items: list[str], limit: int = 12) -> str:
    if not items:
        return "-"
    shown = ", ".join(items[:limit])
    return shown + (f" (+{len(items) - limit} more)" if len(items) > limit else "")


def init_state() -> None:
    st.session_state.setdefault("parsed", [])       # candidates parsed from the PDFs
    st.session_state.setdefault("signature", None)  # (name, size) of the uploaded files
    st.session_state.setdefault("results", [])      # screening output
    st.session_state.setdefault("jd_used", "")      # job description used for `results`


def parse_uploads(uploaded_files) -> list[dict]:
    """Extract text and basic fields from every uploaded PDF."""
    candidates: list[dict] = []
    for uploaded in uploaded_files:
        try:
            raw = uploaded.getvalue()
            text, page_count = extract_pdf_text(raw)
            if not text:
                raise ValueError("No extractable text found. The PDF may be a scanned image.")
            candidates.append(
                {
                    "name": extract_name(text, uploaded.name),
                    "email": extract_email(text),
                    "phone": extract_phone(text),
                    "text": text,
                    "source": uploaded.name,
                    "pages": page_count,
                    "error": "",
                }
            )
        except ValueError as exc:
            candidates.append(
                {
                    "name": name_from_filename(uploaded.name),
                    "email": "",
                    "phone": "",
                    "text": "",
                    "source": uploaded.name,
                    "pages": 0,
                    "error": str(exc),
                }
            )
    return candidates


def render_sidebar() -> float:
    with st.sidebar:
        st.header("About")
        st.markdown(
            "Upload PDF resumes, paste a job description, and this prototype scores "
            "and ranks every candidate with **deterministic keyword matching**."
        )
        st.warning(
            "**Prototype limitation:** this is keyword-based matching, not a trained "
            "AI model and not an LLM. Scores are an aid for shortlisting, never a "
            "substitute for human review.",
            icon="⚠️",
        )

        st.header("Scoring weights")
        with st.expander("Adjust how the score is blended", expanded=False):
            skill_weight = st.slider(
                "Weight of required skills (%)", 0, 100, 70, 5,
                help="The rest of the weight goes to the job description's frequent keywords.",
            ) / 100.0
            st.caption(
                f"Score = {int(skill_weight * 100)}% skills match "
                f"+ {100 - int(skill_weight * 100)}% keyword match."
            )

        st.header("E-mail status")
        config, missing = get_smtp_config()
        if missing:
            st.info(
                "Preview mode: e-mail sending is disabled because "
                f"{', '.join(missing)} is not set. Everything else works normally.",
                icon="✉️",
            )
        else:
            st.success(
                f"Configured: `{config['username']}` via `{config['host']}:{config['port']}`.",
                icon="✅",
            )
        with st.expander("Required environment variables"):
            st.code(
                "SMTP_HOST=smtp.gmail.com\n"
                "SMTP_PORT=587\n"
                "SMTP_USERNAME=you@example.com\n"
                "SMTP_PASSWORD=your-app-password\n"
                "# optional\n"
                "SMTP_FROM=you@example.com\n"
                "SMTP_USE_TLS=true\n"
                "SMTP_TIMEOUT=25",
                language="bash",
            )

        if st.button("Reset everything", use_container_width=True):
            for key in ("parsed", "signature", "results", "jd_used"):
                st.session_state.pop(key, None)
            st.rerun()
    return skill_weight


def render_upload_section(parsed: list[dict]) -> None:
    st.subheader("1️⃣ Upload resumes (PDF)")
    ok = [c for c in parsed if not c["error"]]
    failed = [c for c in parsed if c["error"]]

    if not parsed:
        st.caption("No resumes uploaded yet. Supported format: PDF (text-based, not scanned images).")
    else:
        st.success(f"{len(ok)} resume(s) read successfully.", icon="✅")
        if failed:
            with st.expander(f"⚠️ {len(failed)} file(s) could not be read", expanded=True):
                for cand in failed:
                    st.error(f"**{cand['source']}** - {cand['error']}")

        for cand in ok:
            meta = cand["email"] or "no e-mail found"
            if cand["phone"]:
                meta += f" · {cand['phone']}"
            meta += f" · {cand['pages']} page(s)"
            with st.expander(f"📄 {cand['name']} — {cand['source']} ({meta})", expanded=False):
                cols = st.columns(2)
                cols[0].markdown(f"**Name:** {cand['name']}")
                cols[1].markdown(f"**E-mail:** {cand['email'] or '_not found_'}")
                st.text_area(
                    "Extracted resume text",
                    value=cand["text"],
                    height=220,
                    # The length keeps the key unique if a file is re-uploaded with
                    # the same name but different content, so we never show stale text.
                    key=f"resume_text_{cand['source']}_{len(cand['text'])}",
                    disabled=True,
                )


def _load_sample_job_description() -> None:
    """on_click callback: runs before widgets are rebuilt, so it may set the key."""
    st.session_state["jd_input"] = DEMO_JOB_DESCRIPTION


def render_job_description_section() -> str:
    st.subheader("2️⃣ Job description")
    jd = st.text_area(
        "Paste the job description",
        height=200,
        key="jd_input",
        placeholder="Paste the full job description here, including the required skills...",
    )
    col1, col2 = st.columns([1, 5])
    with col1:
        st.button(
            "Load a sample JD",
            on_click=_load_sample_job_description,
            use_container_width=True,
        )

    if jd and jd.strip():
        jd_skills = find_skills(jd)
        jd_keywords = extract_keywords(jd, exclude={s.lower() for s in jd_skills})
        left, right = st.columns(2)
        with left:
            st.markdown("**Skills detected in the job description**")
            if jd_skills:
                st.write(", ".join(f"`{s}`" for s in sorted(jd_skills)))
            else:
                st.caption(
                    "No known skill names were recognised. The screener will rely on "
                    "frequent keywords instead."
                )
        with right:
            st.markdown("**Top keywords**")
            if jd_keywords:
                st.write(", ".join(f"`{k}`" for k in jd_keywords))
            else:
                st.caption("No significant keywords found.")
    return jd


def run_screening(jd: str, parsed: list[dict], skill_weight: float) -> None:
    usable = [c for c in parsed if not c["error"]]
    if not usable:
        st.session_state["results"] = []
        st.session_state["jd_used"] = jd
        st.error("No readable resumes to screen. Please upload at least one valid PDF.")
        return

    jd_skills = find_skills(jd)
    jd_keywords = extract_keywords(jd, exclude={s.lower() for s in jd_skills})
    if not jd_skills and not jd_keywords:
        st.session_state["results"] = []
        st.session_state["jd_used"] = jd
        st.error(
            "The job description does not contain any recognisable skills or keywords. "
            "Please paste a more detailed description."
        )
        return

    scored = []
    for cand in usable:
        result = score_candidate(cand["text"] or cand["name"], jd_skills, jd_keywords, skill_weight)
        result.update(
            {
                "name": cand["name"],
                "email": cand["email"],
                "phone": cand["phone"],
                "source": cand["source"],
                "required_skills": sorted(jd_skills),
            }
        )
        scored.append(result)

    scored.sort(key=lambda r: (-r["score"], r["name"].lower()))
    for index, result in enumerate(scored, start=1):
        result["rank"] = index

    st.session_state["results"] = scored
    st.session_state["jd_used"] = jd
    st.toast(f"Screened {len(scored)} candidate(s).", icon="✅")


def render_results_section() -> None:
    results = st.session_state["results"]
    st.subheader("3️⃣ Screening results and ranking")

    if not results:
        st.caption("Run the screening to see the ranking here.")
        return

    st.success(
        f"Ranked {len(results)} candidate(s) against the job description. "
        f"Top score: {results[0]['score']:.1f}% ({results[0]['name']}).",
        icon="🏆",
    )

    table = pd.DataFrame(
        [
            {
                "Rank": r["rank"],
                "Candidate": r["name"],
                "E-mail": r["email"] or "-",
                "Phone": r["phone"] or "-",
                "Match %": r["score"],
                "Matching skills": _short_list(r["matched_skills"]),
                "Missing skills": _short_list(r["missing_skills"]),
                "Resume file": r["source"],
            }
            for r in results
        ]
    )
    st.dataframe(
        table,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Match %": st.column_config.ProgressColumn(
                "Match %", min_value=0.0, max_value=100.0, format="%.1f%%"
            ),
            "Matching skills": st.column_config.TextColumn("Matching skills", width="large"),
            "Missing skills": st.column_config.TextColumn("Missing skills", width="large"),
        },
    )

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download ranking as CSV",
        data=csv,
        file_name="candidate_ranking.csv",
        mime="text/csv",
    )

    # Highlight the strongest candidates.
    st.markdown("#### 🌟 Highest scoring candidates")
    top = results[: min(3, len(results))]
    medals = ["🥇", "🥈", "🥉"]
    columns = st.columns(len(top))
    for column, result, medal in zip(columns, top, medals):
        with column.container(border=True):
            st.markdown(f"### {medal} {result['name']}")
            st.metric("Match score", f"{result['score']:.1f}%")
            st.caption(f"Rank #{result['rank']} · {result['email'] or 'no e-mail found'}")
            st.markdown(f"**Matches:** {_short_list(result['matched_skills'], 8)}")
            st.markdown(f"**Gaps:** {_short_list(result['missing_skills'], 8)}")

    st.markdown("#### 🔍 Per-candidate detail")
    for result in results:
        label = (
            f"#{result['rank']} · {result['name']} — {result['score']:.1f}% "
            f"(skills {result['skill_score']:.0f}% · keywords {result['keyword_score']:.0f}%)"
        )
        with st.expander(label):
            left, right = st.columns(2)
            with left:
                st.markdown("**✅ Matching skills**")
                st.write(
                    ", ".join(result["matched_skills"])
                    if result["matched_skills"]
                    else "_None of the required skills were found._"
                )
                st.markdown("**🔑 Matching keywords**")
                st.write(", ".join(result["matched_keywords"]) or "_none_")
            with right:
                st.markdown("**❌ Missing skills**")
                st.write(
                    ", ".join(result["missing_skills"])
                    if result["missing_skills"]
                    else "_No gaps against the required skills._"
                )
                st.markdown("**📇 Contact**")
                st.write(f"E-mail: {result['email'] or '_not found_'} · Phone: {result['phone'] or '_not found_'}")
            st.progress(result["score"] / 100.0, text=f"Overall match: {result['score']:.1f}%")


def render_email_section() -> None:
    results = st.session_state["results"]
    st.subheader("4️⃣ E-mail acknowledgement")

    if not results:
        st.caption("Screen the candidates first to enable e-mail acknowledgement.")
        return

    with_email = [r for r in results if r["email"]]
    without_email = [r for r in results if not r["email"]]
    config, missing = get_smtp_config()

    st.caption(
        "E-mails are **never** sent automatically. You choose the recipients and the "
        "template, review a preview, and confirm before anything is delivered."
    )
    if without_email:
        st.info(
            f"{len(without_email)} candidate(s) have no e-mail address in their resume and "
            "cannot be contacted: " + ", ".join(r["name"] for r in without_email) + ".",
            icon="📭",
        )
    if not with_email:
        st.warning("None of the screened resumes contained an e-mail address.", icon="⚠️")
        return

    labels = [f"#{r['rank']} · {r['name']} ({r['email']})" for r in with_email]
    selected_labels = st.multiselect(
        "Recipients", labels, default=labels, help="Only candidates with a detected e-mail address are listed."
    )
    selected = [r for r, label in zip(with_email, labels) if label in selected_labels]

    col_job, col_company, col_recruiter = st.columns(3)
    job_title = col_job.text_input(
        "Job title", value="", placeholder="e.g. Senior Data Engineer",
        help="Leave blank to use a generic wording in the e-mail.",
    )
    company = col_company.text_input(
        "Company", value="", placeholder="e.g. Acme Analytics",
    )
    recruiter = col_recruiter.text_input(
        "Signed as", value="The Hiring Team", placeholder="e.g. Talent Acquisition Team",
    )

    template_key = st.radio(
        "E-mail template",
        ("acknowledgement", "status"),
        format_func=lambda k: (
            "1. Application received acknowledgement" if k == "acknowledgement"
            else "2. Selection / rejection status notification"
        ),
        horizontal=True,
    )

    status = ""
    feedback = ""
    if template_key == "status":
        col_status, col_feedback = st.columns([1, 3])
        status = col_status.radio("Decision", ("Selected", "Rejected"), horizontal=True)
        feedback = col_feedback.text_area(
            "Brief feedback (optional, included in the e-mail)",
            height=90,
            placeholder="e.g. Strong Python and SQL background; we would like to see more cloud experience.",
        )
        if status == "Rejected":
            st.warning(
                "Rejection e-mails are never sent automatically in this app. They are only "
                "delivered if you choose this decision and confirm the send below.",
                icon="⚠️",
            )

    if not selected:
        st.info("Select at least one recipient to see the e-mail preview.", icon="👆")
        return

    preview = build_email(
        template_key,
        candidate_name=selected[0]["name"],
        job_title=job_title,
        company=company,
        recruiter=recruiter,
        status=status,
        feedback=feedback,
    )
    with st.expander(f"📧 Preview (personalised for each of the {len(selected)} recipient(s))", expanded=True):
        st.markdown(f"**To:** {', '.join(r['email'] for r in selected)}")
        st.markdown(f"**Subject:** {preview[0]}")
        # st.code is stateless, so the preview always reflects the current template.
        st.code(preview[1], language=None, wrap_lines=True)

    if missing:
        st.warning(
            "E-mail sending is disabled (preview mode). Set these environment variables and "
            f"restart the app to enable delivery: {', '.join(missing)}.",
            icon="✉️",
        )
        st.caption("See the README for a step-by-step guide, including Gmail App Passwords.")
        return

    st.divider()
    confirm = st.checkbox(
        f"I have reviewed the preview and confirm that I want to send this e-mail to "
        f"{len(selected)} recipient(s) now."
    )
    send = st.button(
        f"📤 Send {len(selected)} e-mail(s)",
        type="primary",
        disabled=not confirm,
        use_container_width=True,
    )

    if send and confirm:
        outcomes = []
        progress = st.progress(0.0, text="Sending...")
        for index, result in enumerate(selected, start=1):
            subject, body = build_email(
                template_key,
                candidate_name=result["name"],
                job_title=job_title,
                company=company,
                recruiter=recruiter,
                status=status,
                feedback=feedback,
            )
            ok, detail = send_email(config, result["email"], subject, body)
            outcomes.append((ok, result, detail))
            progress.progress(index / len(selected), text=f"Sent {index} of {len(selected)}...")
        progress.empty()

        sent = [o for o in outcomes if o[0]]
        failed = [o for o in outcomes if not o[0]]
        if sent:
            st.success(f"Sent {len(sent)} e-mail(s): " + ", ".join(o[1]["email"] for o in sent), icon="✅")
        if failed:
            st.error(f"{len(failed)} e-mail(s) were NOT sent.")
            for _, result, detail in failed:
                st.write(f"- **{result['name']}** ({result['email']}): {detail}")
        st.info("No other messages were sent. Nothing is sent automatically.", icon="ℹ️")


def main() -> None:
    st.set_page_config(
        page_title="Resume Screening & Candidate Ranking",
        page_icon="📄",
        layout="wide",
    )
    init_state()

    st.title("📄 Intelligent Resume Screening and Candidate Ranking System")
    st.markdown(
        "Upload PDF resumes, paste a job description, and get an instant, explainable "
        "ranking of candidates — with the matching and missing skills for each one. "
        "Runs fully offline: no API key, no paid AI service, no data leaves your machine."
    )
    st.info(
        "**Prototype notice:** matching uses deterministic keyword and skill matching in "
        "Python. It is not a trained AI model and not an LLM. Use the scores to prioritise "
        "your reading, and always review resumes yourself before making a decision.",
        icon="ℹ️",
    )

    skill_weight = render_sidebar()

    uploaded_files = st.file_uploader(
        "Upload one or more PDF resumes",
        type=["pdf"],
        accept_multiple_files=True,
        help="Text-based PDFs work best; scanned images contain no extractable text.",
    )

    signature = tuple((f.name, f.size) for f in uploaded_files)
    if signature != st.session_state["signature"]:
        st.session_state["signature"] = signature
        st.session_state["parsed"] = parse_uploads(uploaded_files) if uploaded_files else []
        # The candidate set changed, so any previous ranking is now out of date.
        st.session_state["results"] = []
        st.session_state["jd_used"] = ""

    parsed = st.session_state["parsed"]
    render_upload_section(parsed)

    st.divider()
    jd = render_job_description_section()

    st.divider()
    st.subheader("Screening")
    if st.button("🔍 Screen and rank candidates", type="primary", use_container_width=True):
        if not jd or not jd.strip():
            st.error("Please paste a job description before screening.")
        elif not parsed:
            st.error("Please upload at least one PDF resume before screening.")
        else:
            run_screening(jd, parsed, skill_weight)

    if st.session_state["results"] and st.session_state["jd_used"] != jd:
        st.caption("⚠️ The job description has changed since this ranking was produced. Screen again to refresh.")

    st.divider()
    render_results_section()

    st.divider()
    render_email_section()

    st.divider()
    st.caption(
        "Intelligent Resume Screening and Candidate Ranking System · Python, Streamlit, "
        "PyMuPDF, pandas · keyword-based prototype, no AI model or paid service."
    )


if __name__ == "__main__":
    main()
