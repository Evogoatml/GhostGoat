"""
Meta-Agentic Gödel Agent System (Local)
========================================
Integrates: LangGraph, GraphRAG, Neuro-ReAct, Semantic Router
Storage:    DuckDB (SQL queries) + ChromaDB (vector memory)
Tracking:   MLflow

Identical agent architecture; only the infrastructure layer differs.
"""

import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Annotated

import duckdb
import mlflow
import numpy as np
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolExecutor
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic
from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder
from typing import TypedDict
# init_dual_brain removed — wire orchestrator at startup

# At startup
# dual_brain wired at startup


# ==================== Core State ====================

class GodelAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "conversation history"]
    current_task: str
    reflexion_depth: int
    proof_trace: List[Dict[str, Any]]
    vector_memory_ids: List[str]
    graph_context: Dict[str, Any]
    agent_decisions: List[Dict[str, Any]]
    semantic_route: Optional[str]
    self_consistency_score: float
    iteration_count: int
    tools_used: List[str]
    error_state: Optional[str]


# ==================== Local Vector Store (ChromaDB) ====================

class LocalVectorStore:
    """
    Persistent vector store backed by ChromaDB.

    Replaces DatabricksVectorStore (Delta Lake + FAISS).
    ChromaDB handles embedding storage, similarity search, and persistence
    natively — no separate FAISS index required.
    """

    def __init__(self, persist_dir: str = "./chroma_db"):
        self.ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            "vector_memory", embedding_function=self.ef
        )

    def add_memory(
        self,
        content: str,
        metadata: Dict,
        agent_id: str,
        community_id: int = 0,
    ) -> str:
        doc_id = f"mem_{datetime.now().timestamp()}_{np.random.randint(10000)}"
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                **{k: str(v) for k, v in metadata.items()},  # ChromaDB requires str values
                "agent_id": agent_id,
                "community_id": str(community_id),
                "timestamp": datetime.now().isoformat(),
            }],
        )
        return doc_id

    def similarity_search(
        self, query: str, k: int = 5, agent_id: Optional[str] = None
    ) -> List[Dict]:
        n = min(k, max(self.collection.count(), 1))
        where = {"agent_id": agent_id} if agent_id else None
        results = self.collection.query(
            query_texts=[query],
            n_results=n,
            where=where,
        )
        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "id": results["ids"][0][i],
                "content": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else 0.0,
            })
        return output


# ==================== GraphRAG ====================

class GraphRAGEngine:
    """Graph-based RAG with community detection and hierarchical retrieval."""

    def __init__(self, vector_store: LocalVectorStore):
        self.vector_store = vector_store
        self.graph_structure: Dict[str, List[str]] = defaultdict(list)
        self.community_map: Dict[int, np.ndarray] = {}
        # Reuse the same embedding model as the vector store to avoid double-loading
        from sentence_transformers import SentenceTransformer
        self._embed = SentenceTransformer("all-MiniLM-L6-v2")

    def add_knowledge_node(
        self, content: str, node_type: str, connections: List[str], agent_id: str
    ) -> str:
        node_id = f"node_{datetime.now().timestamp()}"
        community_id = self._assign_community(content)
        self.vector_store.add_memory(
            content=content,
            metadata={
                "node_type": node_type,
                "connections": json.dumps(connections),
                "node_id": node_id,
            },
            agent_id=agent_id,
            community_id=community_id,
        )
        for conn in connections:
            self.graph_structure[node_id].append(conn)
            self.graph_structure[conn].append(node_id)
        return node_id

    def _assign_community(self, content: str) -> int:
        embedding = self._embed.encode(content)
        if not self.community_map:
            self.community_map[0] = embedding
            return 0
        max_sim, assigned = -1.0, 0
        for comm_id, centroid in self.community_map.items():
            denom = np.linalg.norm(embedding) * np.linalg.norm(centroid) + 1e-9
            sim = float(np.dot(embedding, centroid) / denom)
            if sim > max_sim:
                max_sim, assigned = sim, comm_id
        if max_sim < 0.5:
            assigned = len(self.community_map)
            self.community_map[assigned] = embedding
        return assigned

    def hierarchical_retrieval(self, query: str, depth: int = 2) -> List[Dict]:
        initial = self.vector_store.similarity_search(query, k=3)
        expanded, visited = [], set()
        for result in initial:
            node_id = result["metadata"].get("node_id")
            if node_id and node_id not in visited:
                visited.add(node_id)
                expanded.append(result)
                if depth > 1:
                    for conn_id in self.graph_structure.get(node_id, [])[:2]:
                        if conn_id not in visited:
                            expanded.extend(self.vector_store.similarity_search(conn_id, k=1))
                            visited.add(conn_id)
        return expanded


