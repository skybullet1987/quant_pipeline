#!/usr/bin/env python3
"""
Round 14 Adversarial Audit Patcher (Release 2.4.4)
Applies all findings from the Principal Quantitative Code Audit:
  - FINDING-14-01: Preserve low_bid_detected_ts across STOP_CANCEL_PENDING & include in retry_due.
  - FINDING-14-02: 60/40 Iceberg Tranche split, IN_FLIGHT vs POSTED separation, and partial/cancel recovery.
  - FINDING-14-03: Prevent share-denominated entry fee double-deduction in calculate_realized_cash_pnl.
  - FINDING-14-04: Protect $0.99 capital-recycling order from transient spot timeouts & block zero-bid dumps.
  - FINDING-14-05: Offload synchronous save_state() fsync calls on the hot path to asyncio.to_thread.
  - FINDING-14-06: Enforce dynamic 6.0% NAV daily drawdown circuit breaker ($13.11 on $218.43) in live mode.
  - FINDING-14-07: Hex token_id support in redeem_settled_positions.py & portable Path.home() HMAC key path.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "scripts" else Path.cwd()

def apply_replace(filepath: Path, old: str, new: str, label: str) -> None:
    text = filepath.read_text(encoding="utf-8")
    if new in text:
        print(f"  [SKIP] {label} already applied in {filepath.name}")
        return
    # Strip comments and empty lines to check if code logic is already applied
    norm_new = "\n".join([line.strip() for line in new.splitlines() if line.strip() and not line.strip().startswith("#")])
    norm_text = "\n".join([line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")])
    if norm_new in norm_text:
        print(f"  [SKIP] {label} already applied in {filepath.name}")
        return
    if old not in text:
        raise RuntimeError(f"[ERROR] Target block for {label} not found in {filepath}")
    filepath.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]   Applied {label} in {filepath.name}")

def main():
    harvester_path = ROOT / "src/polymarket_research/polymarket_live_harvester.py"
    executor_path = ROOT / "src/polymarket_research/polymarket_live_executor.py"
    redeem_path = ROOT / "src/polymarket_research/redeem_settled_positions.py"
    test_r13_path = ROOT / "tests/test_round13_adversarial_audit.py"

    print("=" * 75)
    print("  APPLYING ROUND 14 ADVERSARIAL AUDIT PATCHES (RELEASE 2.4.4)")
    print("=" * 75)

    # 1. FINDING-14-01: STOP_CANCEL_PENDING in retry_due & preserve low_bid_detected_ts until cancel confirmed
    apply_replace(
        harvester_path,
        '''                    retry_due = (
                        pos.get("exit_order_status") in ({"UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                        and now_ts >= float(pos.get("next_unwind_retry_ts", 0.0) or 0.0)
                    )''',
        '''                    retry_due = (
                        pos.get("exit_order_status") == "STOP_CANCEL_PENDING"
                        or (
                            pos.get("exit_order_status") in ({"UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES)
                            and now_ts >= float(pos.get("next_unwind_retry_ts", 0.0) or 0.0)
                        )
                    )''',
        "FINDING-14-01A (Include STOP_CANCEL_PENDING in retry_due)",
    )

    apply_replace(
        harvester_path,
        '''                                        logger.warning(
                                            f"[LOW_BID_CONFIRMED] Position {tid}: best bid ${best_b:.4f} persisted below stop for "
                                            f"{now_ts - float(low_bid_ts):.2f}s. Triggering stop-loss unwind."
                                        )
                                        clob_sl_triggered = True
                                        pos.pop("low_bid_detected_ts", None)''',
        '''                                        logger.warning(
                                            f"[LOW_BID_CONFIRMED] Position {tid}: best bid ${best_b:.4f} persisted below stop for "
                                            f"{now_ts - float(low_bid_ts):.2f}s. Triggering stop-loss unwind."
                                        )
                                        clob_sl_triggered = True''',
        "FINDING-14-01B (Retain low_bid_detected_ts until resting exit cancel confirmed)",
    )

    apply_replace(
        harvester_path,
        '''                                self.executor.release_inventory(reservation_id=exit_oid)
                                pos["exit_order_id"] = None
                                exit_oid = None
                            pos["exit_order_status"] = "CANCELED_FOR_STOP_LOSS"''',
        '''                                self.executor.release_inventory(reservation_id=exit_oid)
                                pos["exit_order_id"] = None
                                exit_oid = None
                            pos.pop("low_bid_detected_ts", None)
                            pos["exit_order_status"] = "CANCELED_FOR_STOP_LOSS"''',
        "FINDING-14-01C (Clear low_bid_detected_ts after cancel confirmation)",
    )

    # 2. FINDING-14-02: 60/40 Iceberg Tranche Stepping & Canceled Tranche Recovery
    apply_replace(
        harvester_path,
        '''            self._release_position_reservations(pos, [str(oid)])
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
            self.save_state()
            return True''',
        '''            self._release_position_reservations(pos, [str(oid)])
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
            for t in pos.get("exit_tranches", []):
                if t.get("status") in {"POSTED", "IN_FLIGHT"}:
                    t["status"] = "PENDING"
            self.save_state()
            return True''',
        "FINDING-14-02A (Reset unexecuted tranche to PENDING on unknown exit recovery)",
    )

    apply_replace(
        harvester_path,
        '''        # Drop-in sequential iceberg tranche stepping for tickets > $50
        rem_total = size
        if float(pos.get("notional_usd", 0.0) or 0.0) > 50.0 and "exit_tranches" not in pos and rem_total >= 10.0:
            t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            entry_px = float(pos.get("entry_price", 0.70))
            pos["exit_tranches"] = [
                {"idx": 1, "size": t1_sz, "price": min(0.99, round(entry_px + 0.06, 4)), "status": "PENDING"},
                {"idx": 2, "size": t2_sz, "price": min(0.99, round(entry_px + 0.10, 4)), "status": "PENDING"},
            ]''',
        '''        # Drop-in sequential iceberg tranche stepping for tickets > $50 (60% / 40% split)
        rem_total = size
        if float(pos.get("notional_usd", 0.0) or 0.0) > 50.0 and "exit_tranches" not in pos and rem_total >= 10.0:
            t1_sz = float((Decimal(str(rem_total)) * Decimal("0.60")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
            entry_px = float(pos.get("entry_price", 0.70))
            pos["exit_tranches"] = [
                {"idx": 1, "size": t1_sz, "price": min(0.99, round(entry_px + 0.06, 4)), "status": "PENDING"},
                {"idx": 2, "size": t2_sz, "price": min(0.99, round(entry_px + 0.10, 4)), "status": "PENDING"},
            ]''',
        "FINDING-14-02B (60/40 Iceberg Tranche split in _attempt_maker_exit_post)",
    )

    apply_replace(
        harvester_path,
        '''        posted = self._apply_exit_post_result(pos, exit_res, size)
        if active_tranche is not None and (posted or (exit_res or {}).get("outcome_unknown")):
            active_tranche["status"] = "POSTED"''',
        '''        posted = self._apply_exit_post_result(pos, exit_res, size)
        if active_tranche is not None and posted:
            active_tranche["status"] = "POSTED"
        elif active_tranche is not None and (exit_res or {}).get("outcome_unknown"):
            active_tranche["status"] = "IN_FLIGHT"''',
        "FINDING-14-02C (Defer POSTED status until confirmed broadcast in _attempt_maker_exit_post)",
    )

    apply_replace(
        harvester_path,
        '''                if float(pos_record.get("notional_usd", 0.0) or 0.0) > 50.0 and rem_total >= 10.0:
                    t1_sz = float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    entry_px = float(pos_record.get("entry_price", 0.70))
                    pos_record["exit_tranches"] = [
                        {"idx": 1, "size": t1_sz, "price": min(0.99, round(entry_px + 0.06, 4)), "status": "PENDING"},
                        {"idx": 2, "size": t2_sz, "price": min(0.99, round(entry_px + 0.10, 4)), "status": "PENDING"},
                    ]
                    exit_size = t1_sz
                    exit_price = pos_record["exit_tranches"][0]["price"]
                    pos_record["target_exit_price"] = exit_price
                exit_res = await asyncio.to_thread(
                    self.executor.post_maker_exit_order,
                    token_id=token_id,
                    price=exit_price,
                    size=exit_size,
                    side="SELL",
                )
                posted = self._apply_exit_post_result(pos_record, exit_res, float(exit_size))
                if pos_record.get("exit_tranches") and (posted or (exit_res or {}).get("outcome_unknown")):
                    pos_record["exit_tranches"][0]["status"] = "POSTED"''',
        '''                if float(pos_record.get("notional_usd", 0.0) or 0.0) > 50.0 and rem_total >= 10.0:
                    t1_sz = float((Decimal(str(rem_total)) * Decimal("0.60")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    t2_sz = float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                    entry_px = float(pos_record.get("entry_price", 0.70))
                    pos_record["exit_tranches"] = [
                        {"idx": 1, "size": t1_sz, "price": min(0.99, round(entry_px + 0.06, 4)), "status": "PENDING"},
                        {"idx": 2, "size": t2_sz, "price": min(0.99, round(entry_px + 0.10, 4)), "status": "PENDING"},
                    ]
                    exit_size = t1_sz
                    exit_price = pos_record["exit_tranches"][0]["price"]
                    pos_record["target_exit_price"] = exit_price
                exit_res = await asyncio.to_thread(
                    self.executor.post_maker_exit_order,
                    token_id=token_id,
                    price=exit_price,
                    size=exit_size,
                    side="SELL",
                )
                posted = self._apply_exit_post_result(pos_record, exit_res, float(exit_size))
                if pos_record.get("exit_tranches") and posted:
                    pos_record["exit_tranches"][0]["status"] = "POSTED"
                elif pos_record.get("exit_tranches") and (exit_res or {}).get("outcome_unknown"):
                    pos_record["exit_tranches"][0]["status"] = "IN_FLIGHT"''',
        "FINDING-14-02D (60/40 Iceberg Tranche split & deferred POSTED in evaluate_shock_and_execute)",
    )

    apply_replace(
        harvester_path,
        '''                                tranches = pos.get("exit_tranches", [])
                                for t in tranches:
                                    if t.get("status") == "POSTED":
                                        t["status"] = "FILLED"''',
        '''                                tranches = pos.get("exit_tranches", [])
                                order_matched = float(summary.get("matched", 0.0) or 0.0)
                                for t in tranches:
                                    if t.get("status") in {"POSTED", "IN_FLIGHT"}:
                                        tranche_rem = max(0.0, round(float(t["size"]) - order_matched, 2))
                                        if tranche_rem <= 0.01:
                                            t["status"] = "FILLED"
                                        else:
                                            t["size"] = tranche_rem
                                            t["status"] = "PENDING"''',
        "FINDING-14-02E (Prevent canceled/unfilled Tranche 1 from being falsely marked FILLED)",
    )

    # 3. FINDING-14-03: Prevent share-fee double deduction when received < gross_entry_shares
    apply_replace(
        harvester_path,
        '''                net = float(received.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                pos["entry_shares"] = net''',
        '''                net = float(received.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
                if received < gross - Decimal("0.01"):
                    pos["entry_fee_asset"] = "SHARES"
                    pos["entry_fee_cash_usd"] = 0.0
                pos["entry_shares"] = net''',
        "FINDING-14-03 (Zero entry_fee_cash_usd when buy fee was deducted in outcome shares)",
    )

    # 4. FINDING-14-04: Zero-bid LIQUIDITY_CRISIS dump guard & $0.99 recycle transient spot timeout protection
    apply_replace(
        harvester_path,
        '''                                pos["liquidity_crisis_ts"] = now_ts
                                self.risk_halt = True
                                self._refresh_global_halt()
                            if not spot_crash_triggered:
                                continue''',
        '''                                pos["liquidity_crisis_ts"] = now_ts
                                self.risk_halt = True
                                self._refresh_global_halt()
                            continue''',
        "FINDING-14-04A (Never dump into a zero-bid orderbook during LIQUIDITY_CRISIS)",
    )

    apply_replace(
        harvester_path,
        '''                        holding_099_recycle = (
                            pos.get("exit_order_status") == "RESTING_099_CAPITAL_RECYCLE"
                            and bool(exit_oid)
                            and tte_rem >= 30.0
                            and spot_valid
                            and pin_thresh_pre > 0.0
                            and spot_disp >= pin_thresh_pre
                        )''',
        '''                        holding_099_recycle = (
                            pos.get("exit_order_status") == "RESTING_099_CAPITAL_RECYCLE"
                            and bool(exit_oid)
                            and tte_rem >= 30.0
                            and (not spot_valid or (pin_thresh_pre > 0.0 and spot_disp >= pin_thresh_pre))
                        )''',
        "FINDING-14-04B (Protect $0.99 recycle order from transient spot REST timeout)",
    )

    # 5. FINDING-14-05: Offload hot-path save_state() between entry fill and maker exit post
    apply_replace(
        harvester_path,
        '''            # IMMUTABLE PERSISTENCE: Save open position immediately before placing exit order
            self.active_positions[trade_id] = pos_record
            self.save_state()''',
        '''            # IMMUTABLE PERSISTENCE: Save open position immediately before placing exit order
            self.active_positions[trade_id] = pos_record
            await asyncio.to_thread(self.save_state)''',
        "FINDING-14-05 (Async offload save_state on hot path before maker exit placement)",
    )

    # 6. FINDING-14-06: Dynamic 6.0% NAV daily drawdown circuit breaker in live mode
    apply_replace(
        harvester_path,
        '''            kelly_ticket = _calc_kelly(
                p_model_for_sizing, first_ask, live_bankroll
            )''',
        '''            if self.risk_controller.max_daily_loss_usd == 75.0:
                self.risk_controller.max_daily_loss_usd = round(max(13.0, float(live_bankroll) * 0.06), 2)
            kelly_ticket = _calc_kelly(
                p_model_for_sizing, first_ask, live_bankroll
            )''',
        "FINDING-14-06 (Bind daily drawdown circuit breaker to 6.0% of live NAV)",
    )

    # 7. FINDING-14-07: Hex token_id support in redeem_settled_positions.py & Path.home() in executor
    apply_replace(
        redeem_path,
        '''        addr_padded = funder_address.lower().replace("0x", "").zfill(64)
        token_hex = hex(int(token_id))[2:].zfill(64)''',
        '''        addr_padded = funder_address.lower().replace("0x", "").zfill(64)
        token_int = int(token_id, 16) if str(token_id).startswith("0x") else int(token_id)
        token_hex = hex(token_int)[2:].zfill(64)''',
        "FINDING-14-07A (Hex token_id support in redeem_settled_positions.py)",
    )

    apply_replace(
        executor_path,
        '''        key_file = Path("/home/skybullet1987/.polymarket_reservation_hmac.key")''',
        '''        key_file = Path.home() / ".polymarket_reservation_hmac.key"''',
        "FINDING-14-07B (Portable Path.home() for HMAC reservation key)",
    )

    # Align test_round13_adversarial_audit.py with 60/40 Iceberg Tranche split
    if test_r13_path.exists():
        apply_replace(
            test_r13_path,
            '''    assert len(tranches) == 2
    assert tranches[0]["size"] == 50.0
    assert tranches[0]["price"] == 0.76  # +6¢
    assert tranches[0]["status"] == "POSTED"
    assert tranches[1]["size"] == 50.0
    assert tranches[1]["price"] == 0.80  # +10¢
    assert tranches[1]["status"] == "PENDING"
    # Only Tranche 1 was posted to the CLOB
    assert len(posted_args) == 1
    assert posted_args[0]["size"] == 50.0''',
            '''    assert len(tranches) == 2
    assert tranches[0]["size"] == 60.0
    assert tranches[0]["price"] == 0.76  # +6¢
    assert tranches[0]["status"] == "POSTED"
    assert tranches[1]["size"] == 40.0
    assert tranches[1]["price"] == 0.80  # +10¢
    assert tranches[1]["status"] == "PENDING"
    # Only Tranche 1 was posted to the CLOB
    assert len(posted_args) == 1
    assert posted_args[0]["size"] == 60.0''',
            "TEST-13-10 (Update tranche test assertions to 60/40 split)",
        )

    print("=" * 75)
    print("  ALL ROUND 14 PATCHES APPLIED SUCCESSFULLY.")
    print("  Run: venv/bin/pytest -q && systemctl --user restart polymarket-live-harvester")
    print("=" * 75)

if __name__ == "__main__":
    main()
