"""
Load simulation script - generates a batch of realistic, randomized
events and sends them through the REAL /events endpoint, so they go
through the actual engine (branching, enrichment, connector calls,
retries) exactly like a genuine event would.

This is what makes a claim like "50+ daily events" true and verifiable
rather than aspirational: after running this, you can open the
Execution Audit Trail or query /analytics/summary and see real rows
that resulted from real engine runs - not numbers made up for a resume.

Run with (backend must already be running):
    python simulate_load.py
    python simulate_load.py --count 100
    python simulate_load.py --count 50 --delay 0.5
"""

import argparse
import random
import time
import requests

API_URL = "http://localhost:8000"

REGIONS = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Pune", "Hyderabad", "Kolkata"]
CUSTOMER_IDS = ["CUST001", "CUST002", "CUST003", "CUST004", "CUST005", "CUST006"]
NAMES = ["Aashir", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Karan", "Divya"]
TRIGGER_TYPES = ["new_order", "new_signup"]


def generate_order_event() -> dict:
    return {
        "name": random.choice(NAMES),
        "region": random.choice(REGIONS),
        "amount": random.choice([150, 300, 750, 1200, 1500, 2500, 5000]),
        "customer_id": random.choice(CUSTOMER_IDS),
    }


def generate_signup_event() -> dict:
    return {
        "name": random.choice(NAMES),
        "region": random.choice(REGIONS),
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate a batch of real events against the running engine.")
    parser.add_argument("--count", type=int, default=50, help="Number of events to send (default: 50)")
    parser.add_argument("--delay", type=float, default=0.1, help="Seconds to wait between events (default: 0.1)")
    args = parser.parse_args()

    sent = 0
    errors = 0

    print(f"Sending {args.count} simulated events to {API_URL}/events ...")
    start_time = time.time()

    for i in range(args.count):
        trigger_type = random.choice(TRIGGER_TYPES)
        data = generate_order_event() if trigger_type == "new_order" else generate_signup_event()

        try:
            resp = requests.post(
                f"{API_URL}/events",
                json={"trigger_type": trigger_type, "data": data},
                timeout=10,
            )
            if resp.status_code == 200:
                sent += 1
            else:
                errors += 1
                print(f"  [{i+1}] HTTP {resp.status_code}: {resp.text[:100]}")
        except requests.RequestException as e:
            errors += 1
            print(f"  [{i+1}] Request failed: {e}")

        if (i + 1) % 10 == 0:
            print(f"  ...{i+1}/{args.count} sent")

        time.sleep(args.delay)

    elapsed = time.time() - start_time
    print(f"\nDone. {sent} events sent successfully, {errors} failed, in {elapsed:.1f}s.")
    print("\nTo verify these are real, check:")
    print(f"  curl {API_URL}/analytics/summary")
    print("  or open the Streamlit 'Execution Audit Trail' / 'Analytics' tabs.")


if __name__ == "__main__":
    main()
