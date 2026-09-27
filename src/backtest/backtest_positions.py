from typing import Dict, Tuple, List
from src.backtest.backtest_models import Position

def evaluate_intrabar_stops(
    positions: Dict[str, Position],
    cur_rows: dict,
    next_rows: dict,
    capital: float,
    use_ratchet: bool = False,
    disaster_stop_atr: float = 3.5
) -> Tuple[float, List[str]]:
    bar_pnl = 0.0
    stopped = []
    for sym, pos in list(positions.items()):
        if sym not in next_rows or sym not in cur_rows: continue
        r_nxt, r_cur = next_rows[sym], cur_rows[sym]
        p_cur, p_nxt_hi, p_nxt_lo, p_nxt_cl = r_cur["close"], r_nxt["high"], r_nxt["low"], r_nxt["close"]
        atr, entry_px = pos.atr, pos.entry_px

        # Calculate active stop distance
        if not use_ratchet:
            pos.current_sl_px = entry_px - (disaster_stop_atr * atr) if pos.is_long else entry_px + (disaster_stop_atr * atr)

        if pos.is_long:
            if p_nxt_lo <= pos.current_sl_px:
                exit_px = min(p_cur, pos.current_sl_px)
                bar_pnl += (capital * pos.weight * ((exit_px - p_cur) / p_cur)) - (capital * abs(pos.weight) * 0.00145)
                stopped.append(sym)
            else:
                pos.peak_px = max(pos.peak_px, p_nxt_hi)
                mfe = (pos.peak_px - entry_px) / (atr + 1e-8)
                if use_ratchet:
                    if mfe >= 2.0: pos.current_sl_px, pos.stage = max(pos.current_sl_px, pos.peak_px - 2.0 * atr), "CHANDELIER"
                    elif mfe >= 1.5 and pos.stage == "INITIAL": pos.current_sl_px, pos.stage = max(pos.current_sl_px, entry_px + 0.10 * atr), "BREAKEVEN"
                bar_pnl += capital * pos.weight * ((p_nxt_cl - p_cur) / p_cur)
        else:
            if p_nxt_hi >= pos.current_sl_px:
                exit_px = max(p_cur, pos.current_sl_px)
                bar_pnl += (capital * abs(pos.weight) * ((p_cur - exit_px) / p_cur)) - (capital * abs(pos.weight) * 0.00145)
                stopped.append(sym)
            else:
                pos.trough_px = min(pos.trough_px, p_nxt_lo)
                mfe = (entry_px - pos.trough_px) / (atr + 1e-8)
                if use_ratchet:
                    if mfe >= 2.0: pos.current_sl_px, pos.stage = min(pos.current_sl_px, pos.trough_px + 2.0 * atr), "CHANDELIER"
                    elif mfe >= 1.5 and pos.stage == "INITIAL": pos.current_sl_px, pos.stage = min(pos.current_sl_px, entry_px - 0.10 * atr), "BREAKEVEN"
                bar_pnl += capital * abs(pos.weight) * ((p_cur - p_nxt_cl) / p_cur)
    return bar_pnl, stopped

def sync_positions(target_weights: dict, positions: Dict[str, Position], cur_rows: dict, grp: int, disaster_stop_atr: float = 3.5) -> float:
    all_syms = set(list(target_weights.keys()) + list(positions.keys()))
    turnover = 0.0
    for s in all_syms:
        w_tgt = target_weights.get(s, 0.0)
        w_cur = positions[s].weight if s in positions else 0.0
        turnover += abs(w_tgt - w_cur)
        if abs(w_tgt) < 0.005 and s in positions:
            del positions[s]
        elif abs(w_tgt) >= 0.005 and (s not in positions or (w_tgt * w_cur < 0)):
            r_c = cur_rows.get(s)
            if r_c:
                px, atr, is_l = r_c["close"], r_c["atr_14"], w_tgt > 0
                sl = px - (disaster_stop_atr * atr) if is_l else px + (disaster_stop_atr * atr)
                positions[s] = Position(s, is_l, w_tgt, px, atr, sl, px, px, "INITIAL", grp)
        elif s in positions:
            positions[s].weight = w_tgt
    return turnover
