import gradio as gr
import requests


BACKEND_URL = "http://127.0.0.1:8000/api/check"


def check_concept(explanation):

    response = requests.post(
        BACKEND_URL,
        json={
            "explanation": explanation
        }
    )

    result = response.json()

    return (
        result["recited_sentence"],
        result["follow_up_question"]
    )


demo = gr.Interface(
    fn=check_concept,
    inputs=gr.Textbox(
        label="Explain the concept in your own words"
    ),
    outputs=[
        gr.Textbox(label="Recited sentence"),
        gr.Textbox(label="Follow-up question")
    ],
    title="Concept Check"
)


demo.launch()