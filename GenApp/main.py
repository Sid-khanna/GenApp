import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')  # For session use

# === OpenRouter setup ===
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://your-project.com",
        "X-Title": "AI Character Creator",
    }
)

# === Questions ===
personality_questions = [
    "What is a memory that shaped who you are today?",
    "What do you want to be remembered for?",
    "When do you feel most like yourself?",
    "What’s one thing you’re deeply passionate about?",
    "If you could give your younger self one piece of advice, what would it be?",
    "What’s a fictional world you’d love to live in, and why?",
    "If your personality were a color palette, what colors would it include?",
    "What kind of music best represents your mood today?",
    "What’s something that always makes you smile?",
    "What’s a dream you’ve yet to pursue?"
]

general_questions = [
    "What kind of character do you want to create?",
    "What motivates them?",
    "What are they afraid of?",
    "Describe a world they might live in.",
    "Do they have any special abilities or secrets?"
]

@app.route('/', methods=['GET', 'POST'])
def form_page():
    if request.method == 'POST':
        mode = request.form.get('mode')
        questions = personality_questions if mode == 'self' else general_questions
        answers = [request.form.get(f'q{i}') for i in range(len(questions))]
        responses = dict(zip(questions, answers))

        style = extract_style(responses)

        # Store in session
        session['mode'] = mode
        session['responses'] = responses
        session['style'] = style

        return redirect(url_for('story_preferences'))

    return render_template('form.html', mode_select=True)

@app.route('/questions', methods=['POST'])
def show_questions():
    mode = request.form.get('mode')
    questions = personality_questions if mode == 'self' else general_questions
    return render_template('form.html', questions=questions, mode=mode)

@app.route('/story_preferences', methods=['GET', 'POST'])
def story_preferences():
    genre_options = get_genre_options()
    tone_options = ["hopeful", "dark", "witty", "poetic", "melancholic", "adventurous", "introspective"]

    if request.method == 'POST':
        genre = request.form.get('genre')
        tone = request.form.get('tone')

        # Retrieve from session
        responses = session.get('responses')
        style = session.get('style')
        mode = session.get('mode')

        if not responses or not style or not mode:
            return redirect(url_for('form_page'))

        character_profile, plot = generate_character_and_plot(responses, style, genre, tone, mode)

        # Store result
        session['profile'] = character_profile
        session['plot'] = plot
        session['genre'] = genre

        return render_template('character_preview.html', profile=character_profile, plot=plot)

    return render_template('preferences.html', genre_options=genre_options, tone_options=tone_options)

@app.route('/generate_story', methods=['POST'])
def generate_story():
    profile = session.get('profile')
    plot = session.get('plot')
    genre = session.get('genre')

    if not profile or not plot or not genre:
        return redirect(url_for('form_page'))

    blurb = generate_blurb(profile, plot, genre)
    return render_template('result.html', profile=profile, plot=plot, blurb=blurb)

# === Utils ===

def get_genre_options():
    return ["Fantasy", "Modern", "Sci-Fi", "Historical", "Dystopian", "Slice of Life"]

def extract_style(responses):
    formatted = "\n".join([f"Q: {q}\nA: {a}" for q, a in responses.items()])
    prompt = f"""
    Analyze the following answers and describe the user's tone and emotional style.
    Focus on mood, sentence complexity, use of imagery or metaphor, and emotional depth.

    {formatted}
    """
    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Style extraction error:", e)
        return "Reflective and poetic."

def generate_character_and_plot(responses, style, genre, tone, mode):
    formatted = "\n".join([f"Q: {q}\nA: {a}" for q, a in responses.items()])
    background = "Make this character reflect the user's own identity." if mode == 'self' else "Create an original fictional character."

    prompt = f"""
    Tone: {style}
    Genre: {genre}
    Desired tone: {tone}
    {background}

    Responses:
    {formatted}

    Create a fictional character profile and a 3–5 bullet point plotline.
    Include name, age, background, strengths, weaknesses, and goals.
    """
    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.85,
        )
        content = completion.choices[0].message.content.strip()
        parts = content.split("Plotline:")
        return parts[0].strip(), parts[1].strip() if len(parts) > 1 else "Plot unavailable."
    except Exception as e:
        print("Character generation error:", e)
        return "Error creating character.", ""

def generate_blurb(profile, plot, genre):
    prompt = f"""
    Write a 200-word story blurb in the {genre} genre.

    Character Profile:
    {profile}

    Plot:
    {plot}
    """
    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.8,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Blurb generation error:", e)
        return "Error generating blurb."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000)
