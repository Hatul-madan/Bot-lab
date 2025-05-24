import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_gpt(question):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты полезный ассистент."},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content.strip()

def draw_image(prompt):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url