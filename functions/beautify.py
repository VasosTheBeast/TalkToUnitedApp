from google import genai
from google.genai import types

def beautify(api_key, query, answer):
    # connect with the genai client
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
        The user asked this question: 
        {query}
        After quering the KG, we have this answer:
        {answer}
        Return the answer in a human readable form. 
        Return just the answer, nothing else.
    """

    messages = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    config=types.GenerateContentConfig(max_output_tokens=300)
    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=messages,
        config=config
    )

    if not response or not response.candidates:
        return False

    text = response.candidates[0].content.parts[0].text

    return text
     