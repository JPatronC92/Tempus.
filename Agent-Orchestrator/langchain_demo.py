"""
LangChain + Tempus DDB Integration Demo
---------------------------------------
This script demonstrates how to wrap a modern AI Agent (like a LangChain LLM) 
with the Tempus SDK so it cannot take real-world actions without cryptographic approval.

To run with a real LLM, set your OPENAI_API_KEY environment variable. 
Otherwise, it will run in 'Offline Mock' mode for local, seamless demonstrations.
"""

import os
import json
import time

# 1. Import Tempus SDK
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../Tempus-Engine/tempus-python')))
from tempus_sdk import TempusClient

# =====================================================================
# THE AI AGENT (LLM) LOGIC
# =====================================================================
class BankAgentLLM:
    """A simulated LangChain-style AI Agent built to process loan applications."""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if self.api_key:
            print("🧠 Initialized REAL Agent (OpenAI Connected).")
        else:
            print("🧠 Initialized MOCK Agent (Offline Mode).")

    def process_application(self, applicant_profile: str) -> dict:
        """
        The LLM reads a natural language profile and structures it into JSON data.
        In a real scenario, this uses an LLM's `function_calling` or structured output.
        """
        print(f"\n[Agent] Reading raw text profile: '{applicant_profile[:40]}...'")
        time.sleep(1) # Simulate thinking time
        
        # Simulated "Structured Extraction" by the LLM
        if "bankrupt" in applicant_profile.lower():
            extracted_json = {"credit_score": 450, "amount": 50000, "is_internal": False}
        else:
            extracted_json = {"credit_score": 750, "amount": 10000, "is_internal": False}
            
        print(f"[Agent] Extracting structured data: {json.dumps(extracted_json)}")
        return extracted_json

# =====================================================================
# THE EXECUTION WORKFLOW
# =====================================================================
def run_governed_ai_workflow():
    print("==================================================")
    print("🤖 AI Execution Workflow WITH Tempus Governance")
    print("==================================================\n")

    # 1. Setup the Tempus Client (The "Notary")
    tempus = TempusClient(api_url="http://localhost:8001/api/v1")
    
    # 2. Setup the AI Agent
    llm_agent = BankAgentLLM()

    # 3. Assume we received an email or form from a customer:
    customer_email = "Hi, my name is John. I have a great job but I went bankrupt " \
                     "last year due to medical bills. I need a $50,000 loan to start over."
                     
    # 4. The Agent "thinks" and generates the JSON payload
    agent_output_data = llm_agent.process_application(customer_email)
    
    # 5. THE CRUCIAL GOVERNANCE STEP
    # ---------------------------------------------------------
    # Before the agent is allowed to trigger the "Disburse Funds" API, 
    # it MUST ask Tempus for a cryptographic receipt.
    print("\n[Security] Requesting Tempus Governance Approval...")
    
    try:
        response = tempus.request_decision(
            agent_id="LangChain-Loan-Evaluator",
            rule_name="credit_policy_v1", # The strict business rule
            context={"source": "customer_email_processor"},
            input_data=agent_output_data
        )
        
        # 6. Act upon the Governance response
        if response.get("approved"):
            print("\n✅ Tempus Approved the AI's action.")
            print(f"💰 [Real World Action] Disbursing ${agent_output_data['amount']} to John!")
        else:
            print("\n❌ Tempus BLOCKED the AI's action.")
            print(f"🛑 [Intervention] Action stopped. Reason given by engine: {response.get('reason')}")
            
        print(f"\n🧾 Cryptographic Receipt (Immutable Evidence):")
        print(f"   {response.get('receipt')}")
            
    except Exception as e:
        print(f"\n[!] Governance Validation Failed: {str(e)}")
        print("    Ensure docker compose is running (localhost:8001)")

if __name__ == "__main__":
    run_governed_ai_workflow()
