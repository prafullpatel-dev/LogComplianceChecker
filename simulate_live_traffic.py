import json
import time
import random
import os
from datetime import datetime, timezone

# Path to the mounted JSON file the Telemetry service watches
BUFFER_FILE = "services/telemetry_input_service/data/buffer.json"

MOCK_LOGS = [
    {
        "src_ip": "10.0.0.101",
        "dest_ip": "10.0.0.2",
        "event_type": "lateral_movement",
        "severity": "critical",
        "msg": "Suspicious lateral movement detected via SMB to Domain Controller",
        "user": "compromised_user",
        "hostname": "workstation-01",
        "device_vendor": "CrowdStrike",
        "device_product": "Falcon EDR",
        "source_type": "edr"
    },
    {
        "src_ip": "192.168.1.50",
        "dest_ip": "10.0.0.5",
        "event_type": "data_exfiltration",
        "severity": "critical",
        "msg": "Large file transfer detected to external IP from finance server",
        "user": "contractor_01",
        "hostname": "finance-db-01",
        "device_vendor": "CrowdStrike",
        "device_product": "Falcon EDR",
        "source_type": "edr"
    },
    {
        "src_ip": "10.0.0.99",
        "dest_ip": "10.0.0.200",
        "event_type": "unauthorized_access",
        "severity": "critical",
        "msg": "Unauthorized SSH access to production database server",
        "user": "unknown",
        "hostname": "prod-db-01",
        "device_vendor": "Splunk",
        "device_product": "Splunk Enterprise",
        "source_type": "siem"
    },
    {
        "src_ip": "10.0.0.22",
        "dest_ip": "10.0.0.1",
        "event_type": "brute_force",
        "severity": "high",
        "msg": "Brute force SSH attack detected - 500 attempts in 10 minutes",
        "user": "attacker",
        "hostname": "gateway-01",
        "device_vendor": "Splunk",
        "device_product": "Splunk Enterprise",
        "source_type": "siem"
    },
    {
        "src_ip": "10.0.0.150",
        "dest_ip": "10.0.0.200",
        "event_type": "privilege_escalation",
        "severity": "critical",
        "msg": "Successful sudo to root from non-admin user",
        "user": "guest_user",
        "hostname": "prod-app-05",
        "device_vendor": "Splunk",
        "device_product": "Splunk Enterprise",
        "source_type": "siem"
    }
]

def main():
    print("==================================================")
    print("🚀 AUTOMATED LIVE TRAFFIC SIMULATOR ACTIVE 🚀")
    print("==================================================")
    print("This script simulates an active enterprise network by randomly injecting")
    print("critical security logs into the pipeline. Press [Ctrl+C] to stop.\n")
    
    if not os.path.exists(BUFFER_FILE):
        print(f"ERROR: Cannot find {BUFFER_FILE}")
        return

    while True:
        try:
            # Pick a random delay between 15 to 30 seconds
            delay = random.randint(15, 30)
            print(f"⏳ Waiting {delay} seconds until next network event...", end="\r", flush=True)
            time.sleep(delay)
            
            # Select random log
            new_log = random.choice(MOCK_LOGS).copy()
            
            # Update timestamp to RIGHT NOW to look super realistic
            new_log["timestamp"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Read existing file
            with open(BUFFER_FILE, "r") as f:
                logs = json.load(f)
                
            # Append new log
            logs.append(new_log)
            
            # Write back
            with open(BUFFER_FILE, "w") as f:
                json.dump(logs, f, indent=2)
                
            # Clear line and print injection success
            print(" " * 50, end="\r")
            print(f"🚨 [INJECTED] -> {new_log['event_type'].upper()}: {new_log['msg']}")
            print("   ↳ Your AI Agent is now processing this event in real-time...\n")
            
        except KeyboardInterrupt:
            print("\n\n🛑 Simulator Stopped. Your pipeline is sitting idle again.")
            break
        except Exception as e:
            print(f"\n❌ Error modifying file: {e}")
            break

if __name__ == "__main__":
    main()
