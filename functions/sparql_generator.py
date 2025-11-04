# functions/sparql_generator.py
from google import genai
from google.genai import types

def generate_sparql(api_key: str, ontology_path: str, question: str) -> str:
    """Uses Gemini to create a SPARQL query based on the ontology."""
    with open(ontology_path, "r") as f:
        ontology_text = f.read()

    client = genai.Client(api_key=api_key)

    system_prompt = f"""
    You are an expert in Semantic Web and SPARQL query generation.

    Here is the ontology schema:
    {ontology_text}

    Here are some SPARQL examples:

    Q: List all players and the teams they play for.
    A:
    PREFIX : <http://semanticweb.org/unitedOntology#>
    SELECT ?player ?team
    WHERE {{
    ?player a :Player ;
            :playsFor ?team .
    }}

    Example 2:
    Q: List all features of a Manchester United, with goals they scored and conceded
    A:
    PREFIX : <http://semanticweb.org/unitedOntology#>

    SELECT DISTINCT ?home_team ?away_team ?home_goals ?away_goals 
    WHERE {{
    ?m a ?Match ;
        :matchHasTeamStats ?ts1 ;
        :matchHasTeamStats ?ts2 ;
        :matchGameweek ?gameweek ;
        :hasHomeTeam ?home_team ;
        :hasAwayTeam ?away_team.
    ?ts1 :statsOfTeam ?home_team ;
            :teamGoalsScored ?home_goals .
    ?ts2 :statsOfTeam ?away_team ;
            :teamGoalsScored ?away_goals .
        
    FILTER(?home_team = :Manchester_United || ?away_team = :Manchester_United)
    }} ORDER BY ASC(?gameweek)

    Task:
    - Given a natural language question, generate a valid SPARQL 1.1 SELECT query.
    - Use prefix : <http://semanticweb.org/unitedOntology#>
    - Return only one SPARQL query — no explanations, NO MARKDOWN, no commentary.
    """

    messages = [types.Content(role="user", parts=[types.Part(text=question)])]

    config = types.GenerateContentConfig(system_instruction=system_prompt)

    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=messages,
        config=config
    )

    if not response or not response.candidates:
        return "⚠️ Could not generate SPARQL."

    return response.candidates[0].content.parts[0].text.strip()
