with open('run_walk_forward_4h.py', 'r') as file:
    content = file.read()

# Replace Kraken fees with standard DEX fees
content = content.replace("TAKER_FEE = 0.0026", "TAKER_FEE = 0.00035")  # 3.5 bps
content = content.replace("MAKER_FEE = 0.0016", "MAKER_FEE = 0.0")      # 0 bps
content = content.replace("SLIPPAGE = 0.0005", "SLIPPAGE = 0.0002")     # Tighter slippage on deep DEX order books

with open('run_walk_forward_4h_dex_fees.py', 'w') as file:
    file.write(content)
