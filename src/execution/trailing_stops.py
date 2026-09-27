import dataclasses

@dataclasses.dataclass
class PositionRiskState:
    symbol: str
    entry_price: float
    side: str
    atr: float
    mfe: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = float("inf")
    current_stop_price: float = 0.0
    stage: str = "STAGE_1_HARD_STOP"

class AsymmetricLifecycleStopManager:
    def initialize_position(self, symbol: str, entry_price: float, side: str, atr: float) -> PositionRiskState:
        if side == "BUY":
            initial_stop = entry_price - 1.2 * atr
            highest = entry_price
            lowest = entry_price
        else:
            initial_stop = entry_price + 1.2 * atr
            highest = entry_price
            lowest = entry_price

        return PositionRiskState(
            symbol=symbol,
            entry_price=entry_price,
            side=side,
            atr=atr,
            mfe=0.0,
            highest_price=highest,
            lowest_price=lowest,
            current_stop_price=initial_stop,
            stage="STAGE_1_HARD_STOP"
        )

    def update_position_state(self, pos: PositionRiskState, current_price: float) -> tuple[PositionRiskState, bool]:
        if pos.side == "BUY":
            pos.highest_price = max(pos.highest_price, current_price)
            pos.mfe = max(pos.mfe, current_price - pos.entry_price)
            
            if pos.mfe >= 1.8 * pos.atr:
                pos.stage = "STAGE_3_CHANDELIER"
                pos.current_stop_price = max(pos.current_stop_price, pos.highest_price - 2.0 * pos.atr)
            elif pos.mfe >= 1.0 * pos.atr:
                pos.stage = "STAGE_2_BREAKEVEN"
                pos.current_stop_price = max(pos.current_stop_price, pos.entry_price + 0.1 * pos.atr)
                
            should_exit = current_price <= pos.current_stop_price
        else:
            pos.lowest_price = min(pos.lowest_price, current_price)
            pos.mfe = max(pos.mfe, pos.entry_price - current_price)
            
            if pos.mfe >= 1.8 * pos.atr:
                pos.stage = "STAGE_3_CHANDELIER"
                pos.current_stop_price = min(pos.current_stop_price, pos.lowest_price + 2.0 * pos.atr)
            elif pos.mfe >= 1.0 * pos.atr:
                pos.stage = "STAGE_2_BREAKEVEN"
                pos.current_stop_price = min(pos.current_stop_price, pos.entry_price - 0.1 * pos.atr)
                
            should_exit = current_price >= pos.current_stop_price

        return pos, should_exit
