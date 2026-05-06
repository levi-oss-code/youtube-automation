#!/usr/bin/env python3
"""Fix the port binding issue in deployed main.py"""

with open('/app/main.py', 'r') as f:
    content = f.read()

# Replace the old start_http_server function with the new one
old_function = '''def start_http_server() -> None:
    """Start a tiny HTTP server for health checks and manual trigger."""
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"HTTP server listening on 0.0.0.0:{port}")'''

new_function = '''def start_http_server() -> None:
    """Start a tiny HTTP server for health checks and manual trigger."""
    # Try PORT first (Render), fallback to 8001 if taken
    port = int(os.getenv("PORT", "8000"))
    server = None
    for try_port in [port, 8001]:
        try:
            server = HTTPServer(("0.0.0.0", try_port), HealthHandler)
            port = try_port
            break
        except OSError:
            continue
    
    if not server:
        raise RuntimeError("Could not bind to any port (tried PORT and 8001)")
    
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"HTTP server listening on 0.0.0.0:{port}")'''

# Replace the function
if old_function in content:
    content = content.replace(old_function, new_function)
    with open('/app/main.py', 'w') as f:
        f.write(content)
    print("Successfully fixed port binding issue")
else:
    print("Old function not found - manual fix needed")
