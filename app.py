from flask import Flask, render_template, request
import tweepy
import os
from dotenv import load_dotenv
import time
import logging

# Load environment variables
load_dotenv(dotenv_path="keys.env")

app = Flask(__name__)

# Twitter API v2 Configuration
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Initialize Twitter Client
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to handle rate limits and retry logic
def retry_on_rate_limit(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except tweepy.TooManyRequests as e:
            # Wait until the rate limit resets
            reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 60))
            wait_time = reset_time - time.time()
            logging.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds...")
            time.sleep(max(wait_time, 0))
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

# Route for the home page
@app.route('/')
def home():
    query = request.args.get('query', '#AI')  # Default to #AI if no query parameter is provided
    try:
        # Use retry logic to fetch recent tweets
        response = retry_on_rate_limit(
            client.search_recent_tweets,
            query=query,
            max_results=10,  # Twitter API requires at least 10 results for this query
            tweet_fields=["created_at", "text", "attachments"],
            expansions=["attachments.media_keys"],
            media_fields=["url", "preview_image_url"]
        )

        # Check if data is available
        if response and response.data:
            media = {m.media_key: m for m in response.includes.get('media', [])}
            tweets = []
            for tweet in response.data:
                tweet_data = {
                    "tweet": tweet.text,
                    "date": tweet.created_at,
                    "url": f"https://twitter.com/user/status/{tweet.id}",
                    "media": []
                }
                if tweet.attachments and tweet.attachments.get('media_keys'):
                    for media_key in tweet.attachments.get('media_keys'):
                        if media_key in media:
                            media_url = media[media_key].url or media[media_key].preview_image_url
                            tweet_data["media"].append(media_url)
                tweets.append(tweet_data)
        else:
            tweets = [{"tweet": f"No tweets found for {query}", "date": None, "url": None, "media": []}]

        # Render the tweets on the web page
        return render_template('index.html', tweets=tweets, query=query)
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")
        return f"Error: {e}"

if __name__ == '__main__':
    app.run(debug=True)