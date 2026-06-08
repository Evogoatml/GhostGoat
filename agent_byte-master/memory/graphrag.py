#!/usr/bin/env python3
"""
Neo4j GraphRAG with LangChain
Knowledge Graph powered by local LLM (Ollama)
"""

import os
import json
import logging
import re
import requests  # Added for LLM extraction calls
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable not set")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

PAYLOADS_DIR = Path('/home/popic/PayloadsAllTheThings')

@dataclass
class Node:
    id: str
    label: str
    type: str
    properties: dict

@dataclass
class Relationship:
    from_node: str
    to_node: str
    type: str
    properties: dict = None

class Neo4jGraphRAG:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.nodes = []
        self.relationships = []
        self._driver = None
        
    def connect(self):
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            logger.info("Connected to Neo4j")
            return True
        except ImportError:
            logger.warning("neo4j driver not installed, using in-memory")
            return False
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            return False
    
    def create_node(self, node: Node):
        self.nodes.append(node)
        logger.info(f"Created node: {node.id}")
        
    def create_relationship(self, rel: Relationship):
        self.relationships.append(rel)
        logger.info(f"Created relationship: {rel.from_node} -> {rel.to_node}")
    
    def query(self, cypher: str) -> List[dict]:
        try:
            if self._driver:
                with self._driver.session() as session:
                    result = session.run(cypher)
                    return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query error: {e}")
        return []
    
    def get_node_context(self, query: str, top_k: int = 5) -> str:
        relevant_nodes = []
        query_lower = query.lower()
        
        for node in self.nodes:
            if any(q in node.id.lower() or q in node.label.lower() 
                 for q in query_lower.split()):
                relevant_nodes.append(node)
                
        if not relevant_nodes:
            return ""
        
        context = "=== KNOWLEDGE GRAPH ===\n\n"
        for node in relevant_nodes[:top_k]:
            context += f"Entity: {node.label} ({node.type})\n"
            context += f"ID: {node.id}\n"
            props = json.dumps(node.properties, indent=2)
            context += f"Properties: {props}\n\n"
            
            related = [r for r in self.relationships 
                      if r.from_node == node.id or r.to_node == node.id]
            for r in related[:3]:
                context += f"  --[{r.type}]--> {r.to_node}\n"
            context += "\n"
            
        return context
    
    def close(self):
        if self._driver:
            self._driver.close()

