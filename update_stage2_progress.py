with open("run_100_feature_tournament.py", "r") as f:
    code = f.read()

target_loop = """for f in surviving_stage1:"""
progress_loop = """for idx, f in enumerate(surviving_stage1, 1):
    print(f"--> [{idx:02d}/{len(surviving_stage1):02d}] Evaluating: {f:<42}", end="", flush=True)"""

code = code.replace(target_loop, progress_loop)

print_res = """    delta_ev_l = top_ev_l - base_ev_l
    delta_ev_s = top_ev_s - base_ev_s"""
print_res_new = """    delta_ev_l = top_ev_l - base_ev_l
    delta_ev_s = top_ev_s - base_ev_s
    print(f"| L_ΔEV: {delta_ev_l:>+5.0f} bps | S_ΔEV: {delta_ev_s:>+5.0f} bps")"""

code = code.replace(print_res, print_res_new)

with open("run_100_feature_tournament.py", "w") as f:
    f.write(code)
print("--> Progress tracking successfully injected.")
