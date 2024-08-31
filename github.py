import requests
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


def extract_emails(content):
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    prompt = f"""
    You are given a research paper. Extract all the emails of authors from the paper if they are available.

    Return your response in JSON format as following:

    {{
        "emails": ["email1", "email2", "email3"]
    }}

    in the case there are no emails, return an empty list.

    here is the paper:

    {content}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(response.choices[0].message.content)["emails"]


def check_github_email(email):
    url = f"https://api.github.com/search/users?q={email}+in:email+type:user"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data["items"]
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def get_profile_data(user_url):
    response = requests.get(user_url)
    if response.status_code == 200:
        profile_data = response.json()
        return profile_data.get("twitter_username", None)
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def process_paper(content):
    emails = extract_emails(content)
    twitter_handles = []

    if not emails:
        return twitter_handles

    for email in emails:
        users = check_github_email(email)

        if users:
            for user in users:
                github_profile_url = user["url"]
                twitter_handle = get_profile_data(github_profile_url)
                if twitter_handle:
                    twitter_handles.append(twitter_handle)
    return twitter_handles
