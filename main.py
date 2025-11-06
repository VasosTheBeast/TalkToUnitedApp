import os
from dotenv import load_dotenv
from functions.chat_manager import ChatManager
from functions.router import should_use_kg
from functions.sparql_generator import generate_sparql
from functions.execute_query import execute_sparql
from functions.beautify import beautify
from functions.sparql_validator import validate_sparql

MAX_RETRIES = 3

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    graphDb_url = os.getenv("GRAPH_DB_ENDPOINT")
    ontology_path = "ontology/simple_test.txt"
    turtle_ontology = "ontology/ontology_export.ttl"

    base_prompt = (
        "You are a helpful assistant specialized in football and knowledge graph reasoning about Premier League 25-26. "
        "Decide when to create SPARQL queries based on user questions."
    )

    # Create the chatbot
    chat = ChatManager(api_key=api_key, system_prompt=base_prompt, keep_history=True)

    print("Football Chatbot started! Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        
        # flag to understand if the llm generated a sparql or not
        not_sparql = False
        # Step 1 — Ask the router
        use_kg = should_use_kg(api_key, user_input)

        if use_kg:
            chat.add_message('user',user_input)
            print("Querying the Knowledge Graph...")
            for attempt in range(MAX_RETRIES):
                if attempt == 0:
                    prompt_for_llm = user_input
                else:
                    prompt_for_llm = (
                        f"The previous SPARQL query failed validation with these errors: {errors}. "
                        f"Please correct and regenerate a valid SPARQL query for: {user_input}"
                    )
                sparql_query = generate_sparql(api_key, ontology_path, prompt_for_llm)
                print(f"\nAttempt {attempt + 1} — SPARQL generated:\n{sparql_query}\n")

                # validate the query
                errors = validate_sparql(sparql_query, turtle_ontology)
                if errors == "Input not SPARQL":
                    not_sparql = True
                    break
                if not errors:
                    print("SPARQL validated successfully.")
                    break
                else:
                    print(f"Validation failed (attempt {attempt + 1}/{MAX_RETRIES}): {errors}")
                    attempt += 1
        
            if not_sparql is True:
                print("Cannot answer the question..")
                continue
            response = execute_sparql(graphDb_url, sparql_query)
            if response:
                reply_text = beautify(api_key,user_input, response)
                print("After connecting with the KG here is the answer:", reply_text)
                chat.add_message("assistant", reply_text)
            else:
                print("Did not find any results.")
        else:
            response = chat.ask(user_input)
            print(f"Bot: {response}\n")


if __name__ == "__main__":
    main()


    