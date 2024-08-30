import asyncio
from playwright.async_api import async_playwright, TimeoutError
import nest_asyncio
from bs4 import BeautifulSoup
from datetime import date, timedelta

# Function to generate the Hugging Face URL
def generate_huggingface_url():
    yesterday = date.today() - timedelta(days=1)
    url = f"https://huggingface.co/papers?date={yesterday.year}-{yesterday.month:02d}-{yesterday.day:02d}"
    return url

# Async function to fetch the HTML content
async def fetch_papers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        huggingface_url = generate_huggingface_url()
        await page.goto(huggingface_url)
        html_content = await page.content()
        papers = parse_html_content(html_content)
        return papers

# Function to parse the HTML content and extract paper details
def parse_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    papers = []
    for container in soup.find_all('div', class_='from-gray-50-to-white -mt-2 flex bg-gradient-to-b px-6 pb-6 pt-8'):
        link = container.find('a', class_='line-clamp-3 cursor-pointer text-balance')
        if link:
            href = link.get('href')
            arxiv_url = f"https://arxiv.org/pdf{href[href.rfind('/'):]}.pdf"
            paper_name = link.text.strip()
            upvotes_div = container.find('div', class_='shadow-alternate').find('div', class_='leading-none')
            if upvotes_div:
                upvotes = upvotes_div.text.strip()
                papers.append((arxiv_url, paper_name, upvotes))
        else:
            print("Link not found in this container.")
    return papers

# Ensure nest_asyncio is applied
nest_asyncio.apply()