import requests

def execute_sparql(url, query):
    
    """
    Function that takes a triplestore url and a sparql query and executes the query
    """
    headers = {
        'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/sparql-query',
    }
    data = {
        'query': query
    }
    try:
        response = requests.post(url, data=query.encode('utf-8'), headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error querying GraphDB: {e}")
        return []
    
    try:
        results = response.json()
    except ValueError:
        print("Error decoding JSON response from SPARQL endpoint.")
        return []
    bindings = results.get("results", {}).get("bindings", [])
    return bindings

