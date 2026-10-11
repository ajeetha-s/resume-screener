# resume-screener
# Intelligent Resume Screening and Candidate Ranking System

A small Streamlit app for recruiters: upload PDF resumes, paste a job description, and get an
explainable ranking of candidates — with the matching and missing skills for each one.

Everything runs locally. **No API key, no paid AI service, no data leaves your machine.**

---

## ⚠️ Important limitation — please read

**This is a keyword-based prototype, not a trained AI model and not an LLM.**

Matching is deterministic Python: a curated dictionary of ~150 skills plus the most frequent
keywords in the job description, compared against the resume text with regular expressions.
The app does **not** understand meaning, context, or seniority, and it cannot tell a genuine
"5 years of Python" from the word Python in a hobby project listing.

Use the scores to decide **what to read first** — never as an automated accept/reject decision.
Always review the resume and the listed gaps yourself.

Consequences worth knowing:

- A candidate who describes a skill differently than your job description scores lower.
- Generic words ("good", "strong", "team") are ignored on purpose; unusual jargon may not be.
- Soft skills are matched literally and carry the same weight as technical ones.
- Ordering is by score; ties are broken alphabetically by name.

---

## Features

1. **Resume upload** — multiple PDFs at once, text extracted with PyMuPDF. Each candidate's
   name, e-mail, phone and full extracted text are shown.
2. **Job description** — paste a JD; the app shows the skills and keywords it detected.
3. **Screening** — matching percentage from 0–100 % per candidate, plus matching and missing
   skills, in a sortable table you can export to CSV.
4. **Ranking** — automatic ranking (highest to lowest) with the top three highlighted and a
   per-candidate breakdown.
5. **E-mail acknowledgement** — two templates (application received; selection/rejection with
   feedback) sent through Python's standard `smtplib`/`email`. Preview mode works with no
   credentials, and nothing is ever sent without an explicit confirmation.

---

## Requirements

- Python 3.9 or newer
- `streamlit`, `pymupdf`, `pandas` (see `requirements.txt`)

---

## Install and run

```bash
# 1. (Recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install the dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Streamlit prints a local URL (usually <http://localhost:8501>) and opens it in your browser.
Press `Ctrl+C` in the terminal to stop the app.

No configuration is needed for the first run — **uploading, screening and ranking all work
without e-mail credentials.**

### Quick test drive

1. Click **Load a sample JD** in the job description section to fill in an example posting.
2. Upload two or three PDF resumes of your own.
3. Click **🔍 Screen and rank candidates**.

---

## Configuring e-mail (optional)

E-mail is **off by default**. Without credentials the app stays in preview mode: it shows the
exact message that would be sent and tells you which variables are missing. Nothing is sent and
nothing crashes.

Credentials are read from environment variables only. **Never hardcode a password in the
source.** All four of these must be set for the send button to activate:

| Variable | Required | Default | Description |
|---|---|---|---|
| `SMTP_HOST` | yes | — | Mail server host, e.g. `smtp.gmail.com` |
| `SMTP_PORT` | yes | — | Usually `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` | yes | — | Login username (often your full e-mail address) |
| `SMTP_PASSWORD` | yes | — | Account password or app password |
| `SMTP_FROM` | no | = `SMTP_USERNAME` | "From" address shown to recipients |
| `SMTP_USE_TLS` | no | `true` | Set `false` to connect without STARTTLS |
| `SMTP_TIMEOUT` | no | `25` | Network timeout in seconds |

Setting `SMTP_PORT=465` automatically switches to implicit SSL, so you do not need to change
anything else for that case.

### Linux / macOS

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="you@gmail.com"
export SMTP_PASSWORD="your-16-char-app-password"
export SMTP_FROM="you@gmail.com"     # optional
streamlit run app.py
```

### Windows PowerShell

```powershell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="you@gmail.com"
$env:SMTP_PASSWORD="your-16-char-app-password"
streamlit run app.py
```

### Gmail note

Gmail does not accept your normal account password for SMTP. Enable 2‑step verification and
generate a 16‑character **App Password**, then use that as `SMTP_PASSWORD`. Keep `SMTP_PORT=587`.

### Permanent setup

To avoid retyping the exports, put them in a file that is **not** committed to git — for example
`.env` — and source it before starting the app (`set -a; source .env; set +a`). Add `.env` to
`.gitignore`.

### Sending e-mail safely

The app never sends anything on its own:

- You pick the recipients and the template.
- You review a live preview that updates as you edit.
- You must tick a confirmation checkbox, which is what enables the send button.
- After sending you get an honest per-recipient report, including any that failed.

Rejection e-mails are never sent automatically — you choose the decision and confirm the batch.

---

## How the score is calculated

```
score = 100 × ( w × skills_matched/skills_required
              + (1-w) × keywords_matched/keywords_required )
```

- `skills_required` — skills from the built-in dictionary found in the job description.
- `keywords_required` — up to 25 most frequent meaningful words in the job description
  (common filler words are ignored).
- `w` — the skills weight, 0.70 by default and adjustable with a slider in the sidebar.

If the job description yields only skills or only keywords, that component is used alone.
Matching is boundary-aware, so `C` does not match `C++`, `Java` does not match `JavaScript`,
and `SQL` does not match `MySQL`.

To teach the app a new skill, add an entry to the `SKILLS` dictionary near the top of `app.py`.

---

## Project files

| File | Purpose |
|---|---|
| `app.py` | The complete application |
| `requirements.txt` | Python dependencies |
| `README.md` | This file |

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| *"This does not look like a valid PDF file"* | The file is not a PDF, or is corrupt. Re-export it. |
| *"No extractable text found…"* | The PDF is a scanned image. Run it through OCR first — PyMuPDF reads text layers only. |
| *"The PDF is password protected"* | Remove the password or upload an unprotected copy. |
| Candidate name shows the file name | No name-like line was found near the top. Rename the file, or check the extracted text in the expander. |
| *"no e-mail found"* | The e-mail is inside an image, or written with an "at" (e.g. `name (at) example.com`). Those cannot be detected. |
| All scores are 0 % | The job description may be too short for any skill or keyword to be detected. Paste the full posting. |
| *"E-mail sending is disabled (preview mode)"* | Set all four required `SMTP_*` variables and restart the app. |
| `SMTPAuthenticationError` | Wrong username/password, or the provider needs an app password (see the Gmail note). |
| `SSLCertVerificationError` | The server's certificate is not trusted. Fix the server; the app never disables verification. |

---

Built with Python, Streamlit, PyMuPDF, pandas and the standard library. No trained model, no
paid service, no network calls except the e-mails you explicitly choose to send.