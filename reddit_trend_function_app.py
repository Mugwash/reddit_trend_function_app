import azure.functions as func # type: ignore
import datetime
import json
import logging
import praw # type: ignore
import re
import nltk # type: ignore
from nltk.corpus import stopwords # type: ignore
from collections import Counter
import csv
import os
import uuid
from openai import AzureOpenAI # type: ignore
from azure.cosmos import CosmosClient, exceptions # type: ignore

app = func.FunctionApp()
'''
Main function that runs every day at 6 AM UTC.
'''
@app.schedule(schedule="0 0 6 * * *", arg_name="mytimer", run_on_startup=True)
async def main(mytimer: func.TimerRequest) -> None:
    trends_data = GetTrends()
    trending_words = trends_data.get("trending_words", [])
    CleanTrendsAI(trending_words)
    add_trends_to_db(trending_words)
'''
GetTrends() initialises reddit clients fetches trending words from the Reddit client from product based subreddits 
e.g. WhatShouldIBuy, downloads stopwords, removes stopwords from the trending words list, and returns a list of trending words.
'''
def GetTrends():
    logging.info('Python timer trigger function processed a request.')

    # Ensure NLTK uses bundled stopwords directory
    nltk.data.path.append('./nltk_data')

    reddit = praw.Reddit(
    )

    subreddits = ['buyitforlife', 'Frugal', 'findareddit', 'ifyoulikeblank']
    num_posts = 250
    titles = []

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            titles.extend([post.title for post in subreddit.hot(limit=num_posts)])
        except Exception as e:
            logging.warning(f"Error fetching subreddit '{subreddit_name}': {e}")

    # Load stopwords
    try:
        stop_words = set(stopwords.words('english'))
    except LookupError as e:
        logging.error("Stopwords not found. Ensure nltk_data is deployed with the function.")
        stop_words = set()

    product_keywords = set()
    try:
        with open('food_products_list.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                for keyword in row:
                    keyword = keyword.strip().lower()
                    if keyword and keyword not in stop_words:
                        product_keywords.add(keyword)
    except Exception as e:
        logging.error(f"Error reading food_products_list.csv: {e}")

    words = [
        word.lower() for title in titles for word in re.findall(r'\b\w+\b', title)
        if word.lower() in product_keywords
    ]

    word_counts = Counter(words)
    trending = word_counts.most_common(50)

    return {"trending_words": trending}
'''
CleanTrendsAI(trending_words) uses Azure OpenAI to clean the trending words list by removing non-physical product in a comma seperated list which is then used
to remove words from the original trending words list if they are not in the cleaned list.
The cleaned list is then returned.
'''
def CleanTrendsAI(trending_words):
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
    model_name = os.getenv('AZURE_OPENAI_MODEL_NAME')
    client = AzureOpenAI(
        api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a data cleaning assistant, please return a list of inherently physical products regularly sold online(please ensure it's not a category of items), the list should be separated by commas without additional comments.",
            },
            {
                "role": "user",
                "content": f"{trending_words}",
            }
        ],
        max_tokens=2048,
        temperature=1.0,
        top_p=1.0,
        model=model_name
    )
    # Extract the text response from the OpenAI API
    ai_response = response.choices[0].message.content.strip()
    # Split the response into a list of words, assuming comma separation
    cleaned_words = [word.strip() for word in ai_response.split(',') if word.strip()]
    # Remove any trends not present in cleaned_words
    cleaned_words_set = set(cleaned_words)
    trending_words[:] = [word for word in trending_words if word[0] in cleaned_words_set]
'''
add_trends_to_db(trending_words) adds the trending words to the Cosmos DB database.
It first checks if the word is already in the database, if it is, it updates the date and word count.
If it is not, it creates a new item in the database with the word, date, and word count.
'''
def add_trends_to_db(trending_words):

    # Initialize Cosmos client
    endpoint = os.getenv('COSMOS_DB_ENDPOINT')
    key = os.getenv('COSMOS_DB_KEY')

    try:
        client = CosmosClient(endpoint, key)
        database_name = os.getenv('COSMOS_DB_DATABASE_NAME')
        container_name = os.getenv('COSMOS_DB_CONTAINER_NAME')

        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)

        # Verify connection
        list(container.read_all_items(max_item_count=1))
        logging.info("Connected to Cosmos DB.")
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        return False

    if not trending_words:
        logging.info("No trending words found.")
        return True

    # Fetch existing items using lowercase 'product_name'
    existing_names = set()
    existing_items = {}

    try:
        for item in container.read_all_items():
            existing_names.add(item['product_name'].lower())
            existing_items[item['product_name'].lower()] = item
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Error reading items from Cosmos DB: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False
    # Add new items to the database
    for word in trending_words:
        word = word[0].lower()
        if word not in existing_names:
            new_item = {
                "id": str(uuid.uuid4()),
                "product_name": word,
                "date": datetime.datetime.now(datetime.timezone.utc).strftime("%d,%m,%Y %H:%M:%S"),
                #add the word count to the new item
                "word_count": dict(trending_words).get(word, 0),
                "description": None,
                "email_text": None,
                "social_media_post": None,
                "product_img_prompt": None,
                "advert_img_prompt": None,
                "product_img_url": None,
                "advert_img_url": None
            }
            try:
                container.create_item(body=new_item)
            except exceptions.CosmosHttpResponseError as e:
                logging.error(f"Error creating item in Cosmos DB: {e}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
        else:
            # Update the 'date' field and word_count of the existing item
            existing_item = existing_items[word]
            existing_item['date'] = datetime.datetime.now(datetime.timezone.utc).strftime("%d,%m,%Y %H:%M:%S")
            # Find the count for the current word in trending_words
            word_count = dict(trending_words).get(word, 0)
            existing_item['word_count'] = word_count
            try:
                container.replace_item(item=existing_item['id'], body=existing_item)
            except exceptions.CosmosHttpResponseError as e:
                logging.error(f"Error updating item in Cosmos DB: {e}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
###


