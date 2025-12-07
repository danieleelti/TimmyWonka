import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
import os

def get_gemini_models(api_key):
    """Interroga Google per ottenere i modelli disponibili per questa API Key."""
    if not api_key: return ["Inserisci API Key prima"]
    try:
        genai.configure(api_key=api_key)
        # Filtra solo i modelli che generano contenuto (escludendo embedding)
        models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ordina per mettere le versioni più nuove/pro in evidenza se possibile
        models.sort(reverse=True) 
        return models
    except Exception as e:
        return [f"Errore: {str(e)}"]

def get_openai_models(api_key, base_url=None):
    """Recupera modelli da OpenAI o compatibili (Groq, Grok)."""
    if not api_key: return ["Inserisci API Key prima"]
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        models_list = client.models.list()
        # Filtriamo per pulizia (escludiamo whisper, tts, dall-e dalla lista testuale)
        # Per Groq/Grok prendiamo tutto perché sono pochi
        model_names = [m.id for m in models_list.data]
        
        # Se è OpenAI ufficiale, filtriamo per mostrare solo i GPT chat
        if not base_url: 
            model_names = [m for m in model_names if "gpt" in m or "o1" in m]
            
        model_names.sort(reverse=True)
        return model_names
    except Exception as e:
        return [f"Errore fetch: {str(e)}"]

def get_anthropic_models(api_key):
    """
    Anthropic non ha un endpoint 'list_models' pubblico semplice come OpenAI.
    Restituiamo le versioni note più potenti e permettiamo l'inserimento manuale se serve.
    """
    if not api_key: return ["Inserisci API Key prima"]
    # Lista hardcoded delle versioni attuali più potenti
    # Se esce Claude 3.7 domani, basterà aggiungerlo qui o usare l'opzione "Custom"
    known_models = [
        "claude-3-5-sonnet-latest",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    return known_models
