import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

print("Supabase connected:", bool(SUPABASE_URL and SUPABASE_SERVICE_KEY))

insert_response = (
    supabase
    .table("learners")
    .insert({
        "learner_name": "Test Learner"
    })
    .execute()
)

print("INSERT:")
print(insert_response.data)

select_response = (
    supabase
    .table("learners")
    .select("*")
    .execute()
)

print("SELECT:")
print(select_response.data)