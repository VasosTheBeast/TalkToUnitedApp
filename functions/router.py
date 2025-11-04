
from google import genai
from google.genai import types

def should_use_kg(api_key: str, question: str) -> bool:
    """Asks Gemini if the question needs the KG."""
    client = genai.Client(api_key=api_key)

    router_prompt = """
    You are a classifier. Decide if the following question needs information
    from a Knowledge Graph (e.g., football data such as players, teams, matches, stats, of Premier League 25-26).
    Answer strictly as JSON:
    {"use_kg": true} or {"use_kg": false}.
    """

    messages = [
        types.Content(role="user", parts=[types.Part(text=question)])
    ]

    config = types.GenerateContentConfig(system_instruction=router_prompt)

    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=messages,
        config=config
    )

    if not response or not response.candidates:
        return False

    text = response.candidates[0].content.parts[0].text.strip().lower()

    return "true" in text
