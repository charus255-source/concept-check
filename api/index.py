import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client


# Load values from .env
load_dotenv()


# Create FastAPI application
app = FastAPI()
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>Concept Check</title>
    </head>
    <body>
        <h1>Concept Check</h1>

        <textarea id="explanation" rows="8" cols="70"
        placeholder="Explain the concept in your own words"></textarea>

        <br><br>

        <button onclick="checkConcept()">Submit</button>

        <h3>Recited sentence</h3>
        <p id="recited"></p>

        <h3>Follow-up question</h3>
        <p id="followup"></p>

        <script>
            async function checkConcept() {
                const explanation =
                    document.getElementById("explanation").value;

                const response = await fetch("/api/check", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        explanation: explanation
                    })
                });

                const result = await response.json();

                document.getElementById("recited").innerText =
                    result.recited_sentence || "No recited sentence";

                document.getElementById("followup").innerText =
                    result.follow_up_question || "No follow-up question";
            }
        </script>
    </body>
    </html>
    """


# Create Groq client using the secret key from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)
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
    attempt_response = (
        supabase
        .table("attempts")
        .insert({
            "learner_id": 1,
            "idea_id": 1,
            "attempt_type": "initial",
            "response_text": explanation,
            "result": "pending"
        })
        .execute()
    )

    attempt_id = attempt_response.data[0]["attempt_id"]
    supabase.table("recited_sentences").insert({
    "attempt_id": attempt_id,
    "recited_sentence": result["recited_sentence"],
    "followup_question": result["follow_up_question"]
}).execute()
    return result
   


# Concept Check API endpoint
@app.post("/api/check")
def check_explanation(request: ExplanationRequest):

    result = analyze_explanation(request.explanation)

    return result