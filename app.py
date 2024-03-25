from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, NoSuchAttributeException
from webdriver_manager.chrome import ChromeDriverManager
import time
import anthropic
import json
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
import os

load_dotenv()
nltk.download('vader_lexicon')
nltk.download('punkt')

app = Flask(__name__)

bbc_url = os.getenv('BBC_URL')
section_selector = os.getenv('SECTION_SELECTOR')
article_selector = os.getenv('ARTICLE_SELECTOR')
headline_title_selector = os.getenv('HEADLINE_TITLE_SELECTOR')
description_selector = os.getenv('DESCRIPTION_SELECTOR')
text_block_selector = os.getenv('TEXT_BLOCK_SELECTOR')
main_section_id = os.getenv('MAIN_SECTION_ID')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
claude_model = os.getenv('CLAUDE_MODEL')
summarize_prompt = os.getenv('SUMMARIZE_PROMPT')
relevant_headline_prompt = os.getenv('RELEVANT_HEADLINE_PROMPT')


def get_top_headlines():

    main_headlines = []
    other_news = []
    
    try:
        print("Initializing WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        time.sleep(10)
        driver.get(bbc_url)
        print(f"Page loaded: {bbc_url}")
        
        time.sleep(3)
        
        sections = driver.find_elements(By.CSS_SELECTOR, section_selector)
        print(f"Found {len(sections)} sections to process.")

        for section in sections:
            try:
                section_id = section.get_attribute('data-testid')
                print(f"Processing section: {section_id}")
                article_elements = section.find_elements(By.CSS_SELECTOR, article_selector)

                for article in article_elements:
                    try:
                        headline_data = {
                            'title': article.find_element(By.CSS_SELECTOR, headline_title_selector).text,
                            'description': article.find_element(By.CSS_SELECTOR, description_selector).text if article.find_elements(By.CSS_SELECTOR, description_selector) else "Description not found",
                            'link': article.get_attribute('href')
                        }
                        if headline_data['title'].strip():
                            if section_id == main_section_id:
                                main_headlines.append(headline_data)
                            else:
                                other_news.append(headline_data)
                            print(f"News Extracted: {headline_data['title']}")
                    except Exception as e:
                        print(f"Error processing an article: {e}")
            except Exception as e:
                print(f"Error processing section {section_id}: {e}")
        
        print(f"Extracted {len(main_headlines)} headlines.")
        print(f"Extracted {len(other_news)} other news items.")
        driver.quit()
        print("Closing WebDriver... \n")
    except Exception as e:
        print(f"An error occurred during the scraping process: {e}")        
    
    return {'headlines': main_headlines, 'other_news': other_news}

def save_headlines_to_json(headlines_data):
    with open('headlines_data.json', 'w') as file:
        json.dump(headlines_data, file, indent=4)

def get_article_content(link):
    print(f"\n Getting into link: {link}")
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(link)
    time.sleep(3)
    content = ""
    try:
        text_blocks = driver.find_elements(By.CSS_SELECTOR, text_block_selector)
        content = "\n".join([block.text for block in text_blocks])
    except Exception as e:
        print(f"An error occurred: {e}")
    driver.quit()
    return content

def is_relevant_headline(headlines):
    headlines_titles = [headline["title"] for headline in headlines]
    headlines_prompt = "\n".join(headlines_titles)
    
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = f"{relevant_headline_prompt}\n{headlines_prompt}"
    
    response = client.completions.create(
        prompt=f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        model=claude_model,
        max_tokens_to_sample=1000,
    )
    
    print(f"\n Response of the prompt: {response.completion}")

    lines = response.completion.strip().split("\n")
    relevant_titles = [line.split(". ", 1)[-1] for line in lines if line.startswith(("1", "2", "3", "4", "5"))]
    print(f"\n Relevant titles: {relevant_titles}")
    relevant_titles = [relevant_title.strip() for relevant_title in relevant_titles]
    relevant_headlines = [headline for headline in headlines if headline["title"] in relevant_titles]
    print(f"\n Relevant Headlines: {relevant_headlines}")

    return relevant_headlines

def summarize_content(content):
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = f"{summarize_prompt} {content}"
    response = client.completions.create(
        prompt=f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        model=claude_model,
        max_tokens_to_sample=1000,
    )
    summary = response.completion.strip()
    print(f"\n Summary: {summary}")
    return summary

def rank_summaries(summaries):
    ranked_summaries = sorted(summaries, key=lambda x: len(x['summary']), reverse=True)
    return ranked_summaries


def analyze_news(news_list):
    sia = SentimentIntensityAnalyzer()
    
    for news in news_list:
        summary = news['summary']

        sentiment_scores = sia.polarity_scores(summary)
        sentiment = 'positive' if sentiment_scores['compound'] > 0 else 'negative' if sentiment_scores['compound'] < 0 else 'neutral'
        news['sentiment'] = sentiment

        score = score_summary(summary)
        news['score'] = score

    return news_list

def score_summary(summary):
    length_score = min(len(summary.split()) / 100, 1)  # Pontuação baseada no tamanho do resumo
    capitalized_score = sum(1 for char in summary if char.isupper()) / len(summary)  # Pontuação baseada nas letras maiúsculas
    punctuation_score = sum(1 for char in summary if char in ['.', ',', '!', '?']) / len(summary)  # Pontuação baseada na pontuação

    # Média ponderada dos critérios de pontuação
    score = (length_score * 0.5) + (capitalized_score * 0.3) + (punctuation_score * 0.2)

    return round(score, 2)

@app.route('/api/headlines', methods=['GET'])
def get_headlines():
    headlines = get_top_headlines()
    save_headlines_to_json(headlines)
    return jsonify(headlines)

@app.route('/api/relevant-headlines', methods=['GET'])
def get_relevant_headlines():
    headlines = get_top_headlines()
    relevant_headlines = is_relevant_headline(headlines['headlines'])
    return jsonify(relevant_headlines)

@app.route('/api/summaries', methods=['GET'])
def get_summaries():
    headlines = get_top_headlines()
    relevant_headlines = is_relevant_headline(headlines['headlines'])
    summaries = []
    for headline in relevant_headlines:
        content = get_article_content(headline['link'])
        summary = summarize_content(content)
        summaries.append({
            'title': headline['title'],
            'description': headline['description'],
            'link': headline['link'],
            'summary': summary
        })
    ranked_by_length_summaries = rank_summaries(summaries)
    result = {
        'top_ranked_bbc_news': ranked_by_length_summaries
    }
    with open('news_summaries.json', 'w') as f:
        json.dump(result, f, indent=4)
    return jsonify(result)

@app.route('/api/analyzed-news', methods=['GET'])
def get_analyzed_news():
    headlines = get_top_headlines()
    relevant_headlines = is_relevant_headline(headlines['headlines'])
    summaries = []
    for headline in relevant_headlines:
        content = get_article_content(headline['link'])
        summary = summarize_content(content)
        summaries.append({
            'title': headline['title'],
            'description': headline['description'],
            'link': headline['link'],
            'summary': summary
        })
    ranked_by_length_summaries = rank_summaries(summaries)
    analyzed_news = analyze_news(ranked_by_length_summaries)
    result_analyzed = {
        'top_ranked_bbc_news_with_score': analyzed_news
    }
    with open('news_summaries_scored.json', 'w') as f:
        json.dump(result_analyzed, f, indent=4)
    return jsonify(result_analyzed)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)