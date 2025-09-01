import google.generativeai as genai
import os
import json

# Configure the Gemini API client
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # Handle the case where the API key is not set
    # The application will fail gracefully later if the model is not available
    pass

def get_model():
    """Initializes and returns the Gemini Pro model."""
    try:
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        print(f"Could not initialize Gemini model: {e}")
        return None

def clean_json_from_response(text_response):
    """
    Extracts a JSON object or array from a string response,
    which might be wrapped in markdown backticks.
    """
    # Find the start and end of the JSON block
    json_start = text_response.find('{')
    json_end = text_response.rfind('}') + 1

    if json_start == -1 or json_end == 0:
        json_start = text_response.find('[')
        json_end = text_response.rfind(']') + 1
        if json_start == -1 or json_end == 0:
            return None # No JSON found

    json_str = text_response[json_start:json_end]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Problematic JSON string: {json_str}")
        return None

def analyze_document_context(full_text):
    """
    Performs the first AI call to get the overall disease context and a list of drugs.
    """
    model = get_model()
    if not model:
        return None

    prompt = f"""
    Проанализируй следующий текст клинического протокола. Твоя задача — выполнить две вещи:
    1. Определи основное заболевание или клинический контекст, описанный в протоколе.
    2. Извлеки ВСЕ лекарственные препараты, упомянутые в тексте, вместе с их способом применения и уровнем доказательности (если указан).

    Верни результат в виде ОДНОГО JSON-объекта со следующей структурой:
    {{
      "disease_context": "...",
      "drug_list": [
        {{
          "inn_protocol": "...",
          "usage_protocol": "...",
          "loe_protocol": "..."
        }}
      ]
    }}

    Вот текст для анализа:
    ---
    {full_text[:15000]}
    ---
    """ # Truncate text to avoid exceeding token limits

    try:
        response = model.generate_content(prompt)
        return clean_json_from_response(response.text)
    except Exception as e:
        print(f"Gemini API call for document context failed: {e}")
        return None

def get_drug_details(inn_protocol, usage_protocol, disease_context):
    """
    Performs the second AI call to get detailed information for a single drug.
    """
    model = get_model()
    if not model:
        return None

    prompt = f"""
    Проанализируй следующий препарат в контексте заболевания "{disease_context}".

    Препарат: {inn_protocol}
    Способ применения: {usage_protocol}

    Верни результат в виде ОДНОГО JSON-объекта со следующей структурой:
    {{
      "inn_english": "...",
      "brief_description": "...",
      "system_loe": "..."
    }}

    Пояснения к полям:
    - inn_english: Международное непатентованное наименование (МНН) на английском языке.
    - brief_description: Очень краткое (1-2 предложения) описание роли этого препарата в лечении указанного заболевания.
    - system_loe: Твоя оценка уровня доказательности препарата для данного показания (например, "Класс I (A)", "Класс IIb (B)"), основанная на твоих общих знаниях.
    """

    try:
        response = model.generate_content(prompt)
        return clean_json_from_response(response.text)
    except Exception as e:
        print(f"Gemini API call for drug details failed for '{inn_protocol}': {e}")
        return None
