import sys
import uuid
from typing import List

# Setup path so we can import from the project
sys.path.append(".")

from db.client import (
    upsert_business, 
    upsert_inventory, 
    create_appointment,
    get_appointments_by_session
)
from agent.graph import run_agent_turn

# ---------------------------------------------------------
# 1. Setup Mock Business & External Files
# ---------------------------------------------------------
def setup_mock_data():
    print(">>> 1. Populating DB with mock data (Simulating files) ...")
    
    business_name = "Test Mock Pizzeria & Clinic"
    biz = upsert_business(
        name=business_name,
        business_type="mixed",
        pdf_path="N/A",  # Assuming RAG is simulated or empty for this test
        description="A place that sells pizza and takes appointments."
    )
    biz_id = biz["id"]

    # Simulating Inventory File read -> DB insert
    inventory_items = [
        {"item_name": "pizza abc", "stock_quantity": 2, "wait_time_minutes": 30},
        {"item_name": "cola", "stock_quantity": 100, "wait_time_minutes": 0}
    ]
    for item in inventory_items:
        upsert_inventory(
            business_id=biz_id,
            item_name=item["item_name"],
            quantity=item["stock_quantity"],
            wait_time_minutes=item["wait_time_minutes"]
        )

    # Simulating Calendar File read -> DB insert
    # Pre-book an appointment for tomorrow at 10:00 AM
    pre_booked_date = "2026-03-27T10:00:00"
    create_appointment(
        session_id=str(uuid.uuid4()),
        business_id=biz_id,
        service="Consultation",
        scheduled_at=pre_booked_date,
        duration_min=30,
        provider="Dr. Smith"
    )

    return biz_id, business_name

# ---------------------------------------------------------
# 2. Run Chat Simulator
# ---------------------------------------------------------
def simulate_chat(biz_id: str, biz_name: str, session_id: str, prompts: List[str]):
    history = []
    print(f"\n================ STARTING SESSION: {session_id[:8]} ================")
    for user_msg in prompts:
        print(f"\n[USER]: {user_msg}")
        resp = run_agent_turn(
            user_message=user_msg,
            session_id=session_id,
            business_id=biz_id,
            business_name=biz_name,
            conversation_history=history
        )
        agent_msg = resp["response"]
        print(f"[AGENT]: {agent_msg}")
        
        # Tools used:
        if resp.get("tool_calls"):
            print(f"   (Tools Used: {[t['name'] for t in resp['tool_calls']]})")

        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": agent_msg})
    
    print("\n================ END SESSION ================")


# ---------------------------------------------------------
# 3. Test Scenarios
# ---------------------------------------------------------
def main():
    biz_id, biz_name = setup_mock_data()

    # SCENARIO 1: Order with Inventory Shortage
    session_1 = str(uuid.uuid4())
    prompts_1 = [
        "I would like to order 5 pieces of 'pizza abc', and 2 colas.",
        "Yes, I am willing to wait 30 minutes for the pizzas. Please proceed.",
        "That's all for the order.",
        "Please deliver it to 123 Main St.",
        "Yes, I confirm the order."
    ]
    print("\n\n--- RUNNING SCENARIO 1: Inventory Shortage Handling ---")
    simulate_chat(biz_id, biz_name, session_1, prompts_1)

    # SCENARIO 2: Scheduling Flow (Conflict, Book, Reschedule, Cancel)
    session_2 = str(uuid.uuid4())
    prompts_2 = [
        "I'd like to book a Consultation with Dr. Smith for 2026-03-27 at 10:00 AM.",
        "Okay, what about 11:00 AM on the same day?",
        "Yes, proceed with booking it at 11 AM under the name Jane Doe.",
        "Actually, can you reschedule my appointment to 2026-03-28 at 2:00 PM?",
        "Wait, just cancel the appointment entirely."
    ]
    print("\n\n--- RUNNING SCENARIO 2: End-to-End Scheduling Flow ---")
    simulate_chat(biz_id, biz_name, session_2, prompts_2)


if __name__ == "__main__":
    import os
    # We must have .env with GOOGLE_API_KEY
    if not os.getenv("GOOGLE_API_KEY") and not os.path.exists(".env"):
        print("Warning: .env / GOOGLE_API_KEY not found. LLM calls may fail.")
    main()
