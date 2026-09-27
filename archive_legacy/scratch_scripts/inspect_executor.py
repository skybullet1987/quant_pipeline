from pathlib import Path

exec_path = Path("src/execution/hyperliquid_executor.py")
if exec_path.exists():
    print("=== src/execution/hyperliquid_executor.py ===")
    print(exec_path.read_text()[:1500])
else:
    print("File not found.")

try:
    import msgpack
    print("\n[msgpack] Available")
except ImportError:
    print("\n[msgpack] NOT Installed")

try:
    import hyperliquid
    print("[hyperliquid SDK] Available")
except ImportError:
    print("[hyperliquid SDK] NOT Installed")
