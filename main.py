import asyncio
import time
from bioarxiv import get_trending_urls
from ai import create_image_from_paper_info
from post import post_tweet


async def main():
    top_ten_tweets = await get_trending_urls()  # Await the asynchronous function
    print("top_ten_tweets", top_ten_tweets)

    for tweet in top_ten_tweets:
        paper_info = {
            "url": tweet["url"],
            "tweet_count": tweet["tweet_count"],
            "abstract": tweet["abstract"],
            "title": tweet["title"],
            "subject_area": tweet["subject_area"],
        }

        output_path = create_image_from_paper_info(paper_info)

        # Post the tweet with the image
        post_tweet(paper_info["title"], paper_info["url"], output_path)

        print(f"Image saved at: {output_path}")
        #print(f"Twitter handles: {twitter_handles}")

# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())  # Run the main function