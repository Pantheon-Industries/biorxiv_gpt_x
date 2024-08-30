import asyncio
import time
from huggingface import fetch_papers
from create_image import create_image_from_url
from post import post_tweet

def extract_arxiv_id(url):
    # Extract the arxiv ID from the URL
    return url.split('/')[-1].replace('.pdf', '')

async def main():
    papers = await fetch_papers()
    num_papers = len(papers)
    total_time_seconds = 5 * 60 * 60 + 30 * 60  # 5 hours and 30 minutes in seconds
    sleep_interval = total_time_seconds / num_papers if num_papers > 0 else 0
    for paper in papers:
        url, title, _ = paper  # Adjust based on the actual structure of the paper tuple
        arxiv_id = extract_arxiv_id(url)
        output_path, twitter_handles = create_image_from_url(arxiv_id)
        print(f"Image created at: {output_path}")
        # Post the tweet
        post_tweet(title, url, output_path, twitter_handles)
        # Sleep for the calculated interval
        await asyncio.sleep(sleep_interval)

if __name__ == "__main__":
    asyncio.run(main())