# ==================== Semantic Router ====================

class AgentSemanticRouter:
    """Route tasks to specialised cognitive modes."""

    def __init__(self):
        self.encoder = HuggingFaceEncoder()
        self.routes = [
            Route("analytical_reasoning",
                  ["analyze this data", "perform statistical analysis",
                   "evaluate the hypothesis", "calculate correlations"]),
            Route("creative_synthesis",
                  ["generate new ideas", "brainstorm solutions",
                   "create novel approach", "synthesize insights"]),
            Route("meta_cognitive_reflection",
                  ["reflect on this decision", "evaluate my reasoning",
                   "identify biases", "check consistency"]),
            Route("tool_orchestration",
                  ["execute this workflow", "coordinate multiple tasks",
                   "run distributed job", "orchestrate agents"]),
            Route("knowledge_integration",
                  ["integrate these concepts", "build knowledge graph",
                   "connect ideas", "synthesize information"]),
        ]
        self.route_layer = RouteLayer(encoder=self.encoder, routes=self.routes)

    def route_task(self, task_description: str) -> str:
        route = self.route_layer(task_description)
        return route.name if route else "general_reasoning"


# ==================== Neuro-ReAct ====================

class NeuroReActAgent:
    """Neural reasoning with Thought → Action → Observation loop."""

    def __init__(self, llm: ChatAnthropic, tools: List[BaseTool]):
        self.llm = llm
        self.tools = tools
        self.tool_executor = ToolExecutor(tools)
        self.reasoning_trace: List[Dict] = []

    async def reason_act_observe(self, state: GodelAgentState) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a meta-cognitive agent using ReAct framework.\n\n"
             "Thought: Reason about the current task\n"
             "Action: Choose tool or cognitive operation\n"
             "Observation: Reflect on results\n\n"
             "Available tools: {tools}\nTask: {task}\nContext: {context}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        context = (
            f"Reflexion Depth: {state['reflexion_depth']}\n"
            f"Previous Decisions: {len(state['agent_decisions'])}\n"
            f"Self-Consistency: {state['self_consistency_score']:.2f}\n"
            f"Semantic Route: {state['semantic_route']}"
        )
        response = await self.llm.ainvoke(
            prompt.format_messages(
                tools=[t.name for t in self.tools],
                task=state["current_task"],
                context=context,
                messages=state["messages"],
            )
        )
        reasoning = self._parse_react_response(response.content)
        self.reasoning_trace.append(reasoning)
        if reasoning.get("action"):
            reasoning["observation"] = await self._execute_action(reasoning["action"])
        return reasoning

    def _parse_react_response(self, content: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "thought": "", "action": None, "observation": None,
            "timestamp": datetime.now().isoformat(),
        }
        current = None
        for line in content.split("\n"):
            if line.startswith("Thought:"):
                current = "thought"
                result["thought"] = line.replace("Thought:", "").strip()
            elif line.startswith("Action:"):
                current = "action"
                result["action"] = line.replace("Action:", "").strip()
            elif line.startswith("Observation:"):
                current = "observation"
                result["observation"] = line.replace("Observation:", "").strip()
            elif current and line.strip():
                result[current] = (result[current] or "") + " " + line.strip()
        return result

    async def _execute_action(self, action_str: str) -> str:
        for tool in self.tools:
            if tool.name.lower() in action_str.lower():
                try:
                    return str(await tool.arun(action_str))
                except Exception as e:
                    return f"Error executing {tool.name}: {e}"
        return "No matching tool found for action"


# ==================== Meta-Agentic Gödel Agent ====================

