from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import nest_asyncio

# Apply the nest_asyncio patch
nest_asyncio.apply()

# Function to get date from yesterday ET time
def get_yesterday_date():
    eastern = pytz.timezone('US/Eastern')
    yesterday = datetime.now(eastern) - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

yesterday_date = get_yesterday_date()
print("Yesterday's date in ET:", yesterday_date)

# Function to iterate through biorxiv pages and collect paper URLs
def iterate_biorxiv_pages():
    page_data = []
    page_number = 0
    while True:
        url = f"https://www.biorxiv.org/content/early/recent?page={page_number}"
        print(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get the date based on the X path
        date_element = soup.select_one('#block-system-main > div > div > div > div:nth-child(2) > div:nth-child(1) > div > div > div > div > div:nth-child(1) > h3')
        if not date_element:
            break
        date_text = date_element.get_text(strip=True)
        
        # Reformat the date to match the format of our yesterday_date
        page_date = datetime.strptime(date_text, '%B %d, %Y').strftime('%Y-%m-%d')

        print("page date: ", page_date)
        
        # Check if the date is older than the target date
        if page_date < yesterday_date:
            break
        
        # Skip the page if the date is newer than the target date
        if page_date > yesterday_date:
            page_number += 1
            continue

        # Extract all the URLs from the page
        article_blocks = soup.find_all('div', class_='highwire-cite highwire-cite-highwire-article highwire-citation-biorxiv-article-pap-list-overline clearfix')
        
        for block in article_blocks:
            title_element = block.find('span', class_='highwire-cite-title')
            if title_element:
                link_element = title_element.find('a', class_='highwire-cite-linked-title')
                if link_element and 'href' in link_element.attrs:
                    paper_url = "https://www.biorxiv.org" + link_element['href']
                    page_data.append(paper_url)
        
        page_number += 1
    return page_data

# Initialize an empty list to store the dictionaries
tweet_data_list = []

# Asynchronous function to fetch and parse a single URL
async def fetch_and_parse(url, context):
    print(f"Fetching URL: {url}")
    retries = 3
    for attempt in range(retries):
        try:
            page = await context.new_page()
            await page.goto(url, timeout=60000)  # Wait up to 60 seconds for the page to load
            await page.wait_for_selector('#count_twitter', timeout=60000)  # Wait up to 60 seconds for the element
            content = await page.content()
            await page.close()
            break  # Exit the retry loop if successful
        except PlaywrightTimeoutError as e:
            print(f"Timeout error on {url}: {e}")
        except Exception as e:
            print(f"Error on {url}: {e}")
        if attempt < retries - 1:
            print(f"Retrying {url} (attempt {attempt + 1}/{retries})")
        else:
            print(f"Failed to fetch {url} after {retries} attempts")
            return

    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract the date from the page
    date_element = soup.select_one('#block-system-main > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(3) > div')
    if date_element:
        date_text = date_element.get_text(strip=True)
        # Remove the 'Posted\xa0' prefix if it exists
        if date_text.startswith('Posted\xa0'):
            date_text = date_text.replace('Posted\xa0', '')
        # Remove the period at the end of the date string
        if date_text.endswith('.'):
            date_text = date_text[:-1]
        try:
            page_date = datetime.strptime(date_text, '%B %d, %Y').strftime('%Y-%m-%d')
            print(f"Parsed page date: {page_date}")  # Debug print
        except ValueError as e:
            print(f"Error parsing date on {url}: {e}")
            return
        
        # Check if the date matches the target date
        if page_date == yesterday_date:
            print(f"Date matches target date: {page_date}")  # Debug print
            # Extract the number of tweets using a CSS selector
            tweet_element = soup.select_one('#count_twitter')
            print("tweet_element: ", tweet_element)  # Debug print
            if tweet_element:
                tweet_count = tweet_element.get_text(strip=True)
                print(f"Extracted tweet count: {tweet_count}")  # Debug print
                
                # Create a dictionary with the URL as key and tweet count as value
                tweet_data = {url: tweet_count}
                
                # Add the dictionary to the list
                tweet_data_list.append(tweet_data)
            else:
                print(f"Tweet element not found on {url}")
        else:
            print(f"Date does not match target date on {url}")
    else:
        print(f"Date element not found on {url}")

# Main asynchronous function to handle multiple requests in batches
async def main(urls, batch_size=50, delay=5):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            print(f"Processing batch: {batch}")
            context = await browser.new_context()
            tasks = [fetch_and_parse(url, context) for url in batch]
            await asyncio.gather(*tasks)
            await context.close()
            await asyncio.sleep(delay)  # Add a delay between batches
        
        await browser.close()

# Function to find the top ten URLs with the most tweets
def get_top_ten_tweets(tweet_data_list):
    top_ten_tweets = []
    
    # Flatten the list of dictionaries into a single list of tuples (url, tweet_count)
    flattened_tweets = [(url, int(tweet_count)) for data in tweet_data_list for url, tweet_count in data.items()]
    
    # Sort the list in descending order based on tweet count
    sorted_tweets = sorted(flattened_tweets, key=lambda x: x[1], reverse=True)
    
    # Select the top ten URLs with the most tweets
    top_ten_tweets = sorted_tweets[:10]
    
    return top_ten_tweets

# Main function to run the entire process
def get_trending_urls():
    urls = iterate_biorxiv_pages()
    asyncio.run(main(urls))
    return get_top_ten_tweets(tweet_data_list)

if __name__ == "__main__":
    top_ten_tweets = get_trending_urls()
    print("Top ten URLs with the most tweets:")
    for url, tweet_count in top_ten_tweets:
        print(f"URL: {url}, Tweets: {tweet_count}")