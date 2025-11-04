from rdflib import Graph, Namespace, URIRef, Dataset
import re

RDFS_TYPE = Namespace("http://www.w3.org/2000/01/rdf-schema#type")
# Reserved namespace for query variables
QQ = Namespace("http://example.org/query-vars#")

def extract_where_block(query_str: str) -> str:
    """
    Extracts the full WHERE block content, even if multi-line or nested.
    """
    # Normalize whitespace and case for detection
    query_norm = query_str.replace("\n", " ").replace("\r", " ")
    
    # Find the starting point of WHERE {
    where_start = re.search(r"\bWHERE\s*{", query_norm, re.IGNORECASE)
    if not where_start:
        return ""

    start_index = where_start.end()
    brace_count = 1
    i = start_index
    content = []

    # Traverse characters to find matching closing brace
    while i < len(query_norm) and brace_count > 0:
        c = query_norm[i]
        if c == "{":
            brace_count += 1
        elif c == "}":
            brace_count -= 1
        if brace_count > 0:
            content.append(c)
        i += 1

    return "".join(content).strip()

def extract_bgps_from_sparql(query_str):
    """
    Extracts Basic Graph Patterns (BGPs) from a SPARQL query.
    Returns a list of (subject, predicate, object) triples.
    Handles ; , and . syntaxes correctly.
    """
    where_content = extract_where_block(query_str)
    if not where_content:
        return []

    # Clean up irrelevant clauses
    where_content = re.sub(
        r"(FILTER|OPTIONAL|GROUP BY|ORDER BY|BIND|VALUES|GRAPH)[^{]*",
        "",
        where_content,
        flags=re.IGNORECASE,
    )

    tokens = re.split(r"(\s*[\.;,]\s*)", where_content)
    triples = []
    current_subject = None
    last_predicate = None

    for token in tokens:
        token = token.strip()
        if not token or token in {".", ";", ","}:
            continue

        parts = token.split()
        if len(parts) >= 3:  # full triple s p o
            s, p, o = parts[:3]
            current_subject = s
            last_predicate = p
            triples.append((s, p, o))
        elif len(parts) == 2:  # subject omitted (after ;)
            p, o = parts
            triples.append((current_subject, p, o))
            last_predicate = p
        elif len(parts) == 1:  # object list (after ,)
            o = parts[0]
            triples.append((current_subject, last_predicate, o))

    return triples

def create_query_graph_from_sparql(query_str, ontology_prefix="http://semanticweb.org/unitedOntology#"):
    """
    Converts BGPs from SPARQL query into an RDFLib Graph.
    Replaces variables with qq: namespace and 'a' with rdf:type.
    """
    QUERY_GRAPH = URIRef("http://example.org/query")
    g = Graph(identifier=QUERY_GRAPH)
    EX = Namespace(ontology_prefix)
    triples = extract_bgps_from_sparql(query_str)
    if triples == []:
        return None
    for s, p, o in triples:
        subj = URIRef(QQ[s[1:]]) if s.startswith("?") else URIRef(ontology_prefix + s.replace(":", ""))
        pred = URIRef(RDFS_TYPE) if p == "a" else URIRef(ontology_prefix + p.replace(":", ""))
        if o.startswith("?"):
            obj = URIRef(QQ[o[1:]])
        elif ":" in o:
            obj = URIRef(ontology_prefix + o.replace(":", ""))
        else:
            obj = URIRef(QQ[o])
        g.add((subj, pred, obj))
    return g

# domain rule: If the domain of a property p is a class C, 
# then the subject of any triple using p as a predicate must be a member of class C.
domain_rule_query= """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://semanticweb.org/unitedOntology#>
    
    SELECT ?p ?domain ?s ?class WHERE {
        GRAPH <http://example.org/query> {
            ?s ?p ?o .
            ?s rdfs:type ?class .
        }
        GRAPH <http://example.org/ontology> {
            ?p rdfs:domain ?domain .
            FILTER (isIRI(?domain))
        }
        FILTER NOT EXISTS {
            ?class rdfs:subClassOf* ?domain .
        }
    }
    """

# range rule: If the range of a property p is a class C, 
# then the object of any triple using p as a predicate must be a member of class C
range_rule_query= """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://semanticweb.org/unitedOntology#>
    
    SELECT ?p ?range ?o ?class WHERE {
        GRAPH <http://example.org/query> {
            ?s ?p ?o .
            ?o rdfs:type ?class .
        }
        GRAPH <http://example.org/ontology> {
            ?p rdfs:range ?range .
            FILTER (isIRI(?range))
        }
        FILTER NOT EXISTS {
            ?class rdfs:subClassOf* ?range .
        }
    }

"""
# Double range rule: If the object of a first triple is the object of a second triple,
# then the range of the property of the first triple should be the same as the range of the property of the second triple.
double_range_rule= """
    SELECT ?p ?rangep ?q ?rangeq WHERE {
        GRAPH <http://example.org/query> {
            ?s1 ?p ?o .
            ?s2 ?q ?o .
        }
        GRAPH <http://example.org/ontology>{
            ?p rdfs:range ?rangep .
            ?q rdfs:range ?rangeq .
            FILTER (isIRI (?rangeq )) FILTER (isIRI (?rangep ))
        }
        FILTER NOT EXISTS {
            { ?rangep rdfs:subClassOf* ?rangeq .}
            UNION
            { ?rangeq rdfs:subClassOf* ?rangep .}
        }
    }
"""

