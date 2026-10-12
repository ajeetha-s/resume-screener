# Intelligent Resume Screening and Candidate Ranking System

## About the Project

This project helps recruiters compare resumes with a job description and rank candidates based on matching skills and keywords.

## Features

* Upload multiple PDF resumes.
* Enter a job description.
* Calculate candidate matching scores.
* Display matching and missing skills.
* Rank candidates based on their scores.

## Technologies Used

* Python
* Streamlit
* PyMuPDF
* Pandas

## How to Run

1. Install Python.
2. Install the required packages using `pip install -r requirements.txt`.
3. Run the application using `python -m streamlit run app.py`.
4. Open the local URL shown in the terminal.

## Current Limitation

The current version uses keyword and skill matching. It does not use a trained AI model or understand the meaning of sentences. Scores should be used as guidance, not as the sole basis for hiring decisions.