class MetaGodelAgent:
    """
    Self-referential agent implementing Gödel-inspired meta-reasoning.

    Storage
    -------
    - DuckDB   : SQL queries against local parquet / CSV files (replaces SparkSQL)
    - ChromaDB : persistent vector memory + similarity search (replaces Delta Lake + FAISS)

    Pipeline (LangGraph)
    --------------------
    route_task → retrieve_context → reason_and_act → reflect_and_verify
                      ↑_____________________(loop if score < 0.8)__|
                                                                    ↓
                                                            update_memory → END
    """

    def __init__(
        self,
        db_path: str = "./agent.duckdb",
        chroma_dir: str = "./chroma_db",
    ):
        self.agent_id = f"godel_agent_{datetime.now().timestamp()}"
        self.db_path = db_path

        self.vector_store = LocalVectorStore(persist_dir=chroma_dir)
        self.graph_rag = GraphRAGEngine(self.vector_store)
        self.semantic_router = AgentSemanticRouter()

        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514", temperature=0.7, max_tokens=4000
        )
        self.tools = self._initialize_tools()
        self.neuro_react = NeuroReActAgent(self.llm, self.tools)

        self.workflow = self._build_langgraph()
        self.checkpointer = MemorySaver()

        mlflow.set_experiment(f"/meta-godel-agent/{self.agent_id}")

    # ── tools ────────────────────────────────────────────────────────────────

    def _initialize_tools(self) -> List[BaseTool]:
        db_path = self.db_path
        vector_store = self.vector_store
        graph_rag = self.graph_rag

        class DuckDBSQLTool(BaseTool):
            name: str = "duckdb_sql_query"
            description: str = "Execute DuckDB SQL queries against local data files (parquet, CSV, JSON)"

            def _run(self, query: str) -> str:
                try:
                    conn = duckdb.connect(db_path)
                    df = conn.execute(query).fetchdf()
                    conn.close()
                    return df.to_json(orient="records")
                except Exception as e:
                    return f"SQL Error: {e}"

        class VectorSearchTool(BaseTool):
            name: str = "vector_memory_search"
            description: str = "Search vector memory for relevant context"

            def _run(self, query: str) -> str:
                return json.dumps(vector_store.similarity_search(query, k=5), indent=2)

        class GraphTraversalTool(BaseTool):
            name: str = "graph_traversal"
            description: str = "Traverse knowledge graph for connected concepts"

            def _run(self, query: str) -> str:
                return json.dumps(graph_rag.hierarchical_retrieval(query, depth=2), indent=2)

        return [DuckDBSQLTool(), VectorSearchTool(), GraphTraversalTool()]

    # ── LangGraph workflow ────────────────────────────────────────────────────

    def _build_langgraph(self) -> StateGraph:
        wf = StateGraph(GodelAgentState)
        wf.add_node("route_task", self._route_task_node)
        wf.add_node("retrieve_context", self._retrieve_context_node)
        wf.add_node("reason_and_act", self._reason_and_act_node)
        wf.add_node("reflect_and_verify", self._reflect_and_verify_node)
        wf.add_node("update_memory", self._update_memory_node)

        wf.set_entry_point("route_task")
        wf.add_edge("route_task", "retrieve_context")
        wf.add_edge("retrieve_context", "reason_and_act")
        wf.add_edge("reason_and_act", "reflect_and_verify")
        wf.add_conditional_edges(
            "reflect_and_verify",
            self._should_continue_reflecting,
            {"continue": "retrieve_context", "finalize": "update_memory"},
        )
        wf.add_edge("update_memory", END)
        return wf.compile(checkpointer=self.checkpointer)

    # ── nodes ─────────────────────────────────────────────────────────────────

    async def _route_task_node(self, state: GodelAgentState) -> GodelAgentState:
        state["semantic_route"] = self.semantic_router.route_task(state["current_task"])
        mlflow.log_param("semantic_route", state["semantic_route"])
        return state

    async def _retrieve_context_node(self, state: GodelAgentState) -> GodelAgentState:
        context = self.graph_rag.hierarchical_retrieval(
            state["current_task"], depth=state["reflexion_depth"] + 1
        )
        state["graph_context"] = {
            "retrieved_nodes": len(context),
            "context_summary": context[:3],
        }
        state["messages"].append(
            SystemMessage(content=f"Retrieved context: {json.dumps(context[:2])}")
        )
        return state

    async def _reason_and_act_node(self, state: GodelAgentState) -> GodelAgentState:
        reasoning = await self.neuro_react.reason_act_observe(state)
        state["agent_decisions"].append(reasoning)
        state["tools_used"].append(reasoning.get("action", ""))
        state["messages"].append(AIMessage(content=json.dumps(reasoning)))
        mlflow.log_metric("reasoning_steps", len(state["agent_decisions"]))
        return state

    async def _reflect_and_verify_node(self, state: GodelAgentState) -> GodelAgentState:
        reflection_prompt = (
            f"Reflect on your reasoning process:\n\n"
            f"Task: {state['current_task']}\n"
            f"Decisions made: {len(state['agent_decisions'])}\n"
            f"Current reflexion depth: {state['reflexion_depth']}\n\n"
            "Evaluate: logical consistency, completeness, biases, information gaps.\n"
            "Provide a self-consistency score (0-1) and your reflection."
        )
        reflection = await self.llm.ainvoke([SystemMessage(content=reflection_prompt)])
        score = self._extract_consistency_score(reflection.content)
        state["self_consistency_score"] = score
        state["reflexion_depth"] += 1
        mlflow.log_metric("self_consistency_score", score)
        mlflow.log_metric("reflexion_depth", state["reflexion_depth"])
        return state

    def _should_continue_reflecting(self, state: GodelAgentState) -> str:
        if state["self_consistency_score"] < 0.8 and state["reflexion_depth"] < 3:
            return "continue"
        return "finalize"

    async def _update_memory_node(self, state: GodelAgentState) -> GodelAgentState:
        self.vector_store.add_memory(
            content=json.dumps(state["agent_decisions"]),
            metadata={
                "task": state["current_task"],
                "reflexion_depth": str(state["reflexion_depth"]),
                "consistency_score": str(state["self_consistency_score"]),
            },
            agent_id=self.agent_id,
        )
        for decision in state["agent_decisions"]:
            if decision.get("observation"):
                self.graph_rag.add_knowledge_node(
                    content=decision["observation"],
                    node_type="reasoning_outcome",
                    connections=[state["current_task"]],
                    agent_id=self.agent_id,
                )
        return state

    # ── helpers ───────────────────────────────────────────────────────────────

    def _extract_consistency_score(self, content: str) -> float:
        match = re.search(r"(\d+\.?\d*)\s*/\s*1\.?0?|(\d+\.?\d*)", content)
        if match:
            return min(float(match.group(1) or match.group(2)), 1.0)
        return 0.5

    # ── public API ────────────────────────────────────────────────────────────

    async def execute_task(self, task: str) -> Dict[str, Any]:
        with mlflow.start_run(run_name=f"task_{datetime.now().timestamp()}"):
            mlflow.log_param("task", task)
            mlflow.log_param("agent_id", self.agent_id)

            initial_state: GodelAgentState = {
                "messages": [HumanMessage(content=task)],
                "current_task": task,
                "reflexion_depth": 0,
                "proof_trace": [],
                "vector_memory_ids": [],
                "graph_context": {},
                "agent_decisions": [],
                "semantic_route": None,
                "self_consistency_score": 0.0,
                "iteration_count": 0,
                "tools_used": [],
                "error_state": None,
            }

            try:
                final_state = await self.workflow.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": self.agent_id}},
                )
                result = {
                    "status": "success",
                    "task": task,
                    "decisions": final_state["agent_decisions"],
                    "reflexion_depth": final_state["reflexion_depth"],
                    "consistency_score": final_state["self_consistency_score"],
                    "semantic_route": final_state["semantic_route"],
                    "tools_used": list(set(filter(None, final_state["tools_used"]))),
                }
                mlflow.log_dict(result, "execution_result.json")
                return result
            except Exception as e:
                error_result = {"status": "error", "task": task, "error": str(e)}
                mlflow.log_dict(error_result, "execution_error.json")
                return error_result


# ==================== Entry Point ====================

async def main():
    agent = MetaGodelAgent(db_path="./agent.duckdb", chroma_dir="./chroma_db")

    tasks = [
        "Analyze customer churn patterns in the last quarter",
        "Generate novel feature engineering approaches for recommendation system",
        "Reflect on the consistency of our ML pipeline decisions",
    ]

    results = []
    for task in tasks:
        print(f"\n{'='*60}\nExecuting: {task}\n{'='*60}\n")
        result = await agent.execute_task(task)
        results.append(result)
        print(f"\nResult: {json.dumps(result, indent=2)}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
