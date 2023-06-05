#Načítanie všetkých potrebných knižníc
import os
from flask import Flask, request, jsonify
import re
import google.auth
import requests
import nltk
import numpy as np
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
import random
import json
import requests
import urllib.parse
import openai_secret_manager
import openai
from dotenv import load_dotenv

# Nastavenie environmentálnej premennej pre poverenia Google API
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\olive\OneDrive\Desktop\adlerka\programovanie\chatbot\chatbot-1682015178882-f479b2ab2de1.json'

# Vytvorenie klienta pre Google vyhľadávanie
def create_google_search_client():
    credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/customsearch'])
    return build('customsearch', 'v1', credentials=credentials)

# Vyhľadanie v Google pre daný dotaz a vrátenie výsledkov pomocou knižnice requests
def search(query):
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'q': query,
        'cx': '72bf95bd9773c4858', 
        'key': os.getenv("AIzaSyCRBHQCm1OLF7pocJuHlC3JYy9MGZhHV70"), 
        'fields': 'items(link,snippet)' # Získať iba link a snippet z výsledkov vyhľadávania
    }
    response = requests.get(url, params=params).json()
    results = response.get('items', []) # Získanie výsledkov vyhľadávania zo spracovanej odpovede
    return results

# Extrahovanie celých viet zo výsledkov hľadania
def extract_text_from_results(search_results):
    sentences = []
    if search_results is not None and len(search_results) > 0:
        for result in search_results:
            if 'snippet' in result:
                # Extrahovanie viet z textového snippetu
                snippet = result['snippet']
                snippet = re.sub('<[^>]+>', '', snippet)  # Odstránenie HTML tagov
                snippet = re.sub('\s+', ' ', snippet)  # Nahradenie viacerých medzier jednou medzerou
                for sentence in nltk.sent_tokenize(snippet):
                    sentences.append(sentence)
    return sentences

# Extrahovanie textu z webovej stránky
def extract_text_from_webpage(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Odstránenie script a style tagov
    for script in soup(['script', 'style']):
        script.extract()
    text = soup.get_text()
    # Odstránenie riadkov a nadbytočných medzier
    lines = (line.strip() for line in text.splitlines())
    text = ' '.join(line for line in lines if line)
    return text

# Získanie pomenovaných entít z otázky používateľa
def get_named_entities(question):
    entities = []
    sentences = nltk.sent_tokenize(question)
    for sentence in sentences:
        tagged = nltk.pos_tag(nltk.word_tokenize(sentence))
        for chunk in nltk.ne_chunk(tagged):
            if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
                entity = ' '.join(c[0] for c in chunk.leaves())
                entities.append(entity)
    return entities


# Funkcia na získanie odpovede na otázku pomocou Google Knowledge Graph API a web scrapingu
def get_answer_google(question):
    # Prevedenie otázky na malé písmená a odstránenie medzier z oboch strán
    query = question.lower().strip()
    # Získanie entít (názvy osôb) z otázky pomocou funkcie get_named_entities()
    named_entities = get_named_entities(question)
    if named_entities:
        # Pridanie entít do query, ak existujú
        query += ' ' + ' '.join(named_entities)
    try:
        # Získanie krátkej odpovede na otázku pomocou Google Knowledge Graph API
        api_key = 'AIzaSyAess9gEe7sfeZEH1oZWMAtr34wSDTReW4' # Nahrad svojou Google API kľúčom
        service_url = 'https://kgsearch.googleapis.com/v1/entities:search'
        params = {
            'query': query,
            'limit': 1,
            'indent': True,
            'key': api_key,
            'languages': 'en',
            'types': 'Thing'
        }
        url = service_url + '?' + urllib.parse.urlencode(params)
        response = requests.get(url).json()
        if response.get('itemListElement'):
            # Ak sa nájde odpoveď, vráti sa názov odpovede
            answer = response['itemListElement'][0]['result']['name']
            return answer
    except:
        pass

    # Ak sa odpoveď nenašla pomocou Knowledge Graph API, použije sa GPT-3 na generovanie odpovede
    prompt = "Answer the following question: " + question
    completions = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )
    if len(completions.choices) > 0:
        answer = completions.choices[0].text
        return answer.strip()

    # Ak sa stále nenašla odpoveď, extrahuje sa text z webovej stránky
    search_results = search(query)
    text = extract_text_from_results(search_results)
    if text:
        return text[0]

    # Ak sa stále nenašla odpoveď, extrahuje sa text z webovej stránky
    for result in search_results:
        url = result['link']
        text = extract_text_from_webpage(url)
        if text:
            return text

    # Ak sa stále nenašla odpoveď, vráti sa None
    return None

# Nacitaj API kluc z .env suboru
load_dotenv()

# Nastav OpenAI API klienta s pouzitim nacitaneho klucu
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_answer_gpt3(prompt):
    # Vytvor poziadavku na odpoved z OpenAI API s pouzitim daneho promptu
    response = openai.Completion.create(
        engine="text-davinci-003",    # Pouzitie najlepsieho jazykoveho modelu
        prompt=prompt,                # Text na zaklade ktoreho chceme ziskat odpoved
        temperature=0.7,              # Hladka funkcia pravdepodobnosti, kontroluje kreativnost a kvalitu odpovede
        max_tokens=1024,               # Maximalna dlzka odpovede
        top_p=1,                      # Najvyssia pravdepodobnost pre vyber dalsieho tokena
        frequency_penalty=0,          # Kontrola pouzivania rovnakych slov alebo fráz v odpovediach
        presence_penalty=0            # Kontrola pouzivania slov, ktore chybaju v prompte
    )
    if response.choices:
        return response.choices[0].text.strip()
    else:
        return "I'm sorry, I don't know the answer to that."



def chat():
    os.system("cls")#Premaže celý command prompt
    print('Hello!')
    while True:
        user_input = input('You: ')

        if user_input.lower() in ['bye', 'exit']:
            print('Bot: Goodbye!')
            break

        else:
            try:
                # Ziskaj odpoved z OpenAI API
                answer = get_answer_gpt3(user_input)
                if answer:
                    print('Bot:', answer)
                else:
                    # Ak OpenAI API nevie poskytnut odpoved, pouzi Google search
                    answer = get_answer_google(user_input)
                    if answer:
                        print('Bot:', answer)
                    else:
                        print('Bot: Sorry, I did not understand your question.')
            except Exception as e:
                print(f'Bot: Sorry, an error occurred:{e}')



if __name__ == '__main__':
    #Spustí sa celý program
    chat()
