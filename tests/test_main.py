from dotenv import load_dotenv
load_dotenv('/home/popic/GhostGoat/.env')
print('1. Env loaded', flush=True)

import asyncio, requests
print('2. Imports done', flush=True)

from core.brain.agents.pmmago import build_enterprise_pmmago
print('3. Import successful', flush=True)

def llm_call(prompt):
    resp = requests.post('http://localhost:11434/api/chat', 
                       json={'model': 'qwen2.5:0.5b', 'messages': [{'role': 'user', 'content': prompt}], 'stream': False}, 
                       timeout=60)
    return resp.json()['message']['content']

orch = build_enterprise_pmmago(llm_call, n_workers=1)
print('4. Orchestrator built', flush=True)

async def test():
    print('5. Inside async test()', flush=True)
    result = await orch.execute_async({'description': 'test'})
    print('6. Result:', result, flush=True)

print('7. About to call asyncio.run()', flush=True)
asyncio.run(test())
print('8. asyncio.run() returned!', flush=True)
