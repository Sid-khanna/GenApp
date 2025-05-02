from flask import Flask, render_template, request
from openai import OpenAI
import datetime

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === OpenRouter setup ===
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Replace with your key
    default_headers={
        "HTTP-Referer": "https://your-project.com",
        "X-Title": "AI Biographer",
    })

# === 15 core questions ===
questions = [
    "What is a memory that shaped who you are today?",
    "What do you want to be remembered for?",
    "When do you feel most like yourself?",
    "What’s one thing you’re deeply passionate about?",
    "If you could give your younger self one piece of advice, what would it be?",
    "If your life were a novel, what would its title be?",
    "What’s a fictional world you’d love to live in, and why?",
    "If your personality were a color palette, what colors would it include?",
    "What kind of music best represents your mood today?",
    "If you could create a piece of art that represents your life, what would it look like?",
    "What’s something that always makes you smile?",
    "What’s a fear you’ve overcome, and how did you do it?",
    "Who has had the most significant impact on your life?",
    "What’s a dream you’ve yet to pursue?", "How do you define happiness?"
]


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        answers = [request.form.get(f'q{i}') for i in range(len(questions))]

        # Format answers
        responses = dict(zip(questions, answers))
        style = extract_style(responses)
        story = generate_biography(responses, style)
        return render_template('result.html', story=story)

    return render_template('form.html', questions=questions)


def extract_style(responses):
    formatted = "\n".join([f"Q: {q}\nA: {a}" for q, a in responses.items()])
    prompt = f"""
    Analyze the following answers and infer the user's writing style and emotional tone.
    Describe the voice in terms of sentence structure (short/long, complex/simple), figurative language, emotional weight, and attitude.

    {formatted}
    """

    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=200,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return "Reflective and poetic."


def generate_biography(responses, style_description):
    formatted = "\n".join([f"Q: {q}\nA: {a}" for q, a in responses.items()])
    prompt = f"""
    Write a 200-word short story based on these answers. Reflect the user's tone and values.
    Use this writing style: {style_description}
    Do not copy the answers directly, but capture their emotional world.

    {formatted}
    """

    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=800,
            temperature=0.85,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000)