def extract_entities_with_llm(text: str, llm_url: str, model: str) -> List[dict]:
    prompt = f"""Extract key security concepts and their relationships from this text.
Return a JSON array of entities with format:
{{"id": "entity_name", "label": "Entity Label", "type": "CONCEPT|TECHNIQUE|TOOL|VULNERABILITY", "properties": {{"description": "..."}}}}

Text:
{text[:2000]}

JSON:"""

    try:
        response = requests.post(
            llm_url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json().get('response', '')
            entities = json.loads(result.strip())
            return entities
    except Exception as e:
        logger.error(f"LLM extraction error: {e}")
    
    return []

def extract_entities_simple(text: str) -> List[dict]:
    """Simple entity extraction without LLM"""
    entities = []
    
    vulnerability_patterns = [
        (r'sql injection', 'SQL Injection', 'VULNERABILITY'),
        (r'buffer overflow', 'Buffer Overflow', 'VULNERABILITY'),
        (r'cross.?site scripting|xss', 'XSS', 'VULNERABILITY'),
        (r'command injection', 'Command Injection', 'VULNERABILITY'),
        (r'rop|return.oriented programming', 'ROP Chaining', 'TECHNIQUE'),
        (r'privilege escalation', 'Privilege Escalation', 'TECHNIQUE'),
        (r'sqli', 'SQL Injection', 'VULNERABILITY'),
        (r'xss|cross site', 'XSS', 'VULNERABILITY'),
    ]
    
    technique_patterns = [
        (r'metasploit', 'Metasploit', 'TOOL'),
        (r'nmap', 'Nmap', 'TOOL'),
        (r'burp suit', 'Burp Suite', 'TOOL'),
        (r'wireshark', 'Wireshark', 'TOOL'),
        (r'sqlmap', 'SQLMap', 'TOOL'),
        (r'nikto', 'Nikto', 'TOOL'),
    ]
    
    found = set()
    text_lower = text.lower()
    
    for pattern, label, etype in vulnerability_patterns + technique_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            entity_id = label.lower().replace(' ', '-')
            if entity_id not in found:
                found.add(entity_id)
                entities.append({
                    "id": entity_id,
                    "label": label,
                    "type": etype,
                    "properties": {"description": f"Related to {label}"}
                })
    
    return entities

def extract_relationships(entities: List[dict], text: str) -> List[dict]:
    """Extract relationships between entities"""
    relationships = []
    
    vulnerability_techniques = {
        'sql-injection': ['data-breach', 'authentication-bypass', 'data-manipulation'],
        'buffer-overflow': ['code-execution', 'denial-of-service'],
        'xss': ['session-hijacking', 'cookie-theft', 'defacement'],
    }
    
    for entity in entities:
        eid = entity['id']
        if eid in vulnerability_techniques:
            for target in vulnerability_techniques[eid]:
                relationships.append({
                    "from": eid,
                    "to": target,
                    "type": "CAN_LEAD_TO"
                })
    
    return relationships

def build_graph_from_docs(graph: Neo4jGraphRAG, docs_dir: Path):
    """Build knowledge graph from documents"""
    
    categories = [
        'SQL Injection',
        'XSS Injection', 
        'Command Injection',
        'Buffer Overflow',
        'Server Side Request Forgery',
        'Insecure Deserialization',
        'Privilege Escalation',
    ]
    
    for category in docs_dir.iterdir():
        if not category.is_dir():
            continue
        if category.name.startswith('_') or category.name.startswith('.'):
            continue
            
        category_name = category.name
        files_processed = 0
        
        for md_file in category.glob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if len(content) < 100:
                    continue
                    
                entity = Node(
                    id=md_file.stem.lower().replace(' ', '-'),
                    label=md_file.stem,
                    type='TECHNIQUE',
                    properties={
                        'category': category_name,
                        'content': content[:500],
                        'file': str(md_file.name)
                    }
                )
                graph.create_node(entity)
                
                cat_entity = Node(
                    id=category_name.lower().replace(' ', '-'),
                    label=category_name,
                    type='CATEGORY',
                    properties={'name': category_name}
                )
                graph.create_node(cat_entity)
                
                rel = Relationship(
                    from_node=entity.id,
                    to_node=cat_entity.id,
                    type='BELONGS_TO'
                )
                graph.create_relationship(rel)
                
                entities = extract_entities_simple(content)
                for ent in entities[:5]:
                    e = Node(
                        id=ent['id'],
                        label=ent['label'],
                        type=ent['type'],
                        properties=ent.get('properties', {})
                    )
                    graph.create_node(e)
                    
                    r = Relationship(
                        from_node=entity.id,
                        to_node=ent['id'],
                        type='RELATED_TO'
                    )
                    graph.create_relationship(r)
                
                files_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
        
        logger.info(f"Processed {category_name}: {files_processed} files")

class LangChainRAG:
    """Simple RAG using LangChain-like patterns with local LLM"""
    
    def __init__(self, graph: Neo4jGraphRAG, llm_url: str, model: str):
        self.graph = graph
        self.llm_url = llm_url
        self.model = model
        
    def retrieve(self, query: str) -> str:
        return self.graph.get_node_context(query)
    
    def generate(self, query: str, context: str) -> str:
        prompt = f"""You are a penetration testing expert assistant. 
Use the knowledge graph context below to answer the question accurately.

Knowledge Graph:
{context}

Question: {query}

Answer (be specific and technical):"""

        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7}
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"Generation error: {e}")
        
        return None
    
    def query(self, question: str) -> str:
        context = self.retrieve(question)
        if not context:
            return "I don't have relevant knowledge for that question."
        
        answer = self.generate(question, context)
        return answer or "I couldn't generate an answer."

def main():
    graph = Neo4jGraphRAG(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    connected = graph.connect()
    
    if connected:
        logger.info("Building graph from Neo4j...")
        graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
    else:
        logger.info("Building in-memory graph...")
    
    build_graph_from_docs(graph, PAYLOADS_DIR)
    
    logger.info(f"Graph built: {len(graph.nodes)} nodes, {len(graph.relationships)} relations")
    
    rag = LangChainRAG(graph, OLLAMA_URL, OLLAMA_MODEL)
    
    test_questions = [
        "How does SQL injection work?",
        "What is buffer overflow?",
        "How to bypass DEP?",
    ]
    
    logger.info("Testing RAG...")
    for q in test_questions:
        print(f"\nQ: {q}")
        answer = rag.query(q)
        print(f"A: {answer[:500]}...")

if __name__ == '__main__':
    main()