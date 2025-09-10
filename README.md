1. Ontology = Explicit Meaning

In RDF/OWL, you don’t just store raw data — you also store rules and definitions about what those things mean.

Example in RDF with ontology:

:MajorityStakeholder a owl:Class .
:OwnershipRelation a owl:Class .
:percentage a owl:DatatypeProperty .

# Rule: Anyone with >50% stake is a MajorityStakeholder
[ a owl:Restriction ;
  owl:onProperty :percentage ;
  owl:hasValue "50"^^xsd:decimal
] .


Because of the ontology:

A reasoner can infer:

If BlackRock’s percentage > 50, then BlackRock is a MajorityStakeholder.

You don’t have to manually tag every majority investor — the KG can deduce it.


SELECT ?investor WHERE {
  ?investor a :MajorityStakeholder .
}
Even if no triple explicitly says "BlackRock" a "MajorityStakeholder", the reasoner can return it.

In property graphs, you’d need to query:

cypher
Copy code
MATCH (i:Investor)-[r:OWNS]->(c:Company)
WHERE r.percentage > 50
RETURN i



2. What n10s (Neosemantics) Does

The Neosemantics plugin
 adds RDF support to Neo4j.

Main capabilities:

Import RDF data into Neo4j:

Reads triples (subject, predicate, object).

Maps RDF resources to nodes and properties in Neo4j.

Preserves RDF schema elements (e.g., rdf:type, rdfs:subClassOf).

Export RDF from Neo4j:

Takes your property graph and serializes it into RDF (Turtle, JSON-LD, N-Triples).

Expose a SPARQL endpoint:

Translates SPARQL queries to Cypher internally.

Limited reasoning — mostly just query translation.

3. How Semantics Are Handled

When n10s imports RDF:

Ontology triples (like :MajorityStakeholder rdfs:subClassOf :Stakeholder) are stored as nodes/edges in Neo4j.

Instance triples (like :BlackRock rdf:type :MajorityStakeholder) are stored as relationships or labels.

Reasoning is not automatic:

Neo4j will store the subClassOf relationship.

But it won’t automatically infer "BlackRock" is also a Stakeholder unless:

You run a custom Cypher query to materialize that fact, OR

You run an external reasoner before import.

💡 This is the main difference:

Native RDF stores (e.g., GraphDB, Stardog) can dynamically answer inferred queries using RDFS/OWL rules.

Neo4j + n10s stores the ontology structure, but you have to simulate reasoning with Cypher or preprocessing.

4. Example

Suppose RDF triple store contains:

:MajorityStakeholder rdfs:subClassOf :Stakeholder .
:BlackRock rdf:type :MajorityStakeholder .


In GraphDB (RDF store):

Query: SELECT ?x WHERE { ?x rdf:type :Stakeholder }

Returns: :BlackRock (via inference).

In Neo4j + n10s:

Ontology is stored:

(:Class {uri: "MajorityStakeholder"})-[:SCO]->(:Class {uri: "Stakeholder"})
(:BlackRock)-[:TYPE]->(:MajorityStakeholder)


If you run Cypher:

MATCH (x)-[:TYPE]->(c)-[:SCO*0..]->(:Class {uri: "Stakeholder"})
RETURN x


You manually traverse the hierarchy to find BlackRock.

5. Summary Table
Feature	RDF Triple Store (GraphDB, Stardog)	Neo4j + n10s
Storage	Native RDF triples	Property graph nodes/edges
Query	SPARQL with reasoning	Cypher (SPARQL via translation)
Reasoning	Built-in RDFS/OWL inference	Manual via Cypher or preprocessing
Ontology support	Full semantic reasoning	Ontology stored, but no auto-inference
Interoperability	High (W3C RDF standards)	Medium (via import/export)

Bottom line:

Neo4j + n10s is great if you want RDF interoperability inside a property graph environment.

It’s not a full semantic reasoner — you’ll need either:

An external RDF reasoner before loading data, or

Custom Cypher queries to mimic inference.



if you only have Neo4j Community Edition (no multi-database support), you can use a vertex attribute (or label) to keep two graphs from colliding inside the same database.

Here’s how you can do it:

1️⃣ Use a graphId Property

Assign each node (vertex) and relationship an attribute that identifies which graph it belongs to.

Creating data for Graph 1:
CREATE (:Person {graphId: "graph1", name: "Alice"});
CREATE (:City   {graphId: "graph1", name: "Paris"});

Creating data for Graph 2:
CREATE (:Person {graphId: "graph2", name: "Bob"});
CREATE (:City   {graphId: "graph2", name: "London"});

2️⃣ Query Only One Graph

Graph 1:

MATCH (n {graphId: "graph1"})
RETURN n;


Graph 2:

MATCH (n {graphId: "graph2"})
RETURN n;

3️⃣ Use Labels for Separation

You can also add labels to nodes so queries are faster.

Graph 1:

CREATE (:Graph1:Person {name: "Alice"});


Graph 2:

CREATE (:Graph2:Person {name: "Bob"});


Query Graph 1:

MATCH (n:Graph1) RETURN n;


Query Graph 2:

MATCH (n:Graph2) RETURN n;

4️⃣ Relationships Separation

If you create relationships, also tag them:

MATCH (a:Person {name: "Alice"}), (c:City {name: "Paris"})
CREATE (a)-[:LIVES_IN {graphId: "graph1"}]->(c);

