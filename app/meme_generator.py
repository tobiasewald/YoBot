from PIL import Image, ImageDraw, ImageFont
import random
import os

# Define meme templates (you can replace these with your actual meme images)
MEME_TEMPLATES = [
    "meme_template_1.jpg",
    "meme_template_2.jpg",
    "meme_template_3.jpg",
    "meme_template_4.gif",
]

# Funny messages based on severity
FUNNY_MESSAGES = {
    "Critical": "Oh no! This is a disaster! 😱",
    "High": "Yikes! Time to panic! 😅",
    "Medium": "Not bad, but still a little concerning 🤔",
    "Low": "Meh, it's just a little bug 🐛",
}

def create_meme(vuln_name, severity):
    meme_template = random.choice(MEME_TEMPLATES)
    meme_image = Image.open(f"app/templates/{meme_template}")
    draw = ImageDraw.Draw(meme_image)

    font = ImageFont.load_default()
    funny_text = f"{FUNNY_MESSAGES.get(severity, 'Well, that’s unexpected!')}\nVuln: {vuln_name}"

    text_position = (50, 50)
    draw.text(text_position, funny_text, font=font, fill="white")

    meme_image_path = f"app/memes/{vuln_name}_{severity}.jpg"
    meme_image.save(meme_image_path)

    return meme_image_path