import asyncio
import time
from bioarxiv import get_trending_urls
from ai import create_image_from_paper_info
from post import post_tweet


async def main():
    top_ten_tweets = await get_trending_urls()  # Await the asynchronous function
    print("top_ten_tweets", top_ten_tweets)

    num_tweets = len(top_ten_tweets)
    total_time_seconds = 5 * 60 * 60 + 30 * 60  # 5 hours and 30 minutes in seconds
    sleep_interval = total_time_seconds / num_tweets if num_tweets > 0 else 0

    for tweet in top_ten_tweets:
        paper_info = {
            "url": tweet["url"],
            "tweet_count": tweet["tweet_count"],
            "abstract": tweet["abstract"],
            "title": tweet["title"],
            "subject_area": tweet["subject_area"],
        }

        output_path, twitter_handles = create_image_from_paper_info(paper_info)

        # Post the tweet with the image
        post_tweet(paper_info["title"], paper_info["url"], output_path, twitter_handles)

        print(f"Image saved at: {output_path}")
        print(f"Twitter handles: {twitter_handles}")

        # Sleep for the calculated interval
        await asyncio.sleep(sleep_interval)


# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())  # Run the main function