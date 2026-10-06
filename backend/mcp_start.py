import subprocess
import sys


hotel_mcp = subprocess.Popen(
    [sys.executable, "hotel_mcp_server/server.py"]
)

transport_mcp = subprocess.Popen(
    [sys.executable, "transport_mcp_server/server.py"]
)

try:
    hotel_mcp.wait()
    transport_mcp.wait()

except KeyboardInterrupt:
    hotel_mcp.terminate()
    transport_mcp.terminate()

    hotel_mcp.wait()
    transport_mcp.wait()