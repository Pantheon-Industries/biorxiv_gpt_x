import requests
import fitz  # PyMuPDF
import arxiv
import tiktoken
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import textwrap
from datetime import datetime
from github import process_paper

# Load environment variables from .env file
load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def download_and_extract_paper_info(arxiv_id, token_limit=120000, model="gpt-3.5-turbo"):
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    
    title = paper.title
    publish_date = paper.published.date()
    
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_content = response.content
        
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text = ""
        encoding = tiktoken.encoding_for_model(model)
        
        for page in doc:
            page_text = page.get_text()
            text += page_text
            
            tokens = encoding.encode(text)
            if len(tokens) > token_limit:
                text = encoding.decode(tokens[:token_limit])
                break
        twitter_handles=process_paper(text)
        #this will either be an empty list or a list with twitter handles 
        return {
            "title": title,
            "publish_date": publish_date,
            "full_text": text,
            "twitter_handles": twitter_handles
        }
    else:
        print(f"Failed to download paper. Status code: {response.status_code}")
        return None

def summarize_text(text):
    prompt = f""" 
    You are getting the text version of an arxiv paper your goal is to provide a summary of the paper by providing bullet points which summarise the paper. 

    It should be exact three bullet points which summarise the paper. Return your response in JSON format where the keys are the bullet points and the values are the summaries of the bullet points as following:

    {{
    "bullet_point_1": "content",
    "bullet_point_2": "content",
    "bullet_point_3": "content"
    }}

    Here is the text of the paper:

    {text}
    """

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
    )

    summary = completion.choices[0].message.content
    return summary

def add_text_to_image(background_path, title, text_content, publish_date, output_path="output.jpg", scale_factor=2, offset=20):
    with Image.open(background_path) as img:
        width, height = img.size
        background = img.resize((width * scale_factor, height * scale_factor), Image.LANCZOS)
    
    draw = ImageDraw.Draw(background)

    title_font = ImageFont.truetype("fonts/Inika-Regular.ttf", 35 * scale_factor)
    content_font = ImageFont.truetype("fonts/Inika-Regular.ttf", 20 * scale_factor)
    date_font = ImageFont.truetype("fonts/Inika-Regular.ttf", 20 * scale_factor)
    arxiv_font = ImageFont.truetype("fonts/Larabieb.ttf", 50 * scale_factor)

    margin = 50 * scale_factor
    max_width = background.width - (2 * margin)

    # Dynamically calculate the width for wrapping the title
    wrapped_title = textwrap.wrap(title, width=int(max_width / (35 * scale_factor * 0.6)))
    y_text = 50 * scale_factor

    for line in wrapped_title:
        bbox = title_font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        x_text = (background.width - line_width) // 2
        draw.text((x_text, y_text), line, font=title_font, fill=(0, 0, 0))
        y_text += line_height + (10 * scale_factor)

    bullet_points = json.loads(text_content)
    total_height = sum(len(textwrap.wrap(value, width=90)) * (25 * scale_factor) + (20 * scale_factor) for value in bullet_points.values())
    y = (background.height - total_height) // 2
    bullet_width = content_font.getbbox("• ")[2]
    max_content_width = max(max(content_font.getbbox(line)[2] for line in textwrap.wrap(value, width=90)) for value in bullet_points.values())
    bullet_start_x = (background.width - max_content_width - bullet_width) // 2

    for value in bullet_points.values():
        wrapped_text = textwrap.wrap(value, width=90)
        
        for i, line in enumerate(wrapped_text):
            if i == 0:
                draw.text((bullet_start_x, y), "•", font=content_font, fill=(0, 0, 0))
                draw.text((bullet_start_x + bullet_width, y), line, font=content_font, fill=(0, 0, 0))
            else:
                draw.text((bullet_start_x + bullet_width, y + (25 * scale_factor * i)), line, font=content_font, fill=(0, 0, 0))
        
        y += (25 * scale_factor * len(wrapped_text)) + (20 * scale_factor)

    date_text = f"Published: {publish_date}"
    date_bbox = date_font.getbbox(date_text)
    date_height = date_bbox[3] - date_bbox[1]
    draw.text((margin, background.height - margin - date_height - offset), date_text, font=date_font, fill=(0, 0, 0))

    arxiv_text = "@arXivGPT"
    arxiv_bbox = arxiv_font.getbbox(arxiv_text)
    arxiv_width = arxiv_bbox[2] - arxiv_bbox[0]
    arxiv_height = arxiv_bbox[3] - arxiv_bbox[1]
    arxiv_x = background.width - margin - arxiv_width
    arxiv_y = background.height - margin - arxiv_height - offset

    pre_x_text = "@ar"
    pre_x_width = arxiv_font.getbbox(pre_x_text)[2]
    draw.text((arxiv_x, arxiv_y), pre_x_text, font=arxiv_font, fill=(0, 0, 0))

    x_text = "X"
    x_width = arxiv_font.getbbox(x_text)[2]
    draw.text((arxiv_x + pre_x_width, arxiv_y), x_text, font=arxiv_font, fill="#B31B1B")

    post_x_text = "ivGPT"
    draw.text((arxiv_x + pre_x_width + x_width, arxiv_y), post_x_text, font=arxiv_font, fill=(0, 0, 0))

    background.save(output_path, quality=95)
    print(f"High-resolution image saved as {output_path}")

def create_image_from_url(arxiv_id, background_path="background.jpg", output_path="output.jpg"):
    paper_info = download_and_extract_paper_info(arxiv_id)
    if paper_info:
        title = paper_info.get("title")
        publish_date = paper_info.get("publish_date")
        full_text = paper_info.get("full_text")
        summary = summarize_text(full_text)
        add_text_to_image(background_path, title, summary, publish_date, output_path)
        twitter_handles = paper_info.get("twitter_handles")
    return output_path, twitter_handles

# Example usage
# if __name__ == "__main__":
#     arxiv_id = "2106.14881"  # Replace with the actual arxiv_id
#     create_image_from_url(arxiv_id)