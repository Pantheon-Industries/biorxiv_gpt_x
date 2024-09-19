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


yesterday_date = get_yesterday_date()
print("Yesterday's date in ET:", yesterday_date)


# Function to iterate through biorxiv pages and collect paper URLs
async def iterate_biorxiv_pages():
    page_data = []
    page_number = 0
    max_concurrent_pages = 5  # Number of pages to open concurrently

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()

        async def fetch_page(page_num):
            url = f"https://www.biorxiv.org/content/early/recent?page={page_num}"
            print(url)
            page = await context.new_page()

            retries = 3  # Number of retries for the goto call
            for attempt in range(retries):
                try:
                    await page.goto(url)
                    break  # Exit the retry loop if successful
                except Exception as e:
                    print(f"Error navigating to {url}: {e}")
                    if attempt < retries - 1:
                        print(f"Retrying {url} (attempt {attempt + 1}/{retries})")
                    else:
                        print(f"Failed to navigate to {url} after {retries} attempts")
                        await page.close()
                        return []  # Return empty if all retries fail

            # Get the date based on the selector
            date_element = await page.query_selector(
                "#block-system-main > div > div > div > div:nth-child(2) > div:nth-child(1) > div > div > div > div > div:nth-child(1) > h3"
            )
            if not date_element:
                await page.close()
                return []  # Return empty if no date element found
            date_text = await date_element.inner_text()

            # Reformat the date to match the format of our yesterday_date
            page_date = datetime.strptime(date_text.strip(), "%B %d, %Y").strftime("%Y-%m-%d")

            print("page date: ", page_date)

            # Close the page after processing
            await page.close()
            return page_date

        while True:
            tasks = [fetch_page(page_number + i) for i in range(max_concurrent_pages)]
            results = await asyncio.gather(*tasks)

            # Process results
            for result in results:
                if result and result < yesterday_date:
                    return page_data  # Exit if any page date is older than yesterday
                if result and result == yesterday_date:
                    page_data.append(result)

            page_number += max_concurrent_pages  # Move to the next batch of pages

        await browser.close()
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
            await page.goto(
                url, timeout=60000
            )  # Wait up to 60 seconds for the page to load
            await page.wait_for_selector(
                "#count_twitter", timeout=60000
            )  # Wait up to 60 seconds for the element
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

    soup = BeautifulSoup(content, "html.parser")

    # Extract the date from the page
    date_element = soup.select_one(
        "#block-system-main > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(3) > div"
    )
    if date_element:
        date_text = date_element.get_text(strip=True)
        # Remove the 'Posted\xa0' prefix if it exists
        if date_text.startswith("Posted\xa0"):
            date_text = date_text.replace("Posted\xa0", "")
        # Remove the period at the end of the date string
        if date_text.endswith("."):
            date_text = date_text[:-1]
        try:
            page_date = datetime.strptime(date_text, "%B %d, %Y").strftime("%Y-%m-%d")
            print(f"Parsed page date: {page_date}")  # Debug print
        except ValueError as e:
            print(f"Error parsing date on {url}: {e}")
            return

        # Check if the date matches the target date
        if page_date == yesterday_date:
            print(f"Date matches target date: {page_date}")  # Debug print

            # Extract the number of tweets using a CSS selector
            tweet_element = soup.select_one("#count_twitter")
            tweet_count = tweet_element.get_text(strip=True) if tweet_element else "0"
            print(f"Extracted tweet count: {tweet_count}")  # Debug print

            # Extract the abstract
            abstract_element = soup.select_one("#p-3")
            abstract = (
                abstract_element.get_text(strip=True) if abstract_element else "N/A"
            )
            print(f"Extracted abstract: {abstract}")  # Debug print

            # Extract the title
            title_element = soup.select_one("#page-title")
            title = title_element.get_text(strip=True) if title_element else "N/A"
            print(f"Extracted title: {title}")  # Debug print

            # Extract the subject area
            subject_area_elements = soup.select(
                "#block-system-main > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(11) > div > div > div > ul > li > span > a"
            )
            subject_area = (
                ", ".join(
                    [element.get_text(strip=True) for element in subject_area_elements]
                )
                if subject_area_elements
                else "N/A"
            )
            print(f"Extracted subject area: {subject_area}")  # Debug print

            # Create a dictionary with the extracted data
            tweet_data = {
                "url": url,
                "tweet_count": tweet_count,
                "abstract": abstract,
                "title": title,
                "subject_area": subject_area,
            }

            # Add the dictionary to the list
            tweet_data_list.append(tweet_data)
        else:
            print(f"Date does not match target date on {url}")
    else:
        print(f"Date element not found on {url}")


# Main asynchronous function to handle multiple requests in batches
async def main(urls, batch_size=50, delay=5):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            print(f"Processing batch: {batch}")
            context = await browser.new_context()
            tasks = [fetch_and_parse(url, context) for url in batch]
            await asyncio.gather(*tasks)
            await context.close()
            await asyncio.sleep(delay)  # Add a delay between batches

        await browser.close()


# Function to find the top ten URLs with the most tweets
def get_top_ten_tweets(tweet_data_list):
    # Sort the list in descending order based on tweet count
    sorted_tweets = sorted(
        tweet_data_list, key=lambda x: int(x["tweet_count"]), reverse=True
    )
    # Select the top ten URLs with the most tweets
    top_ten_tweets = sorted_tweets[:10]
    return top_ten_tweets


# Main function to run the entire process
async def get_trending_urls():
    urls = await iterate_biorxiv_pages()
    asyncio.run(main(urls))
    return get_top_ten_tweets(tweet_data_list)


if __name__ == "__main__":
    top_ten_tweets = get_trending_urls()
    print("Top ten URLs with the most tweets:")
    for data in top_ten_tweets:
        print(
            f"URL: {data['url']}, Tweets: {data['tweet_count']}, Title: {data['title']}, Abstract: {data['abstract']}, Subject Area: {data['subject_area']}"
        )