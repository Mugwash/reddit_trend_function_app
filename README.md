
# 📦 Reddit Product Trends Tracker

**Automated Azure Function to extract, clean, and store trending product keywords from Reddit using NLP and Azure OpenAI.**

## 🔧 Overview

This project is a scheduled Azure Function that runs daily at **6 AM UTC** to:

1. **Scrape Reddit** for trending product-related keywords from curated subreddits.
2. **Clean and filter** the keywords using NLTK and Azure OpenAI to retain only physical products.
3. **Store the results** in Azure Cosmos DB, updating existing entries or creating new ones.

## 🚀 Features

- ⏰ **Scheduled Execution**: Runs daily using Azure Timer Trigger.
- 🧠 **NLP Processing**: Uses NLTK to remove stopwords and extract relevant keywords.
- 🤖 **AI Filtering**: Leverages Azure OpenAI to filter out non-physical or irrelevant terms.
- ☁️ **Cloud Storage**: Saves trending data in Azure Cosmos DB with metadata like word count and timestamp.
- 🔄 **Smart Updates**: Updates existing entries or inserts new ones based on keyword presence.

## 📂 Subreddits Monitored

- `buyitforlife`
- `Frugal`
- `findareddit`
- `ifyoulikeblank`

## 🛠️ Tech Stack

- **Azure Functions (Python)**
- **Azure OpenAI**
- **Azure Cosmos DB**
- **Reddit API (via PRAW)**
- **NLTK for NLP**
- **CSV-based keyword filtering**

## 📁 File Structure

- `main()` – Entry point for the scheduled function.
- `GetTrends()` – Scrapes Reddit and extracts trending keywords.
- `CleanTrendsAI()` – Uses Azure OpenAI to filter out non-physical products.
- `add_trends_to_db()` – Inserts or updates keywords in Cosmos DB.

## 📌 Environment Variables

Ensure the following environment variables are set:

- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_MODEL_NAME`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `COSMOS_DB_ENDPOINT`
- `COSMOS_DB_KEY`
- `COSMOS_DB_DATABASE_NAME`
- `COSMOS_DB_CONTAINER_NAME`
