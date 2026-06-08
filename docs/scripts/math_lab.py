import asyncio
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import sympy as sp
from datasets import load_dataset
import uvicorn

app = FastAPI()

algebra_problems = [
    {"id": 1, "question": "Solve for x: 3x + 5 = 20", "answer": "5", "type": "linear"},
    {"id": 2, "question": "Factor: x² - 5x + 6", "answer": "(x-2)(x-3)", "type": "polynomial"},
]

try:
    gsm8k = load_dataset("openai/gsm8k", "main", split="train[:500]")
    for i, item in enumerate(gsm8k):
        algebra_problems.append({
            "id": 100 + i,
            "question": item["question"],
            "answer": item["answer"],
            "type": "word_problem"
        })
except:
    print("GSM8K not loaded - using generated problems")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws/math")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("action") == "get_problem":
                problem = random.choice(algebra_problems)
                await websocket.send_json({
                    "type": "problem",
                    "problem": problem
                })

            elif msg.get("action") == "submit_answer":
                problem_id = msg["problem_id"]
                user_answer = msg["answer"].strip()
                correct = False
                for p in algebra_problems:
                    if p["id"] == problem_id:
                        correct = user_answer.lower() == p["answer"].lower()
                        break
                await websocket.send_json({
                    "type": "feedback",
                    "correct": correct,
                    "correct_answer": p["answer"] if not correct else None
                })

            elif msg.get("action") == "solve_symbolic":
                expr = msg["expression"]
                try:
                    x = sp.symbols('x')
                    eq = sp.Eq(sp.sympify(expr.split('=')[0]), sp.sympify(expr.split('=')[1]))
                    solution = sp.solve(eq, x)
                    await websocket.send_json({"type": "solution", "solution": str(solution)})
                except:
                    await websocket.send_json({"type": "error", "message": "Invalid equation"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def get():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head><title>Live Algebra Lab</title></head>
<body>
    <h1>Real-time Algebra & Coding Practice</h1>
    <button onclick="getProblem()">Get New Problem</button>
    <div id="problem"></div>
    <input id="answer" placeholder="Your answer">
    <button onclick="submitAnswer()">Submit</button>
    <div id="feedback"></div>

    <script>
    let ws = new WebSocket("ws://localhost:8000/ws/math");
    let currentProblem = null;

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "problem") {
            currentProblem = data.problem;
            document.getElementById("problem").innerHTML = `<strong>${data.problem.question}</strong>`;
        } else if (data.type === "feedback") {
            document.getElementById("feedback").innerHTML = data.correct ? 
                "<span style='color:green'>Correct!</span>" : 
                `<span style='color:red'>Wrong. Answer: ${data.correct_answer}</span>`;
        } else if (data.type === "solution") {
            document.getElementById("feedback").innerHTML += `<br>SymPy Solution: ${data.solution}`;
        }
    };

    function getProblem() {
        ws.send(JSON.stringify({action: "get_problem"}));
    }

    function submitAnswer() {
        const answer = document.getElementById("answer").value;
        ws.send(JSON.stringify({
            "action": "submit_answer",
            problem_id: currentProblem.id,
            answer: answer
        }));
    }
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)