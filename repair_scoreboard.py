file_path = "execute_hyperliquid_testnet.py"

with open(file_path, "r") as f:
    code = f.read()

# Replace fragile 2-tuple unpacking with explicit index slicing x[0], x[1]
code = code.replace(
    '[f"{k}: {v:.4f}" for k, v in top_longs]',
    '[f"{x[0]}: {float(x[1]):.4f}" for x in top_longs]'
)
code = code.replace(
    '[f"{k}: {v:.4f}" for k, v in top_shorts]',
    '[f"{x[0]}: {float(x[1]):.4f}" for x in top_shorts]'
)

with open(file_path, "w") as f:
    f.write(code)

print("[SUCCESS] Fixed tuple unpacking in execute_hyperliquid_testnet.py")
