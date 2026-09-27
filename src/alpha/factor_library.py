#!/usr/bin/env python3
"""
ECONOMICALLY MOTIVATED FACTOR LIBRARY & LINEAGE METADATA REGISTRY
=================================================================
A curated library of orthogonal crypto alpha signals computed strictly causally:
Every factor carries formal FactorMetadata lineage tracking:
- factor_id, version, formula, required_history_bars, source_tables, source_fields,
  sampling_frequency, availability_lag_ms, lookback_bars, horizons_supported,
  pit_required, neutralization_set, economic_hypothesis.

Initial Validation Set (4 Representative Starter Alphas):
1. residual_momentum: Cross-sectional 24h momentum residualized against BTC trend.
2. funding_divergence: Imbalance between synthetic funding rate/basis and price trend.
3. oi_price_divergence: Volume/OI accumulation vs sideways or falling price.
4. volume_taker_skew: Imbalance of aggressive volume relative to rolling baseline.

Secondary Expansion Set:
5. liquidation_absorption: Extreme volume spikes with narrow body (exhaustion/absorption).
6. volatility_expansion_skew: Upside vs downside candle range asymmetry.
7. basis_oracle_dislocation: Basis spread between exchange mark and composite oracle.
8. cross_sectional_dispersion: Divergence of asset return from altcoin cross-sectional median.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


@dataclass
class FactorMetadata:
    """
    Formal lineage definition answering:
    'Why does this factor exist, exactly what data created it, and what information was available when?'
    """
    factor_id: str
    version: str
    formula: str
    required_history_bars: int
    source_tables: List[str]
    source_fields: List[str]
    sampling_frequency: str  # "4H"
    availability_lag_ms: int  # e.g., 500ms post bar close
    lookback_bars: int
    horizons_supported: List[int]
    pit_required: bool
    neutralization_set: List[str]
    economic_hypothesis: str


METADATA_REGISTRY: Dict[str, FactorMetadata] = {
    "short_term_reversal": FactorMetadata(
        factor_id="alpha_01_short_term_reversal",
        version="2.0.0",
        formula="-(R_{i, 24h} - beta_{i, BTC} * R_{BTC, 24h})",
        required_history_bars=12,
        source_tables=["raw_candles_4h"],
        source_fields=["close", "timestamp_ms"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=6,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Cross-sectional idiosyncratic overextension in crypto perpetuals exhibits powerful short-horizon (4h-16h) mean-reversion once market-wide BTC beta is stripped.",
    ),
    "residual_momentum": FactorMetadata(
        factor_id="alpha_01_residual_momentum",
        version="1.2.0",
        formula="R_{i, 24h} - beta_{i, BTC} * R_{BTC, 24h}",
        required_history_bars=12,
        source_tables=["raw_candles_4h"],
        source_fields=["close", "timestamp_ms"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=6,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Cross-sectional crypto momentum contains idiosyncratic return information once market-wide BTC beta is stripped.",
    ),
    "funding_divergence": FactorMetadata(
        factor_id="alpha_02_funding_divergence",
        version="1.1.0",
        formula="((Close - EMA20) / ATR20) - ((Close - VWAP_proxy) / Close)",
        required_history_bars=36,
        source_tables=["raw_candles_4h"],
        source_fields=["open", "high", "low", "close", "volume"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=18,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Crowded speculative positioning generates excessive basis/funding premium that disconnects from spot trend, forecasting sharp mean-reverting unwinds.",
    ),
    "oi_price_divergence": FactorMetadata(
        factor_id="alpha_03_oi_price_divergence",
        version="1.1.0",
        formula="Z(Volume_12) * sign(-(Close - Close_12) / ATR)",
        required_history_bars=24,
        source_tables=["raw_candles_4h"],
        source_fields=["open", "high", "low", "close", "volume"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=12,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Smart-money inventory accumulation or absorption during price consolidation precedes explosive cross-sectional expansion.",
    ),
    "volume_taker_skew": FactorMetadata(
        factor_id="alpha_04_volume_taker_skew",
        version="1.2.0",
        formula="((Volume - mean(Volume, 18)) / std(Volume, 18)) * sign(Close - Open)",
        required_history_bars=24,
        source_tables=["raw_candles_4h"],
        source_fields=["open", "close", "volume"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=18,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Aggressive market order imbalances driving volume surges establish short-horizon order flow momentum and predictive continuation.",
    ),
    "liquidation_absorption": FactorMetadata(
        factor_id="alpha_07_liquidation_absorption",
        version="1.0.0",
        formula="(Volume / median(Volume, 12)) * (1 - (abs(Close - Open) / (High - Low))) * sign(Close - Mid)",
        required_history_bars=24,
        source_tables=["raw_candles_4h"],
        source_fields=["open", "high", "low", "close", "volume"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=12,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Passive limit orders absorbing extreme volume liquidations create local structural market exhaustion reversals.",
    ),
    "macro_residual_momentum": FactorMetadata(
        factor_id="alpha_06_macro_residual_momentum",
        version="1.0.0",
        formula="R_{i, 144h} - beta_{i, BTC} * R_{BTC, 144h}",
        required_history_bars=48,
        source_tables=["raw_candles_4h"],
        source_fields=["close", "timestamp_ms"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=36,
        horizons_supported=[18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Macro residual momentum captures multi-day institutional token-specific trend continuation at h=36 (144h / 6 days).",
    ),
    "volatility_expansion_skew": FactorMetadata(
        factor_id="alpha_07_volatility_expansion_skew",
        version="1.0.0",
        formula="(Upside_Range - Downside_Range) / (Upside_Range + Downside_Range)",
        required_history_bars=24,
        source_tables=["raw_candles_4h"],
        source_fields=["open", "high", "low", "close"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=12,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Asymmetric upside volatility expansion indicates aggressive institutional accumulation vs orderly downside consolidation.",
    ),
    "basis_oracle_dislocation": FactorMetadata(
        factor_id="alpha_08_basis_oracle_dislocation",
        version="1.0.0",
        formula="(Oracle_px - Close) / Oracle_px",
        required_history_bars=1,
        source_tables=["raw_candles_4h"],
        source_fields=["close", "oracle_px"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=1,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Temporary pricing dislocation between internal matching engine and composite oracle will mean-revert through arbitrage.",
    ),
    "cross_sectional_dispersion": FactorMetadata(
        factor_id="alpha_09_cross_sectional_dispersion",
        version="1.0.0",
        formula="R_{i, 24h} - median_{j in Alts}(R_{j, 24h})",
        required_history_bars=12,
        source_tables=["raw_candles_4h"],
        source_fields=["close"],
        sampling_frequency="4H",
        availability_lag_ms=500,
        lookback_bars=6,
        horizons_supported=[1, 2, 4, 8, 18, 36],
        pit_required=True,
        neutralization_set=["btc_beta", "volatility", "liquidity"],
        economic_hypothesis="Outliers deviating from the broad altcoin cross-sectional cohort experience idiosyncratic momentum or sharp mean-reversion.",
    ),
}


class FactorLibrary:
    """
    Computes candidate alpha factor matrices strictly using information known through time t.
    Zero future lookahead; outputs shape (T_bars, N_symbols).
    """
    def __init__(
        self,
        close_mat: np.ndarray,
        open_mat: np.ndarray,
        high_mat: np.ndarray,
        low_mat: np.ndarray,
        volume_mat: np.ndarray,
        oracle_mat: np.ndarray,
        valid_mask: np.ndarray,
        symbols: List[str],
        benchmark_symbol: str = "BTC",
    ):
        self.close = close_mat
        self.open = open_mat
        self.high = high_mat
        self.low = low_mat
        self.volume = volume_mat
        self.oracle = oracle_mat
        self.valid = valid_mask
        self.symbols = symbols
        self.T, self.N = close_mat.shape

        self.btc_idx = symbols.index(benchmark_symbol) if benchmark_symbol in symbols else 0

        # Precompute simple bar returns
        self.ret = np.zeros_like(self.close)
        self.ret[1:] = (self.close[1:] / (self.close[:-1] + 1e-12)) - 1.0

    @classmethod
    def get_metadata(cls, factor_name: str) -> Optional[FactorMetadata]:
        return METADATA_REGISTRY.get(factor_name)

    @classmethod
    def get_all_metadata(cls) -> Dict[str, FactorMetadata]:
        return METADATA_REGISTRY

    @classmethod
    def get_complete_registry(cls) -> Dict[str, FactorMetadata]:
        """
        Returns full registry mapping both factor_id (e.g. 'alpha_01_short_term_reversal')
        and factor_name (e.g. 'short_term_reversal') to FactorMetadata.
        """
        reg = dict(METADATA_REGISTRY)
        for meta in METADATA_REGISTRY.values():
            reg[meta.factor_id] = meta
        return reg

    # ----------------------------------------------------------------------
    # 4 Canonical Starter Alphas
    # ----------------------------------------------------------------------
    def compute_short_term_reversal(self, lookback_bars: int = 6) -> np.ndarray:
        """
        Alpha 1: Short-Term Residual Reversal (24h default @ 4H = 6 bars).
        Inverted cross-sectional momentum stripped of contemporaneous BTC beta.
        Exploits powerful short-horizon (4h-16h) mean-reversion of idiosyncratic token moves.
        Formula: -(R_{i, 24h} - beta_{i, BTC} * R_{BTC, 24h})
        """
        mom = np.full_like(self.close, np.nan)
        mom[lookback_bars:] = (self.close[lookback_bars:] / (self.close[:-lookback_bars] + 1e-12)) - 1.0

        btc_mom = mom[:, self.btc_idx]
        short_rev = np.full_like(mom, np.nan)

        for t in range(lookback_bars, self.T):
            mask_t = self.valid[t] & ~np.isnan(mom[t])
            if np.sum(mask_t) >= 10:
                y = mom[t, mask_t]
                x = btc_mom[t]
                # Inverted residualized cross-sectional difference: mean reversion
                short_rev[t, mask_t] = -(y - x)

        return short_rev

    def compute_residual_momentum(self, lookback_bars: int = 6) -> np.ndarray:
        """
        Legacy un-inverted residual momentum (for comparison & decay diagnostics).
        """
        mom = np.full_like(self.close, np.nan)
        mom[lookback_bars:] = (self.close[lookback_bars:] / (self.close[:-lookback_bars] + 1e-12)) - 1.0

        btc_mom = mom[:, self.btc_idx]
        res_mom = np.full_like(mom, np.nan)

        for t in range(lookback_bars, self.T):
            mask_t = self.valid[t] & ~np.isnan(mom[t])
            if np.sum(mask_t) >= 10:
                y = mom[t, mask_t]
                x = btc_mom[t]
                # Residualized cross-sectional difference
                res_mom[t, mask_t] = y - x

        return res_mom

    def compute_funding_divergence(self, lookback_bars: int = 18) -> np.ndarray:
        """
        Alpha 2: Funding / Synthetic Basis Divergence.
        Measures premium of close over short-term EWMA relative to ATR trend.
        Extreme positive values indicate over-leveraged long crowded positioning.
        """
        fund_div = np.full_like(self.close, np.nan)
        tr = np.maximum(
            self.high - self.low,
            np.maximum(
                np.abs(self.high - np.roll(self.close, 1, axis=0)),
                np.abs(self.low - np.roll(self.close, 1, axis=0)),
            ),
        )

        for t in range(lookback_bars, self.T):
            slice_close = self.close[t - lookback_bars : t]
            slice_tr = tr[t - lookback_bars : t]
            slice_vol = self.volume[t - lookback_bars : t]

            atr = np.nanmean(slice_tr, axis=0) + 1e-8
            ema = np.nanmean(slice_close, axis=0)
            vwap_proxy = np.nansum(slice_close * slice_vol, axis=0) / (np.nansum(slice_vol, axis=0) + 1e-8)

            trend_dist = (self.close[t] - ema) / atr
            basis_proxy = (self.close[t] - vwap_proxy) / (self.close[t] + 1e-8)

            # Divergence between fast price runup and volume-weighted basis
            signal = -(trend_dist - basis_proxy * 5.0) # Mean-reversion on crowded divergence
            fund_div[t] = np.where(self.valid[t], signal, np.nan)

        return fund_div

    def compute_oi_price_divergence(self, lookback_bars: int = 12) -> np.ndarray:
        """
        Alpha 3: Smart-Money Volume/OI Accumulation vs Flat Price.
        Identifies heavy volume accumulation while price is consolidating or falling.
        """
        oi_div = np.full_like(self.close, np.nan)

        for t in range(lookback_bars, self.T):
            vol_slice = self.volume[t - lookback_bars : t]
            mean_v = np.nanmean(vol_slice, axis=0) + 1.0
            std_v = np.nanstd(vol_slice, axis=0) + 1.0
            vol_z = (self.volume[t] - mean_v) / std_v

            price_change = (self.close[t] / (self.close[t - lookback_bars] + 1e-12)) - 1.0
            # Accumulation: volume z > 1.0 while price change <= 0
            signal = vol_z * np.where(price_change <= 0.0, 1.0, -0.5)
            oi_div[t] = np.where(self.valid[t], signal, np.nan)

        return oi_div

    def compute_volume_taker_skew(self, lookback_bars: int = 18) -> np.ndarray:
        """
        Alpha 4: Volume Surge Imbalance.
        Current volume standardized against rolling mean and signed by close-to-open direction.
        """
        vol_skew = np.full_like(self.volume, np.nan)
        for t in range(lookback_bars, self.T):
            vol_slice = self.volume[t - lookback_bars : t]
            mean_v = np.nanmean(vol_slice, axis=0) + 1.0
            std_v = np.nanstd(vol_slice, axis=0) + 1.0

            z_vol = (self.volume[t] - mean_v) / std_v
            sign_dir = np.sign(self.close[t] - self.open[t])
            vol_skew[t] = np.where(self.valid[t], z_vol * sign_dir, np.nan)

        return vol_skew

    # ----------------------------------------------------------------------
    # Secondary Factor Expansion Set
    # ----------------------------------------------------------------------
    def compute_liquidation_absorption(self, lookback_bars: int = 12) -> np.ndarray:
        """
        Alpha 5: Liquidation Absorption (High volume with narrow candle body).
        """
        absorb = np.full_like(self.close, np.nan)
        for t in range(lookback_bars, self.T):
            vol_slice = self.volume[t - lookback_bars : t]
            med_vol = np.nanmedian(vol_slice, axis=0) + 1.0
            vol_ratio = self.volume[t] / med_vol

            candle_body = np.abs(self.close[t] - self.open[t])
            candle_range = (self.high[t] - self.low[t]) + 1e-8
            body_ratio = candle_body / candle_range

            signal = vol_ratio * (1.0 - body_ratio) * np.sign(self.close[t] - self.low[t] - (self.high[t] - self.close[t]))
            absorb[t] = np.where(self.valid[t], signal, np.nan)

        return absorb

    def compute_volatility_expansion_skew(self, lookback_bars: int = 12) -> np.ndarray:
        """
        Alpha 6: Volatility Expansion Skew.
        """
        vol_skew = np.full_like(self.close, np.nan)
        for t in range(lookback_bars, self.T):
            slice_high = self.high[t - lookback_bars : t]
            slice_low = self.low[t - lookback_bars : t]
            slice_open = self.open[t - lookback_bars : t]

            upside = np.nanmean(np.maximum(0.0, slice_high - slice_open), axis=0)
            downside = np.nanmean(np.maximum(0.0, slice_open - slice_low), axis=0) + 1e-8
            ratio = (upside - downside) / (upside + downside)
            vol_skew[t] = np.where(self.valid[t], ratio, np.nan)

        return vol_skew

    def compute_basis_oracle_dislocation(self) -> np.ndarray:
        """
        Alpha 7: Basis / Oracle Dislocation.
        """
        basis = (self.oracle - self.close) / (self.oracle + 1e-12)
        return np.where(self.valid, basis, np.nan)

    def compute_cross_sectional_dispersion(self, lookback_bars: int = 6) -> np.ndarray:
        """
        Alpha 8: Cross-Sectional Return Dispersion Divergence.
        """
        disp = np.full_like(self.close, np.nan)
        mom = np.full_like(self.close, np.nan)
        mom[lookback_bars:] = (self.close[lookback_bars:] / (self.close[:-lookback_bars] + 1e-12)) - 1.0

        for t in range(lookback_bars, self.T):
            mask_t = self.valid[t] & ~np.isnan(mom[t])
            if np.sum(mask_t) >= 10:
                alt_median = np.nanmedian(mom[t, mask_t])
                disp[t, mask_t] = mom[t, mask_t] - alt_median

        return disp

    def compute_macro_residual_momentum(self, lookback_bars: int = 36) -> np.ndarray:
        """
        Alpha 6: Macro Residual Momentum (144h / 6 days @ 4H = 36 bars).
        Cross-sectional momentum continuation at macro horizons (h = 36).
        Formula: R_{i, 144h} - beta_{i, BTC} * R_{BTC, 144h}
        """
        mom = np.full_like(self.close, np.nan)
        mom[lookback_bars:] = (self.close[lookback_bars:] / (self.close[:-lookback_bars] + 1e-12)) - 1.0

        btc_mom = mom[:, self.btc_idx]
        macro_mom = np.full_like(mom, np.nan)

        for t in range(lookback_bars, self.T):
            mask_t = self.valid[t] & ~np.isnan(mom[t])
            if np.sum(mask_t) >= 10:
                y = mom[t, mask_t]
                x = btc_mom[t]
                # Positive continuation at macro horizons
                macro_mom[t, mask_t] = y - x

        return macro_mom

    def get_starter_factors(self) -> Dict[str, np.ndarray]:
        """
        Returns the 4 canonical starter alphas for pipeline validation:
        1. short_term_reversal (remediated inverted residual momentum)
        2. funding_divergence
        3. oi_price_divergence
        4. volume_taker_skew
        """
        return {
            "short_term_reversal": self.compute_short_term_reversal(lookback_bars=6),
            "funding_divergence": self.compute_funding_divergence(lookback_bars=18),
            "oi_price_divergence": self.compute_oi_price_divergence(lookback_bars=12),
            "volume_taker_skew": self.compute_volume_taker_skew(lookback_bars=18),
        }

    def get_all_factors(self) -> Dict[str, np.ndarray]:
        """
        Returns all candidate alpha factors (remediated starter set + expansion set).
        """
        factors = self.get_starter_factors()
        factors.update({
            "residual_momentum": self.compute_residual_momentum(lookback_bars=6),
            "liquidation_absorption": self.compute_liquidation_absorption(lookback_bars=12),
            "macro_residual_momentum": self.compute_macro_residual_momentum(lookback_bars=36),
            "volatility_expansion_skew": self.compute_volatility_expansion_skew(lookback_bars=12),
            "basis_oracle_dislocation": self.compute_basis_oracle_dislocation(),
            "cross_sectional_dispersion": self.compute_cross_sectional_dispersion(lookback_bars=6),
        })
        return factors

