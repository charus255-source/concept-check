import json
import os

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq


# Load values from .env
load_dotenv()


# Create FastAPI application
app = FastAPI()


# Create Groq client using the secret key from .env
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

print("Groq key loaded:", bool(os.getenv("GROQ_API_KEY")))


# Define the package the backend expects
class ExplanationRequest(BaseModel):
    explanation: str


# Core Concept Check function
def analyze_explanation(explanation: str):

    prompt = f"""
You are part of a Concept Check learning app.

The learner gave this explanation:

{explanation}

Do exactly two things:
1. Pick one sentence from the learner's explanation that should be probed further.
2. Ask exactly one short follow-up question about that sentence.

Return ONLY valid JSON in this exact shape:

{{
  "recited_sentence": "...",
  "follow_up_question": "..."
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content

    result = json.loads(content)

    return result


# Concept Check API endpoint
@app.post("/api/check")
def check_explanation(request: ExplanationRequest):

    result = analyze_explanation(request.explanation)

    return result