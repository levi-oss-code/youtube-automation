#!/usr/bin/env python3
"""
Debug script to check what's happening in the deployed service
"""

import subprocess
import sys

def check_service_status():
    """Check what's happening in the deployed service"""
    
    # Try to run main.py and see what errors occur
    try:
        result = subprocess.run([sys.executable, "main.py"], 
                          capture_output=True, 
                          text=True, 
                          timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        print(f"Return code: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("Process timed out after 30 seconds")
    except Exception as e:
        print(f"Error running process: {e}")

if __name__ == "__main__":
    check_service_status()