# double domain rule: If the subject of a first triple is the subject of a second triple, 
# then the domain of the property of the first triple should be the same as the domain of the property of the second triple.
double_domain_rule= """
    SELECT ?p ?domp ?q ?domq WHERE {
        GRAPH <http://example.org/query> {
            ?s ?p ?o1 .
            ?s ?q ?o2 .
        }
        GRAPH <http://example.org/ontology>{
            ?p rdfs:domain ?domp .
            ?q rdfs:domain ?domq .
            FILTER (isIRI (?domq)) FILTER (isIRI (?domp))
        }
        FILTER NOT EXISTS {
            { ?domp rdfs:subClassOf* ?domq .}
            UNION
            { ?domq rdfs:subClassOf* ?domp .}
        }
    }
"""

# domain range rule: If the object of a first triple is the subject of a second triple,
# then the range of the property of the first triple should be the same 
domain_range_rule = """
    SELECT ?p ?rangep ?q ?domq WHERE{
        GRAPH <http://example.org/query> {
            ?s ?p ?o .
            ?o ?q ?o2 .
        }
        GRAPH <http://example.org/ontology> {
            ?p rdfs:range ?rangep .
            ?q rdfs:domain ?domq .
            FILTER (isIRI(?domq)) FILTER(isIRI(?rangep))
        }
        FILTER NOT EXISTS {
            { ?rangep rdfs:subClassOf* ?domq .}
            UNION
            { ?domq rdfs:subClassOf* ?rangep .}
        }
    }

"""

# Incorrect Property: All the properties of the query need to exist in the ontology
incorrect_property_rule = """
    SELECT ?p WHERE {
        GRAPH <http://example.org/query> {
            ?s ?p ?o .
            FILTER NOT EXISTS {
                VALUES ?ns {
                "http://www.w3.org/1999/02/22rdf-syntax-ns#"
                "http://www.w3.org/2002/07/owl#"
                "http://www.w3.org/2000/01/rdf-schema#"
                "http://www.w3.org/2004/02/skos/core#"
                }
                FILTER(STRSTARTS(STR(?p) , ?ns))
            }
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/ontology> {
                ?p a ?type
            }
        }
    }

"""

def validate_sparql(query, ontology):
    """
    Function that validates a SPARQL query, using the ontology schema and some SPARQL constraints
    """
    
    # create an rdflib Graph and parse the ontology schema
    ONT_GRAPH = URIRef("http://example.org/ontology")
    ontology_graph = Graph(identifier=ONT_GRAPH)
    ontology_graph.parse(ontology, format="turtle")
    # create a graph from the query 
    query_graph = create_query_graph_from_sparql(query)
    if query_graph is None:
        return "Input not SPARQL"
    #print(f"Triples in query graph: {len(query_graph)}")
    #for r in query_graph:
    #   print(r)
    # create an rdflib dataset to combine the two graphs
    dataset = Dataset()
    dataset.add_graph(ontology_graph)
    dataset.add_graph(query_graph)
    dataset.default_graph = ontology_graph
    
    error_messages = []

    # query the dataset with SPARQL constraints
    print("Checking Domain Rule: ") 
    results = dataset.query(domain_rule_query)
    if results:
        for row in results:
            message = f"The property {row['p']} has range {row['domain']}, but its subject {row['s']} is a {row['class']}, which isn't a subclass of {row['domain']}"
            error_messages.append(message)
    else:
        print("Rule Passed!")
    
    print("Checking Range Rule") 
    results = dataset.query(range_rule_query)
    if results:
        for row in results:
            message = f"The property {row['p']} has range {row['range']}, but its object {row['o']} is a {row['class']}, which isn't a subclass of {row['range']}"
            error_messages.append(message)
    else:
        print("Rule Passed!")
    
    print("Checking Double Range Rule")
    results = dataset.query(double_range_rule)
    if results:
        for row in results:
            message = f"The property {row['p']} has range {row['rangep']}, and {row['q']} has range {row['rangeq']} and these are incompatible." 
            error_messages.append(message)
    else:
        print("Rule Passed!")

    print("Checking Double Domain Rule")
    results = dataset.query(double_domain_rule)
    if results:
        for row in results:
            message = f"The property {row['p']} has domain {row['domp']}, and {row['q']} has domain {row['domq']} and these are incompatible."
            error_messages.append(message)
    else:
        print("Rule Passed!")

    print("Checking domain-range rule")
    results = dataset.query(domain_range_rule)
    if results:
        for row in results:
            message = f"The property {row['p']} has range {row['rangep']}, and {row['q']} has domain {row['domq']} and these are incompatible. "
            error_messages.append(message)
    else:
        print("Rule Passed!")


    print("Checking incorrect property rule")
    results = dataset.query(incorrect_property_rule)
    if results:
        for row in results:
            message = f"The property {row['p']} isn't defined in the ontology. Please only use properties from the ontology, or from a standard source like rdf:, rdfs:, owl:, or skos:."
            error_messages.append(message)
    else:
        print("Rule Passed!")

    if error_messages != []:
        return error_messages
    return None




if __name__ == "__main__":

    s = """
    PREFIX : <http://semanticweb.org/unitedOntology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?player ?team 
    WHERE {
        ?team a :Team .  
        ?player a :Player. 
        ?team :hasPlayer ?player ;
    }   
    GROUP BY ?player ?team
    ORDER BY DESC(?goals)

    """

    ontology= 'ontology/ontology_export.ttl'
    
    validate_sparql(s, ontology)

