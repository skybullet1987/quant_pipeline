import json
from pathlib import Path

state_file = Path('data/live_execution_state.json')
if state_file.exists():
    data = json.loads(state_file.read_text())
    print(f"=== ORDER EXECUTION SUMMARY ({data.get('timestamp')}) ===")
    print(f"Live Equity: ${data.get('account_equity', 0):,.2f}")
    print(f"Total Actions Dispatched: {data.get('actions_dispatched', 0)}\n")
    
    for act in data.get('results', []):
        coin = act.get('coin')
        action = act.get('action')
        res = act.get('result', {})
        print(f"{coin:<10} | {action:<10} | Response: {res}")
else:
    print("No execution report found.")
