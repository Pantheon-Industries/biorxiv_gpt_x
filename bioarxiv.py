# /Users/maxhager/projects_2024/bioarxiv_gpt_x/test.py

from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
import nest_asyncio

# Apply the nest_asyncio patch
nest_asyncio.apply()

# Function to get date from yesterday ET time
def get_yesterday_date():
    eastern = pytz.timezone("US/Eastern")
    yesterday = datetime.now(eastern) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

# Construct the URL using yesterday_date
def construct_url():
    yesterday_date = get_yesterday_date()
    base_url = "https://www.biorxiv.org/search/jcode%3Abiorxiv"
    limit_from_to = f"limit_from%3A{yesterday_date}%20limit_to%3A{yesterday_date}"
    num_results = "numresults%3A75"
    sort_order = "sort%3Arelevance-rank"
    format_result = "format_result%3Astandard"
    complete_url = f"{base_url}%20{limit_from_to}%20{num_results}%20{sort_order}%20{format_result}"
    return complete_url

# Function to extract pagination URLs
async def extract_pagination_urls(complete_url):
    pagination_urls = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()
        
        try:
            await page.goto(complete_url)
            await page.wait_for_load_state('networkidle', timeout=20000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            pagination_div = soup.find('div', class_='highwire-list page-group-items item-list')
            if pagination_div:
                pagination_links = pagination_div.find('ul', class_='pager pager-items')
                pagination_urls.append(complete_url)
                for link in pagination_links.find_all('a'):
                    href = link.get('href')
                    if href and not href.startswith('http'):
                        href = f"https://www.biorxiv.org{href}"
                    pagination_urls.append(href)
        except PlaywrightTimeoutError:
            print("Navigation timed out. Taking a screenshot...")
            await page.screenshot(path='timeout_screenshot.png')  # Save screenshot on timeout
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            await page.screenshot(path='error_screenshot.png')  # Save screenshot on other errors
            return []
        finally:
            await browser.close()
    return pagination_urls

# Function to open pagination URLs and extract DOI links
async def open_pagination_urls(pagination_urls):
    all_doi_urls = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()

        for url in pagination_urls:
            try:
                await page.goto(url)
                await page.wait_for_load_state('networkidle', timeout=20000)
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                doi_elements = soup.find_all('span', class_='highwire-cite-metadata-doi')
                for doi_element in doi_elements:
                    doi_link = doi_element.get_text(strip=True).replace("doi:", "").strip()
                    if doi_link:
                        all_doi_urls.append(doi_link)
            except PlaywrightTimeoutError:
                print(f"Navigation to {url} timed out.")
            except Exception as e:
                print(f"An error occurred while navigating to {url}: {e}")

        await browser.close()
    return all_doi_urls

# Function to get top ten tweets
def get_top_ten_tweets(tweet_data_list):
    sorted_tweets = sorted(tweet_data_list, key=lambda x: int(x["tweet_count"]), reverse=True)
    return sorted_tweets[:10]

# Function to fetch and parse tweet data
async def fetch_and_parse(url, context, yesterday_date, tweet_data_list):
    print(f"Fetching URL: {url}")
    page = await context.new_page()
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("#count_twitter", timeout=60000)
        content = await page.content()
    except PlaywrightTimeoutError:
        print(f"Timeout error while fetching {url}. Skipping this paper.")
        return  # Skip this paper
    except Exception as e:
        print(f"An error occurred while navigating to {url}: {e}")
        return  # Skip this paper
    finally:
        await page.close()

    soup = BeautifulSoup(content, "html.parser")
    date_element = soup.select_one("#block-system-main > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(3) > div")
    if date_element:
        date_text = date_element.get_text(strip=True).replace("Posted\xa0", "").rstrip('.')
        try:
            page_date = datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")
            if page_date == yesterday_date:
                tweet_element = soup.select_one("#count_twitter")
                tweet_count = tweet_element.get_text(strip=True) if tweet_element else "0"
                abstract_element = soup.select_one("#p-3")
                abstract = abstract_element.get_text(strip=True) if abstract_element else "N/A"
                title_element = soup.select_one("#page-title")
                title = title_element.get_text(strip=True) if title_element else "N/A"
                subject_area_elements = soup.select("#block-system-main > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(11) > div > div > div > ul > li > span > a")
                subject_area = ", ".join([element.get_text(strip=True) for element in subject_area_elements]) if subject_area_elements else "N/A"
                tweet_data = {
                    "url": url,
                    "tweet_count": tweet_count,
                    "abstract": abstract,
                    "title": title,
                    "subject_area": subject_area,
                }
                tweet_data_list.append(tweet_data)
        except ValueError as e:
            print(f"Error parsing date on {url}: {e}")


async def main(all_doi_urls, yesterday_date, batch_size=50, delay=5):
    tweet_data_list = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        for i in range(0, len(all_doi_urls), batch_size):
            batch = all_doi_urls[i : i + batch_size]
            print(f"Processing batch: {batch}")
            tasks = [fetch_and_parse(url, context, yesterday_date, tweet_data_list) for url in batch]
            await asyncio.gather(*tasks)
            await asyncio.sleep(delay)

        await browser.close()
    return get_top_ten_tweets(tweet_data_list)

# Main function to run the entire process
async def get_trending_urls():
    complete_url = construct_url()
    pagination_urls = await extract_pagination_urls(complete_url)
    all_doi_urls = await open_pagination_urls(pagination_urls)
    yesterday_date = get_yesterday_date()
    return await main(all_doi_urls, yesterday_date)

# Entry point for the script
if __name__ == "__main__":
    top_ten_tweets = asyncio.run(get_trending_urls())
    print("Top ten URLs with the most tweets:")
    for data in top_ten_tweets:
        print(f"URL: {data['url']}, Tweets: {data['tweet_count']}, Title: {data['title']}, Abstract: {data['abstract']}, Subject Area: {data['subject_area']}")