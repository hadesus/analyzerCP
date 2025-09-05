import google.generativeai as genai
import os
import json

class AIProcessorException(Exception):
    """Custom exception for AI processing errors."""
    pass

# Configure the Gemini API client
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
except Exception as e:
    # This is a critical error, so we raise our custom exception
    raise AIProcessorException(f"Error configuring Gemini API: {e}")

def get_model():
    """Initializes and returns the Gemini Pro model."""
    try:
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        raise AIProcessorException(f"Could not initialize Gemini model: {e}")

def clean_json_from_response(text_response):
    """
    Extracts a JSON object or array from a string response that might be wrapped in markdown.
    Raises AIProcessorException if JSON is malformed or not found.
    """
    json_start = text_response.find('{')
    json_end = text_response.rfind('}') + 1
    if json_start == -1 or json_end == 0:
        json_start = text_response.find('[')
        json_end = text_response.rfind(']') + 1
        if json_start == -1 or json_end == 0:
            raise AIProcessorException("No JSON object found in the AI response.")

    json_str = text_response[json_start:json_end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        error_message = f"Failed to decode JSON from AI response. Error: {e}. Response snippet: '{json_str[:100]}...'"
        raise AIProcessorException(error_message)

def analyze_document_context(full_text):
    """
    Performs the first AI call to get the overall disease context and a list of drugs.
    Raises AIProcessorException on failure.
    """
    model = get_model()
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
    """
    try:
        response = model.generate_content(prompt)
        # The response object has a prompt_feedback attribute that can be checked for safety ratings
        if response.prompt_feedback.block_reason:
            raise AIProcessorException(f"AI call blocked due to: {response.prompt_feedback.block_reason.name}")
        return clean_json_from_response(response.text)
    except Exception as e:
        raise AIProcessorException(f"Gemini API call for document context failed: {e}")

def get_drug_details(inn_protocol, usage_protocol, disease_context):
    """
    Performs the second AI call to get detailed information for a single drug.
    Raises AIProcessorException on failure.
    """
    model = get_model()
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
        if response.prompt_feedback.block_reason:
            raise AIProcessorException(f"AI call blocked for drug '{inn_protocol}' due to: {response.prompt_feedback.block_reason.name}")
        return clean_json_from_response(response.text)
    except Exception as e:
        raise AIProcessorException(f"Gemini API call for drug details failed for '{inn_protocol}': {e}")
