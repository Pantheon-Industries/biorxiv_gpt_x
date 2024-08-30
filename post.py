import tweepy
import os

def post_tweet(title, url, image_path, twitter_handles):
    # Twitter API credentials
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET_KEY")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

    # Authenticate with Twitter using API v1.1
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)

    # Create API object for media upload
    api = tweepy.API(auth)

    # Create Client object for posting the tweet (v2) with bearer token
    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    try:
        # Upload image
        media = api.media_upload(image_path)

        # Print media ID
        print("Media ID:", media.media_id)

        # Prepare tweet text
        tweet_text = f"🏷️:{title}\n\n"
        
        # Add Twitter handles if the list is not empty
        if twitter_handles:
            formatted_handles = " ".join([f"@{handle}" for handle in twitter_handles])
            tweet_text += f"👤:{formatted_handles}\n\n"
        
        tweet_text += f"🔗:{url}"

        # Create tweet with uploaded image using Client (v2)
        tweet = client.create_tweet(text=tweet_text, media_ids=[media.media_id])

        print("Tweet posted successfully! Tweet ID:", tweet.data['id'])

    except tweepy.Forbidden as e:
        print("Error posting tweet:", e)
    except Exception as e:
        print("An error occurred:", e)