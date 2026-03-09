import requests
import json

base_url = "http://localhost:8001/api/v1/govern"

# 1. Decide
payload = {
    "agent_id": "crypto-tester-bot",
    "rule_name": "credit_policy_v1",
    "context": {"doc_ref": "123"},
    "input_data": {"credit_score": 750}
}
res = requests.post(f"{base_url}/decide", json=payload)
print("Decide response:", res.status_code, res.json())

if res.status_code == 200:
    receipt = res.json()["receipt"]
    dec = res.json()["decision"]
    print("Receipt:", receipt)
    
    # 2. Audit Valid
    audit_res = requests.get(f"{base_url}/audit/{receipt}")
    print("Audit Valid:", audit_res.json())

