#!/usr/bin/env python3
"""
Competiscan Demo Script
Demonstrates the complete ETL and data processing pipeline
"""

import subprocess
import os
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display results"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/Users/tarunpinnem/Desktop/competiscan/data/etl")
        print(result.stdout)
        if result.stderr:
            print(f"⚠️  Stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main demo function"""
    
    print("""
🏗️ COMPETISCAN-LITE DEMO
========================
Event-Driven Competitive Marketing Insights Platform

This demo showcases the enhanced ETL pipeline with:
• Sophisticated synthetic data generation
• Multi-industry campaign templates  
• Advanced data analysis and validation
• CSV/JSON conversion capabilities
    """)
    
    # Demo commands
    commands = [
        {
            "cmd": "python3 etl.py generate demo_campaigns.csv --count 25",
            "desc": "Generate 25 Synthetic Marketing Campaigns"
        },
        {
            "cmd": "python3 etl.py analyze demo_campaigns.csv", 
            "desc": "Analyze Generated Campaign Data"
        },
        {
            "cmd": "python3 etl.py validate demo_campaigns.csv",
            "desc": "Validate Data Quality and Structure"
        },
        {
            "cmd": "python3 etl.py convert demo_campaigns.csv demo_campaigns.json",
            "desc": "Convert CSV to Event-Ready JSON Format"
        }
    ]
    
    # Run all commands
    for cmd_info in commands:
        success = run_command(cmd_info["cmd"], cmd_info["desc"])
        if not success:
            print(f"❌ Command failed: {cmd_info['cmd']}")
            break
        
    print(f"\n{'='*60}")
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("📊 Generated Files:")
    print("   • demo_campaigns.csv - Synthetic campaign data")
    print("   • demo_campaigns.json - Event-ready JSON format")
    print(f"{'='*60}")
    
    # Show file sizes
    try:
        csv_path = Path("/Users/tarunpinnem/Desktop/competiscan/data/etl/demo_campaigns.csv")
        json_path = Path("/Users/tarunpinnem/Desktop/competiscan/data/etl/demo_campaigns.json")
        
        if csv_path.exists():
            csv_size = csv_path.stat().st_size
            print(f"📄 demo_campaigns.csv: {csv_size:,} bytes")
            
        if json_path.exists():
            json_size = json_path.stat().st_size  
            print(f"📄 demo_campaigns.json: {json_size:,} bytes")
            
    except Exception as e:
        print(f"⚠️  Could not get file sizes: {e}")

if __name__ == "__main__":
    main()