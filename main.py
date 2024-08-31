from bioarxiv import get_trending_urls

if __name__ == "__main__":
    top_ten_tweets = get_trending_urls()
    print(top_ten_tweets)