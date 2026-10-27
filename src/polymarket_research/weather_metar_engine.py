#!/usr/bin/env python3
"""
Option #1: Automated Multi-City Daily Weather Engine (METAR Oracle + NWP Ensemble)
==================================================================================
Implements exact bit-for-bit Polymarket Airport Weather Oracle parsing and two
orthogonal systematic weather alpha sleeves:

  1. W1_SOLAR_PEAK_LOCK (Target 88%-95% Win Rate):
     - Monitors routine ICAO METAR observations (strictly excluding SPECI per spec,
       preferring 8-digit T-group remarks in tenths of °C over whole-°C body groups).
     - After local diurnal peak (or post-sunrise trough for Lowest-Temp markets),
       verifies physical cooling cushion + multi-model NWP remaining-day trajectory
       (ECMWF + GFS + ICON) before locking underpriced winning brackets into settlement.

  2. W2_ENSEMBLE_VALUE (Calibrated 71-Member Multi-Model Ensemble + MOS Bias Correction):
     - Combines Open-Meteo multi-model ensembles (ICON 40m + GFS 31m + ECMWF IFS)
       with real-time METAR runway persistence bias correction:
         bias(t + dt) = (T_metar_now - T_model_now) * exp(-dt / tau_hours)
     - Truncates impossible lower/upper brackets already ruled out by intraday METARs.
     - Captures mispriced brackets (0% fee on Polymarket `zero_fees` weather markets).
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger("WeatherMetarEngine")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
AWC_METAR_URL = "https://aviationweather.gov/api/data/metar"
AWC_STATION_URL = "https://aviationweather.gov/api/data/stationinfo"
IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HIST_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

# Verified station metadata cache (ICAO -> (lat, lon, iana_tz, city_label))
STATION_CATALOG: Dict[str, Tuple[float, float, str, str]] = {
    "RJTT": (35.5523, 139.7798, "Asia/Tokyo", "Tokyo"),
    "EGLC": (51.5053, 0.0553, "Europe/London", "London"),
    "ZSPD": (31.1434, 121.8052, "Asia/Shanghai", "Shanghai"),
    "ZSQD": (36.3667, 120.0944, "Asia/Shanghai", "Qingdao"),
    "WMKK": (2.7456, 101.7099, "Asia/Kuala_Lumpur", "Kuala Lumpur"),
    "RCSS": (25.0694, 121.5525, "Asia/Taipei", "Taipei"),
    "EDDM": (48.3538, 11.7861, "Europe/Berlin", "Munich"),
    "LFPB": (48.9694, 2.4414, "Europe/Paris", "Paris"),
    "ZUUU": (30.5785, 103.9471, "Asia/Shanghai", "Chengdu"),
    "SBGR": (-23.4356, -46.4731, "America/Sao_Paulo", "Sao Paulo"),
    "LEMD": (40.4719, -3.5626, "Europe/Madrid", "Madrid"),
    "ZHHH": (30.7838, 114.2081, "Asia/Shanghai", "Wuhan"),
    "EHAM": (52.3086, 4.7639, "Europe/Amsterdam", "Amsterdam"),
    "EPWA": (52.1657, 20.9671, "Europe/Warsaw", "Warsaw"),
    "WSSS": (1.3502, 103.9940, "Asia/Singapore", "Singapore"),
    "ZBAA": (40.0801, 116.5846, "Asia/Shanghai", "Beijing"),
    "ZUCK": (29.7192, 106.6417, "Asia/Shanghai", "Chongqing"),
    "LTFM": (41.2753, 28.7519, "Europe/Istanbul", "Istanbul"),
    "KMIA": (25.7959, -80.2870, "America/New_York", "Miami"),
    "OPKC": (24.9065, 67.1608, "Asia/Karachi", "Karachi"),
    "KLGA": (40.7769, -73.8740, "America/New_York", "NYC"),
    "RKSI": (37.4602, 126.4407, "Asia/Seoul", "Seoul"),
    "LLBG": (32.0114, 34.8867, "Asia/Jerusalem", "Tel Aviv"),
    "ZGGG": (23.3924, 113.2988, "Asia/Shanghai", "Guangzhou"),
    "OEJN": (21.6796, 39.1565, "Asia/Riyadh", "Jeddah"),
    "VILK": (26.7606, 80.8893, "Asia/Kolkata", "Lucknow"),
    "ZGSZ": (22.6393, 113.8107, "Asia/Shanghai", "Shenzhen"),
    "LIMC": (45.6306, 8.7281, "Europe/Rome", "Milan"),
    "RKPK": (35.1795, 128.9382, "Asia/Seoul", "Busan"),
    "LTAC": (40.1281, 32.9951, "Europe/Istanbul", "Ankara"),
    "SAEZ": (-34.8222, -58.5358, "America/Argentina/Buenos_Aires", "Buenos Aires"),
    "KSEA": (47.4502, -122.3088, "America/Los_Angeles", "Seattle"),
    "KDAL": (32.8471, -96.8518, "America/Chicago", "Dallas"),
    "NZWN": (-41.3272, 174.8053, "Pacific/Auckland", "Wellington"),
    "KSFO": (37.6213, -122.3790, "America/Los_Angeles", "San Francisco"),
    "KORD": (41.9742, -87.9073, "America/Chicago", "Chicago"),
    "MMMX": (19.4363, -99.0721, "America/Mexico_City", "Mexico City"),
    "CYYZ": (43.6777, -79.6248, "America/Toronto", "Toronto"),
    "RPLL": (14.5086, 121.0194, "Asia/Manila", "Manila"),
    "EFHK": (60.3172, 24.9633, "Europe/Helsinki", "Helsinki"),
    "KATL": (33.6407, -84.4277, "America/New_York", "Atlanta"),
    "KHOU": (29.6454, -95.2789, "America/Chicago", "Houston"),
    "KDEN": (39.8561, -104.6737, "America/Denver", "Denver"),
    "UUWW": (55.5915, 37.2615, "Europe/Moscow", "Moscow"),
    "MPMG": (8.9733, -79.5556, "America/Panama", "Panama City"),
}

_T_REMARK_RE = re.compile(r"(?:^|\s)T([01])(\d{3})(?:\d{4}|////)(?=\s|$)")
_BODY_TEMP_RE = re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)")
_METAR_TS_RE = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")
_CONVECTIVE_WX_RE = re.compile(
    r"(?:^|\s)(?:[-+]|VC)?(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)*\b"
    r"|(?:FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)\b"
    r"|\b(?:CB|TCU|RAB\d{2,4}|TSB\d{2,4}|P\d{4})\b"
)
_AWC_ICAO_RE = re.compile(r"aviationweather\.gov/api/data/metar\?ids=([A-Z0-9]{4})", re.IGNORECASE)
_NOAA_ICAO_RE = re.compile(r"weather\.gov/wrh/timeseries\?site=([A-Z0-9]{4})", re.IGNORECASE)
_PAREN_ICAO_RE = re.compile(r"\(([A-Z]{4})\)")
_SERIES_TO_ICAO: Dict[str, str] = {
    "tokyo-daily-weather": "RJTT",
    "london-daily-weather": "EGLC",
    "shanghai-daily-weather": "ZSPD",
    "chengdu-daily-weather": "ZUUU",
    "beijing-daily-weather": "ZBAA",
    "wuhan-daily-weather": "ZHHH",
    "chongqing-daily-weather": "ZUCK",
    "guangzhou-daily-weather": "ZGGG",
    "shenzhen-daily-weather": "ZGSZ",
    "qingdao-daily-weather": "ZSQD",
    "paris-daily-weather": "LFPB",
    "munich-daily-weather": "EDDM",
    "miami-daily-weather": "KMIA",
    "nyc-daily-weather": "KLGA",
    "houston-daily-weather": "KHOU",
    "seoul-daily-weather": "RKSI",
    "busan-daily-weather": "RKPK",
    "chicago-daily-weather": "KORD",
    "seattle-daily-weather": "KSEA",
    "dallas-daily-weather": "KDAL",
    "madrid-daily-weather": "LEMD",
    "amsterdam-daily-weather": "EHAM",
    "taipei-daily-weather": "RCSS",
    "singapore-daily-weather": "WSSS",
}

HIGH_VOLUME_WEATHER_SERIES: Tuple[str, ...] = (
    "chengdu-daily-weather",
    "beijing-daily-weather",
    "seoul-daily-weather",
    "shanghai-daily-weather",
    "tokyo-daily-weather",
    "wuhan-daily-weather",
    "chongqing-daily-weather",
    "guangzhou-daily-weather",
    "shenzhen-daily-weather",
    "taipei-daily-weather",
    "singapore-daily-weather",
    "nyc-daily-weather",
    "chicago-daily-weather",
    "london-daily-weather",
)
_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


@dataclass
class WeatherBucket:
    market_id: str
    condition_id: str
    label: str
    question: str
    yes_token: str
    no_token: str
    unit: str  # "C" or "F"
    low_bound: float  # -inf for "X or below"
    high_bound: float  # +inf for "X or higher"
    outcome_yes_resolved: Optional[int] = None  # 1 or 0 for closed markets
    fee_rate: float = 0.0
    fee_exponent: float = 1.0

    def contains_rounded(self, rounded_int: int) -> bool:
        return self.low_bound <= rounded_int <= self.high_bound


@dataclass
class WeatherEventSpec:
    event_id: str
    slug: str
    series_slug: str
    title: str
    icao: str
    city: str
    lat: float
    lon: float
    tz_name: str
    obs_date: date
    metric: str  # "HIGH" or "LOW"
    unit: str  # "C" or "F"
    fee_type: str
    end_date_iso: str
    buckets: List[WeatherBucket] = field(default_factory=list)


@dataclass
class MetarObservation:
    icao: str
    utc_dt: datetime
    local_dt: datetime
    temp_c: float
    has_t_remark: bool
    raw_line: str
    has_convective_precip: bool = False
    is_corrected: bool = False


def round_half_up_polymarket(val: float) -> int:
    """
    Exact Polymarket Weather rounding rule verified against spec examples:
      13.9 -> 14, 17.4 -> 17, 16.5 -> 17, -1.7 -> -2, -8.5 -> -8.
    Mathematically identical to floor(val + 0.5) with float epsilon guard.
    """
    return int(math.floor(val + 0.5 + 1e-12))


def celsius_to_market_int(temp_c: float, unit: str) -> int:
    if unit.upper() == "F":
        val_f = temp_c * 9.0 / 5.0 + 32.0
        return round_half_up_polymarket(val_f)
    return round_half_up_polymarket(temp_c)


def parse_bucket_bounds(label: str) -> Optional[Tuple[str, float, float]]:
    """
    Parses Polymarket weather bucket titles such as:
      '16°C or below', '17°C', '26°C or higher',
      '71°F or below', '72-73°F', '90°F or higher',
      '-2°C or below', '-1°C', '-4--3°F'
    Returns (unit, low_bound, high_bound).
    """
    s = label.strip().replace("−", "-").replace("–", "-")
    unit_m = re.search(r"°\s*([CF])", s, re.IGNORECASE)
    if not unit_m:
        return None
    unit = unit_m.group(1).upper()
    low_s = s.lower()

    if "or below" in low_s or "or lower" in low_s or "or less" in low_s or "under" in low_s:
        m = re.search(r"(-?\d+)\s*°", s)
        if not m:
            return None
        return unit, float("-inf"), float(int(m.group(1)))

    if "or higher" in low_s or "or above" in low_s or "or more" in low_s:
        m = re.search(r"(-?\d+)\s*°", s)
        if not m:
            return None
        return unit, float(int(m.group(1))), float("inf")

    m_range = re.search(r"(-?\d+)\s*(?:°[CF])?\s*(?:-|to)\s*(-?\d+)\s*°", s, re.IGNORECASE)
    if m_range:
        lo, hi = int(m_range.group(1)), int(m_range.group(2))
        return unit, float(min(lo, hi)), float(max(lo, hi))

    m_single = re.search(r"(-?\d+)\s*°", s)
    if m_single:
        v = float(int(m_single.group(1)))
        return unit, v, v
    return None


def parse_metar_line(
    raw_line: str,
    icao: str,
    ref_utc: datetime,
    tz_name: str,
    explicit_utc_dt: Optional[datetime] = None,
) -> Optional[MetarObservation]:
    """
    Parses a single raw METAR line strictly per Polymarket Weather contract rules:
      1. Any line whose report begins with SPECI is excluded.
      2. Extracts 8-digit hourly temperature remark T[01]xxx.... (0.1°C) if present.
      3. Otherwise falls back to body temperature group M?dd/M?dd (1.0°C).
    """
    line = raw_line.strip()
    if not line:
        return None
    # Strip optional leading timestamp prefix if present
    upper = line.upper()
    tokens = upper.split()
    if not tokens:
        return None
    if "SPECI" in tokens[:3]:
        return None
    if icao.upper() not in tokens[:4]:
        return None
    is_cor = "COR" in tokens[:5]

    utc_dt = explicit_utc_dt
    if utc_dt is None:
        m_ts = _METAR_TS_RE.search(upper)
        if not m_ts:
            return None
        day_i, hr_i, min_i = int(m_ts.group(1)), int(m_ts.group(2)), int(m_ts.group(3))
        # Resolve year/month near ref_utc cleanly across month boundaries
        candidates: List[datetime] = []
        for d_off in (-32, 0, 32):
            anchor = ref_utc + timedelta(days=d_off)
            try:
                cand = datetime(anchor.year, anchor.month, day_i, hr_i, min_i, tzinfo=timezone.utc)
                candidates.append(cand)
            except ValueError:
                continue
        if not candidates:
            return None
        utc_dt = min(candidates, key=lambda c: abs((c - ref_utc).total_seconds()))

    # 1. Check 8-digit T-remark (only in RMK section if RMK is present)
    rmk_part = upper.split("RMK", 1)[1] if "RMK" in upper else upper
    m_rem = _T_REMARK_RE.search(rmk_part)
    if m_rem:
        sign = -1.0 if m_rem.group(1) == "1" else 1.0
        temp_c = sign * (int(m_rem.group(2)) / 10.0)
        has_t = True
    else:
        # 2. Fallback to body temperature group before RMK
        body_part = upper.split("RMK", 1)[0]
        m_body = _BODY_TEMP_RE.search(body_part)
        if not m_body:
            return None
        grp = m_body.group(1)
        temp_c = -float(int(grp[1:])) if grp.startswith("M") else float(int(grp))
        has_t = False

    local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
    has_precip = bool(_CONVECTIVE_WX_RE.search(upper))
    return MetarObservation(
        icao=icao.upper(),
        utc_dt=utc_dt,
        local_dt=local_dt,
        temp_c=temp_c,
        has_t_remark=has_t,
        raw_line=line,
        has_convective_precip=has_precip,
        is_corrected=is_cor,
    )


def parse_obs_date_from_event(title: str, desc: str, end_date_iso: str) -> Optional[date]:
    """Extracts the target local observation date from event description or title."""
    # Description pattern: "on 26 Oct '26" or "on 25 Oct '26"
    m_desc = re.search(r"\bon\s+(\d{1,2})\s+([A-Za-z]+)\s+'?(\d{2,4})\b", desc)
    if m_desc:
        day_v = int(m_desc.group(1))
        mon_v = _MONTH_MAP.get(m_desc.group(2).lower())
        yr_v = int(m_desc.group(3))
        if yr_v < 100:
            yr_v += 2000
        if mon_v:
            try:
                return date(yr_v, mon_v, day_v)
            except ValueError:
                pass

    # Title pattern: "on October 26?" or "on October 25, 2026?"
    ref_year = 2026
    if end_date_iso:
        try:
            ref_year = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00")).year
        except Exception:
            pass
    m_title = re.search(r"\bon\s+([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?", title)
    if m_title:
        mon_v = _MONTH_MAP.get(m_title.group(1).lower())
        day_v = int(m_title.group(2))
        yr_v = int(m_title.group(3)) if m_title.group(3) else ref_year
        if mon_v:
            try:
                return date(yr_v, mon_v, day_v)
            except ValueError:
                pass
    return None


def parse_weather_event(
    ev: Dict[str, Any],
    allow_historical_same_station: bool = False,
    series_slug_hint: str = "",
) -> Optional[WeatherEventSpec]:
    """
    Converts a Polymarket Gamma event dict into a validated WeatherEventSpec.
    Live mode (`allow_historical_same_station=False`) strictly requires an explicit
    aviationweather.gov ICAO METAR oracle URL + SPECI rule in description.
    Backtest mode (`allow_historical_same_station=True`) also accepts pre-Oct-23
    markets at the exact same airport station (NOAA/Wunderground airport METAR feed).
    """
    title = str(ev.get("title") or "")
    tl = title.lower()
    if "highest temperature in" in tl:
        metric = "HIGH"
    elif "lowest temperature in" in tl:
        metric = "LOW"
    else:
        return None

    mkts = ev.get("markets") or []
    if len(mkts) < 4:
        return None

    series_arr = ev.get("series") or []
    s_slug = str(series_arr[0].get("slug") if series_arr else (ev.get("seriesSlug") or series_slug_hint or ""))
    desc = str(mkts[0].get("description") or ev.get("description") or "")

    icao: Optional[str] = None
    m_icao = _AWC_ICAO_RE.search(desc)
    if m_icao and "SPECI" in desc:
        icao = m_icao.group(1).upper()
    elif allow_historical_same_station:
        m_noaa = _NOAA_ICAO_RE.search(desc)
        m_par = _PAREN_ICAO_RE.search(desc)
        if m_noaa and m_noaa.group(1).upper() in STATION_CATALOG:
            icao = m_noaa.group(1).upper()
        elif m_par and m_par.group(1).upper() in STATION_CATALOG:
            icao = m_par.group(1).upper()
        elif s_slug in _SERIES_TO_ICAO:
            icao = _SERIES_TO_ICAO[s_slug]

    if not icao or icao not in STATION_CATALOG:
        return None

    lat, lon, tz_name, city = STATION_CATALOG[icao]
    end_iso = str(ev.get("endDate") or mkts[0].get("endDate") or "")
    obs_date = parse_obs_date_from_event(title, desc, end_iso)
    if obs_date is None:
        return None

    fee_type = str(mkts[0].get("feeType") or "zero_fees")

    buckets: List[WeatherBucket] = []
    for m in mkts:
        lbl = str(m.get("groupItemTitle") or m.get("question") or "")
        parsed = parse_bucket_bounds(lbl)
        if not parsed:
            continue
        unit, lo, hi = parsed
        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        if not toks or len(toks) < 2:
            continue

        resolved_yes: Optional[int] = None
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            if isinstance(op, list) and len(op) >= 2:
                try:
                    if float(op[0]) >= 0.99:
                        resolved_yes = 1
                    elif float(op[1]) >= 0.99:
                        resolved_yes = 0
                except Exception:
                    pass

        m_fee_sched = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
        fees_enabled = bool(m.get("feesEnabled", False))
        raw_rate = float(m_fee_sched.get("rate") or 0.0)
        b_fee_rate = raw_rate if (fees_enabled and raw_rate > 0.0) else 0.0
        b_fee_exp = float(m_fee_sched.get("exponent") or 1.0)

        buckets.append(
            WeatherBucket(
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                label=lbl,
                question=str(m.get("question") or lbl),
                yes_token=str(toks[0]),
                no_token=str(toks[1]),
                unit=unit,
                low_bound=lo,
                high_bound=hi,
                outcome_yes_resolved=resolved_yes,
                fee_rate=b_fee_rate,
                fee_exponent=b_fee_exp,
            )
        )

    if len(buckets) < 4:
        return None
    buckets.sort(key=lambda b: (b.low_bound, b.high_bound))
    if any(b.fee_rate > 0.0 for b in buckets):
        fee_type = "fees_enabled"
    return WeatherEventSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        series_slug=s_slug,
        title=title,
        icao=icao,
        city=city,
        lat=lat,
        lon=lon,
        tz_name=tz_name,
        obs_date=obs_date,
        metric=metric,
        unit=buckets[0].unit,
        fee_type=fee_type,
        end_date_iso=end_iso,
        buckets=buckets,
    )


def fetch_metar_observations_sync(
    icao: str,
    obs_date: date,
    tz_name: str,
    timeout: float = 8.0,
) -> List[MetarObservation]:
    """
    Fetches routine METAR observations for (icao, obs_date) in station local time.
    Uses exact Polymarket AWC endpoint for recent dates (<= 13 days) and falls back
    seamlessly to Iowa Environmental Mesonet (IEM ASOS) raw METAR archive for older dates.
    """
    tz = ZoneInfo(tz_name)
    local_start = datetime(obs_date.year, obs_date.month, obs_date.day, 0, 0, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    utc_end_query = local_end.astimezone(timezone.utc) + timedelta(hours=3)
    now_utc = datetime.now(timezone.utc)
    query_anchor = min(now_utc, utc_end_query)

    age_days = (now_utc - local_start.astimezone(timezone.utc)).total_seconds() / 86400.0
    obs_by_ts: Dict[int, MetarObservation] = {}

    def _merge_metar(parsed_obs: MetarObservation) -> None:
        ts_k = int(parsed_obs.utc_dt.timestamp())
        prev = obs_by_ts.get(ts_k)
        if (
            prev is None
            or parsed_obs.is_corrected
            or (not prev.is_corrected and (parsed_obs.has_t_remark or not prev.has_t_remark))
        ):
            obs_by_ts[ts_k] = parsed_obs

    if age_days <= 13.5:
        iso_q = query_anchor.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{AWC_METAR_URL}?ids={icao.upper()}&format=raw&date={iso_q}&hours=36"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
            raw_text = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
            # AWC emits newest lines first; iterate oldest -> newest so COR amendments supersede originals (`M-02`)
            for line in reversed(raw_text.splitlines()):
                parsed = parse_metar_line(line, icao, query_anchor, tz_name)
                if parsed and parsed.local_dt.date() == obs_date:
                    _merge_metar(parsed)
        except Exception as exc:
            logger.debug(f"AWC METAR fetch fallback for {icao} {obs_date}: {exc}")

    if not obs_by_ts:
        # Fallback to IEM ASOS historical raw METAR archive
        u_start = local_start.astimezone(timezone.utc) - timedelta(hours=2)
        u_end = local_end.astimezone(timezone.utc) + timedelta(hours=2)
        st_param = icao.upper()[1:] if (len(icao) == 4 and icao.upper().startswith("K")) else icao.upper()
        params = urllib.parse.urlencode({
            "station": st_param,
            "data": "metar",
            "year1": u_start.year, "month1": u_start.month, "day1": u_start.day,
            "year2": u_end.year, "month2": u_end.month, "day2": u_end.day,
            "tz": "Etc/UTC",
            "format": "onlycomma",
            "latlon": "no", "elev": "no",
            "missing": "M", "trace": "T", "direct": "no",
            "report_type": ["3", "4"],
        }, doseq=True)
        try:
            req = urllib.request.Request(f"{IEM_ASOS_URL}?{params}", headers={"User-Agent": "DominusWeatherEngine/1.0"})
            csv_txt = urllib.request.urlopen(req, timeout=timeout + 4.0).read().decode("utf-8", errors="ignore")
            for row in csv_txt.splitlines()[1:]:
                parts = row.split(",", 2)
                if len(parts) < 3:
                    continue
                try:
                    dt_utc = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                parsed = parse_metar_line(parts[2], icao, dt_utc, tz_name, explicit_utc_dt=dt_utc)
                if parsed and parsed.local_dt.date() == obs_date:
                    _merge_metar(parsed)
        except Exception as exc:
            logger.debug(f"IEM METAR archive fetch error for {icao} {obs_date}: {exc}")

    return sorted(obs_by_ts.values(), key=lambda o: o.utc_dt)


def compute_weather_probabilities(
    spec: WeatherEventSpec,
    eval_utc: datetime,
    metars_so_far: List[MetarObservation],
    ensemble_hourly_c: Dict[int, List[float]],
    forecast_sigma_base_c: float = 1.15,
    bias_decay_tau_hr: float = 6.0,
    taf_extreme_c: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes strictly causal (as-of `eval_utc`) bucket probabilities and physical solar-lock signals:
      - `metars_so_far`: strictly filtered to `o.utc_dt <= eval_utc` on `spec.obs_date`.
      - `ensemble_hourly_c`: mapping of `unix_hour_ts -> [member_1_temp_c, ..., member_M_temp_c]`
        covering `spec.obs_date` in the station's local timezone.
    Returns dict with per-bucket probabilities, lock metrics, and model diagnostics.
    """
    tz = ZoneInfo(spec.tz_name)
    eval_local = eval_utc.astimezone(tz)
    local_day_start = datetime(spec.obs_date.year, spec.obs_date.month, spec.obs_date.day, 0, 0, tzinfo=tz)
    local_day_end = local_day_start + timedelta(days=1)

    valid_obs = [o for o in metars_so_far if o.utc_dt <= eval_utc and o.local_dt.date() == spec.obs_date]
    has_obs = len(valid_obs) > 0
    latest_obs = valid_obs[-1] if has_obs else None

    if has_obs:
        if spec.metric == "HIGH":
            running_ext_c = max(o.temp_c for o in valid_obs)
        else:
            running_ext_c = min(o.temp_c for o in valid_obs)
        running_ext_int = celsius_to_market_int(running_ext_c, spec.unit)
    else:
        running_ext_c = None
        running_ext_int = None

    # Compute real-time MOS / station runway persistence bias from recent METARs vs ensemble mean
    # Guard against transient convective rain-shower cold pools (e.g. KMIA midday RA/CB cooling runway by -2.3°C)
    bias_c = 0.0
    eff_bias_tau_hr = bias_decay_tau_hr
    recent_convective = False
    convective_cold_pool = False
    if latest_obs is not None:
        recent_window = [o for o in valid_obs if (eval_utc - o.utc_dt).total_seconds() <= 12600.0][-3:]
        recent_convective = any(
            o.has_convective_precip for o in valid_obs if (eval_utc - o.utc_dt).total_seconds() <= 7200.0
        )
        local_hr_now = eval_local.hour + eval_local.minute / 60.0
        sudden_daytime_drop = (
            spec.metric == "HIGH"
            and 9.0 <= local_hr_now <= 16.25
            and running_ext_c is not None
            and (running_ext_c - latest_obs.temp_c) >= 1.2
        )
        if ensemble_hourly_c and recent_window:
            obs_biases: List[float] = []
            for o_rec in recent_window:
                nearest_hr = int(round(o_rec.utc_dt.timestamp() / 3600.0) * 3600)
                ref_members = ensemble_hourly_c.get(nearest_hr)
                if ref_members:
                    ens_mean_hr = sum(ref_members) / len(ref_members)
                    obs_biases.append(o_rec.temp_c - ens_mean_hr)
            if obs_biases:
                obs_biases.sort()
                if len(obs_biases) == 3:
                    raw_bias = obs_biases[1]  # Median / trimmed mean of last 3 routine METARs
                else:
                    raw_bias = sum(obs_biases) / len(obs_biases)
                # Clear-sky systematic NWP airport bias rarely exceeds +/-1.5°C; larger swings are mesoscale
                bias_c = max(-1.5, min(1.5, raw_bias))
                if spec.metric == "HIGH" and raw_bias < -0.35 and (recent_convective or sudden_daytime_drop):
                    convective_cold_pool = True
                    # Do NOT extrapolate transient rain-cooled runway air across the rest of the sunny afternoon!
                    bias_c = max(-0.45, raw_bias * 0.20)
                    eff_bias_tau_hr = min(bias_decay_tau_hr, 1.2)
        elif recent_convective or sudden_daytime_drop:
            convective_cold_pool = spec.metric == "HIGH"

    # Build remaining hourly timestamps on `obs_date` strictly after `eval_utc`
    rem_hour_ts: List[int] = []
    cur_dt = max(local_day_start, eval_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    while cur_dt < local_day_end:
        rem_hour_ts.append(int(cur_dt.astimezone(timezone.utc).timestamp()))
        cur_dt += timedelta(hours=1)
    if eval_local < local_day_end and not rem_hour_ts:
        # Between 23:00:00 and 23:59:59 local time: routine 23:53-23:59 METAR can still print (`H-02`)!
        rem_hour_ts.append(int(local_day_end.astimezone(timezone.utc).timestamp()))

    # Determine number of ensemble trajectories (or synthesize Gaussian trajectories around mean if 1-3 deterministic models)
    sample_counts = [len(ensemble_hourly_c[t]) for t in rem_hour_ts if t in ensemble_hourly_c and ensemble_hourly_c[t]]
    if not sample_counts and ensemble_hourly_c:
        sample_counts = [len(v) for v in ensemble_hourly_c.values() if v]
    n_raw = min(sample_counts) if sample_counts else 0

    # Construct N=13-quadrature x M-member calibrated Ensemble trajectories over remaining hours
    z_grid = [-2.1, -1.5, -1.1, -0.75, -0.45, -0.2, 0.0, 0.2, 0.45, 0.75, 1.1, 1.5, 2.1]
    bucket_weights = [0.0 for _ in spec.buckets]
    total_weight = 0.0
    member_extremes: List[float] = []

    rem_hours_count = len(rem_hour_ts)
    if eval_local >= local_day_end and running_ext_int is not None:
        # Observation day has physically ended in local station time!
        for idx, b in enumerate(spec.buckets):
            bucket_weights[idx] = 1.0 if b.contains_rounded(running_ext_int) else 0.0
        total_weight = 1.0
    elif n_raw > 0 and rem_hours_count > 0:
        # Residual sub-grid / urban runway representation uncertainty (shrinks when few hours remain)
        sigma_resid = forecast_sigma_base_c * min(1.0, math.sqrt(max(1.0, rem_hours_count) / 10.0))
        if n_raw >= 15:
            # Multi-member ensemble already captures synoptic spread; add modest runway microclimate kernel
            sigma_kernel = max(0.45, 0.55 * sigma_resid)
        else:
            # 1-3 deterministic models (e.g., historical archive or partial fallback): use full forecast error kernel
            sigma_kernel = max(0.75, sigma_resid)
        if convective_cold_pool:
            # Post-shower solar recovery vs lingering outflow cloud cover increases afternoon peak spread
            sigma_kernel *= 1.45

        for m_idx in range(n_raw):
            # Future extreme for member m_idx with bias decay
            base_future_vals: List[float] = []
            for h_ts in rem_hour_ts:
                vals = ensemble_hourly_c.get(h_ts)
                if not vals:
                    continue
                v = vals[min(m_idx, len(vals) - 1)]
                dt_hr = max(0.0, (h_ts - eval_utc.timestamp()) / 3600.0)
                decayed_bias = bias_c * math.exp(-dt_hr / max(0.5, eff_bias_tau_hr))
                base_future_vals.append(v + decayed_bias)

            if not base_future_vals:
                continue
            fut_ext_base = max(base_future_vals) if spec.metric == "HIGH" else min(base_future_vals)
            if taf_extreme_c is not None and math.isfinite(float(taf_extreme_c)):
                # Blend official human-forecaster Airport TAF TX/TN group as a 15% physical runway prior (`Gemini #11`)
                fut_ext_base = 0.85 * fut_ext_base + 0.15 * float(taf_extreme_c)
            member_extremes.append(fut_ext_base)

            for z in z_grid:
                w = math.exp(-0.5 * z * z)
                sim_fut_c = fut_ext_base + z * sigma_kernel
                if running_ext_c is not None:
                    final_c = max(running_ext_c, sim_fut_c) if spec.metric == "HIGH" else min(running_ext_c, sim_fut_c)
                else:
                    final_c = sim_fut_c
                final_int = celsius_to_market_int(final_c, spec.unit)
                for b_idx, b in enumerate(spec.buckets):
                    if b.contains_rounded(final_int):
                        bucket_weights[b_idx] += w
                        break
                total_weight += w

    peak_iqr_c = 0.0
    if len(member_extremes) >= 4:
        s_ext = sorted(member_extremes)
        q25 = s_ext[int(0.25 * (len(s_ext) - 1))]
        q75 = s_ext[int(0.75 * (len(s_ext) - 1))]
        peak_iqr_c = max(0.0, q75 - q25)

    if total_weight <= 0.0:
        probs = [1.0 / len(spec.buckets) for _ in spec.buckets]
    else:
        probs = [max(0.001, min(0.998, w / total_weight)) for w in bucket_weights]
        s_p = sum(probs)
        probs = [p / s_p for p in probs]

    # Check W1_SOLAR_PEAK_LOCK qualification
    is_solar_lock_window = False
    cooling_cushion_c = 0.0
    locked_bucket_idx: Optional[int] = None
    p_locked_bucket = 0.0

    if has_obs and latest_obs is not None and running_ext_c is not None and running_ext_int is not None:
        local_hr_float = eval_local.hour + eval_local.minute / 60.0
        for idx, b in enumerate(spec.buckets):
            if b.contains_rounded(running_ext_int):
                locked_bucket_idx = idx
                p_locked_bucket = probs[idx]
                break

        if spec.metric == "HIGH":
            cooling_cushion_c = running_ext_c - latest_obs.temp_c
            # Post-afternoon solar peak: local time >= 15:45 on clear days, or >= 17:30 if convective rain cooled runway!
            min_lock_hr = 17.50 if (recent_convective or convective_cold_pool) else 15.75
            past_peak = (eval_local.date() > spec.obs_date) or (
                eval_local.date() == spec.obs_date and local_hr_float >= min_lock_hr
            )
            if past_peak and (eval_local.date() > spec.obs_date or cooling_cushion_c >= 0.8) and p_locked_bucket >= 0.88:
                is_solar_lock_window = True
        else:
            # LOW temperature market: typically locks only late at night (23:00+) unless evening stays warm above morning trough
            warming_cushion_c = latest_obs.temp_c - running_ext_c
            cooling_cushion_c = warming_cushion_c
            past_trough = (eval_local.date() > spec.obs_date) or (
                eval_local.date() == spec.obs_date and local_hr_float >= 22.5
            )
            if past_trough and (eval_local.date() > spec.obs_date or warming_cushion_c >= 1.0) and p_locked_bucket >= 0.90:
                is_solar_lock_window = True

    return {
        "probs": probs,
        "has_obs": has_obs,
        "obs_count": len(valid_obs),
        "latest_temp_c": latest_obs.temp_c if latest_obs else None,
        "running_ext_c": running_ext_c,
        "running_ext_int": running_ext_int,
        "bias_c": round(bias_c, 3),
        "convective_cold_pool": convective_cold_pool,
        "ensemble_member_count": n_raw,
        "peak_iqr_c": round(peak_iqr_c, 3),
        "rem_hours_count": rem_hours_count,
        "is_solar_lock": is_solar_lock_window,
        "cooling_cushion_c": round(cooling_cushion_c, 2),
        "locked_bucket_idx": locked_bucket_idx,
        "p_locked_bucket": round(p_locked_bucket, 4),
    }


def fetch_live_ensemble_hourly_sync(lat: float, lon: float, timeout: float = 8.0) -> Dict[int, List[float]]:
    """
    Fetches live 71-member NWP ensemble hourly temperatures (ICON 40m + GFS 31m)
    plus deterministic ECMWF IFS 0.25° from Open-Meteo in UTC unix seconds.
    """
    hourly_members: Dict[int, List[float]] = {}
    ens_url = (
        f"{OPEN_METEO_ENSEMBLE_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=temperature_2m&models=icon_seamless,gfs_seamless&past_days=1&forecast_days=3&timeformat=unixtime"
    )
    for attempt in range(2):
        try:
            req = urllib.request.Request(ens_url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
            hourly = data.get("hourly") or {}
            times = hourly.get("time") or []
            raw_keys = sorted(k for k in hourly.keys() if k.startswith("temperature_2m"))
            # Keep deterministic member alignment across all hours (`M-02`: never shift member indices on single-hour None)
            aligned_series: List[List[float]] = []
            for k in raw_keys:
                arr = hourly.get(k) or []
                if len(arr) < len(times):
                    continue
                filled: List[float] = []
                last_v: Optional[float] = None
                missing_n = 0
                for raw_v in arr[: len(times)]:
                    if raw_v is not None:
                        last_v = float(raw_v)
                        filled.append(last_v)
                    elif last_v is not None:
                        missing_n += 1
                        filled.append(last_v)
                    else:
                        missing_n = len(times)
                        break
                if len(filled) == len(times) and missing_n <= max(2, len(times) // 10):
                    aligned_series.append(filled)
            for idx, ts in enumerate(times):
                vals = [series[idx] for series in aligned_series]
                if vals:
                    hourly_members[int(ts)] = vals
            if hourly_members:
                break
        except Exception as exc:
            if attempt == 0:
                time.sleep(0.45)
            else:
                logger.debug(f"Open-Meteo ensemble fetch notice ({lat},{lon}): {exc}")

    # Augment with deterministic ECMWF IFS 0.25° (upweighted x5 for skill superiority)
    ec_url = (
        f"{OPEN_METEO_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=temperature_2m&models=ecmwf_ifs025&past_days=1&forecast_days=3&timeformat=unixtime"
    )
    try:
        req = urllib.request.Request(ec_url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
        ec_data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        ec_h = ec_data.get("hourly") or {}
        ec_times = ec_h.get("time") or []
        ec_vals = ec_h.get("temperature_2m") or ec_h.get("temperature_2m_ecmwf_ifs025") or []
        for idx, ts in enumerate(ec_times):
            if idx < len(ec_vals) and ec_vals[idx] is not None:
                v = float(ec_vals[idx])
                hourly_members.setdefault(int(ts), []).extend([v] * 8)
    except Exception:
        pass

    return hourly_members


def fetch_historical_nwp_hourly_sync(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    timeout: float = 10.0,
) -> Dict[int, List[float]]:
    """
    Fetches archived historical point-in-time NWP forecasts (ECMWF IFS 0.25°, GFS, ICON)
    from Open-Meteo Historical Forecast Archive for leak-free backtesting.
    """
    url = (
        f"{OPEN_METEO_HIST_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        f"&hourly=temperature_2m&models=ecmwf_ifs025,gfs_seamless,icon_seamless&timeformat=unixtime"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    m_keys = sorted(k for k in hourly.keys() if k.startswith("temperature_2m"))
    out: Dict[int, List[float]] = {}
    for idx, ts in enumerate(times):
        vals: List[float] = []
        for k in m_keys:
            arr = hourly[k]
            if idx < len(arr) and arr[idx] is not None:
                v = float(arr[idx])
                # Weight ECMWF 2x relative to GFS and ICON
                if "ecmwf" in k:
                    vals.extend([v, v])
                else:
                    vals.append(v)
        if vals:
            out[int(ts)] = vals
    return out


_TAF_TEMP_RE = re.compile(r"\bT([XN])(M?\d{2})/(\d{2})(\d{2})Z\b")
AWC_TAF_URL = "https://aviationweather.gov/api/data/taf"

# Empirical ICAO routine hourly METAR release minute past the hour (US ASOS :51-:54, ICAO Europe/Asia :00/:20/:50)
STATION_ROUTINE_RELEASE_MIN: Dict[str, Tuple[int, ...]] = {
    "KLGA": (51,), "KORD": (51,), "KATL": (52,), "KDAL": (53,), "KHOU": (53,),
    "KMIA": (53,), "KSEA": (53,), "KSFO": (56,), "KDEN": (53,), "CYYZ": (0,),
    "EGLC": (20, 50), "LFPB": (0, 30), "EDDM": (20, 50), "LIMC": (20, 50), "EFHK": (20, 50),
    "RJTT": (0, 30), "RKSI": (0, 30), "RKPK": (0,), "ZSPD": (0,), "ZGSZ": (0,),
    "RPLL": (0,), "LTAC": (20, 50), "SAEZ": (0,), "NZWN": (0, 30), "MMMX": (45,),
}


def compute_adaptive_metar_poll_ttl(
    icao: str,
    metars_so_far: Optional[List[MetarObservation]] = None,
    now_utc: Optional[datetime] = None,
) -> float:
    """
    Station-release-minute synchronized METAR polling cadence (`Gemini #11`):
    Returns `10.0s` inside `[release_min - 1, release_min + 4]` (capturing new hourly METARs within
    seconds of AWC publication!) and `300.0s` during quiet mid-hour windows.
    """
    dt = now_utc or datetime.now(timezone.utc)
    cur_min = dt.minute + dt.second / 60.0
    release_mins: List[int] = list(STATION_ROUTINE_RELEASE_MIN.get(icao.upper(), ()))
    if metars_so_far:
        recent_mins = sorted({o.utc_dt.minute for o in metars_so_far[-4:]})
        for rm in recent_mins:
            if rm not in release_mins:
                release_mins.append(rm)
    if not release_mins:
        release_mins = [0, 51, 53]
    for r_min in release_mins:
        # Circular 60-minute distance from `r_min`: check `delta in [-1.0, +4.5]`
        delta = (cur_min - float(r_min) + 30.0) % 60.0 - 30.0
        if -1.0 <= delta <= 4.5:
            return 10.0
    return 300.0


def parse_taf_temperature_extremes(
    raw_taf: str,
    icao: str,
    ref_utc: datetime,
    tz_name: str,
) -> Dict[date, Dict[str, float]]:
    """
    Parses official NWS/ICAO Terminal Aerodrome Forecast (`TAF`) `TXdd/ddhhZ` and `TNdd/ddhhZ`
    temperature extreme groups into `{local_obs_date: {"HIGH": temp_c, "LOW": temp_c}}`.
    """
    if not raw_taf or icao.upper() not in raw_taf.upper():
        return {}
    tz = ZoneInfo(tz_name)
    out: Dict[date, Dict[str, float]] = {}
    for m in _TAF_TEMP_RE.finditer(raw_taf.upper()):
        kind = "HIGH" if m.group(1) == "X" else "LOW"
        raw_t = m.group(2)
        temp_c = -float(int(raw_t[1:])) if raw_t.startswith("M") else float(int(raw_t))
        day_i, hr_i = int(m.group(3)), min(23, int(m.group(4)))
        cands: List[datetime] = []
        for d_off in (-16, 0, 16):
            anc = ref_utc + timedelta(days=d_off)
            try:
                cands.append(datetime(anc.year, anc.month, day_i, hr_i, 0, tzinfo=timezone.utc))
            except ValueError:
                continue
        if not cands:
            continue
        valid_utc = min(cands, key=lambda c: abs((c - ref_utc).total_seconds()))
        loc_date = valid_utc.astimezone(tz).date()
        rec = out.setdefault(loc_date, {})
        if kind == "HIGH":
            rec["HIGH"] = max(rec.get("HIGH", -999.0), temp_c)
        else:
            rec["LOW"] = min(rec.get("LOW", 999.0), temp_c)
    return out


def fetch_taf_extremes_sync(
    icao: str,
    obs_date: date,
    tz_name: str,
    timeout: float = 5.0,
) -> Dict[str, float]:
    """Fetches official `aviationweather.gov/api/data/taf` `TX`/`TN` runway extremes for `(icao, obs_date)`."""
    url = f"{AWC_TAF_URL}?ids={icao.upper()}&format=raw"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
        raw_txt = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
        by_date = parse_taf_temperature_extremes(raw_txt, icao, datetime.now(timezone.utc), tz_name)
        return dict(by_date.get(obs_date) or {})
    except Exception:
        return {}


def verify_weather_slate_partition(spec: WeatherEventSpec) -> bool:
    """
    Verifies that `spec.buckets` forms an exact, gap-free, non-overlapping integer partition
    over `[-60, 140]` so exactly ONE bucket resolves `YES = $1.00` (`ChatGPT #5`).
    """
    if len(spec.buckets) < 3:
        return False
    for k in range(-60, 141):
        hits = sum(1 for b in spec.buckets if b.contains_rounded(k))
        if hits != 1:
            return False
    return True


def evaluate_weather_event_slate(
    spec: WeatherEventSpec,
    probs: List[float],
    bucket_books: Dict[str, Dict[str, Any]],
    target_budget_usd: float = 10.0,
    max_underround_sum: float = 0.985,
) -> Dict[str, Any]:
    """
    Event-Level Weather Slate Arbitrage & Constrained Subset Optimizer (`Gemini #10` + `ChatGPT #5`):
      1. `FULL_SLATE_DUTCH_ARB`: When `verify_weather_slate_partition(spec)` is True and
         `sum_i ask_yes(i) <= max_underround_sum` (`0%` weather fees!), equal shares across all
         buckets lock a deterministic riskless `$1.00 - sum_asks` payout!
      2. `CONSTRAINED_SUBSET_BASKET`: Multi-bucket positive-EV adjacent subset (`2..3` buckets)
         maximizing `EV_net` subject to total basket cost `<= $0.88/share` and combined win prob `>= 0.72`.
    """
    partition_ok = verify_weather_slate_partition(spec)
    rows: List[Dict[str, Any]] = []
    for idx, b in enumerate(spec.buckets):
        bk = bucket_books.get(b.market_id) or {}
        ask_y = bk.get("ask_yes")
        ask_sz = float(bk.get("ask_yes_shares") or 0.0)
        p_b = float(probs[idx]) if idx < len(probs) else 0.0
        if ask_y is not None and 0.005 <= float(ask_y) <= 0.99 and ask_sz >= 5.0:
            rows.append({
                "idx": idx,
                "market_id": b.market_id,
                "label": b.label,
                "yes_token": b.yes_token,
                "ask_yes": float(ask_y),
                "ask_yes_shares": ask_sz,
                "prob": p_b,
                "edge": p_b - float(ask_y),
            })

    full_slate: Optional[Dict[str, Any]] = None
    if partition_ok and len(rows) == len(spec.buckets):
        sum_asks = sum(r["ask_yes"] for r in rows)
        min_sh = min(r["ask_yes_shares"] for r in rows)
        if sum_asks <= max_underround_sum and min_sh >= 5.0:
            equal_sh = max(5.0, min(min_sh, math.floor(float(target_budget_usd) / max(0.10, sum_asks))))
            if equal_sh * sum_asks <= float(target_budget_usd) * 1.25:
                full_slate = {
                    "mode": "FULL_SLATE_DUTCH_ARB",
                    "sum_asks": round(sum_asks, 5),
                    "guaranteed_edge_per_set": round(1.0 - sum_asks, 5),
                    "equal_shares": float(equal_sh),
                    "total_cost_usd": round(equal_sh * sum_asks, 4),
                    "guaranteed_profit_usd": round(equal_sh * (1.0 - sum_asks), 4),
                    "legs": rows,
                }

    # Constrained positive-EV subset (2-3 buckets with individual edge >= +0.04, combined prob >= 0.72, sum_asks <= 0.88)
    pos_rows = sorted([r for r in rows if r["edge"] >= 0.04], key=lambda x: x["edge"], reverse=True)
    best_subset: Optional[Dict[str, Any]] = None
    if len(pos_rows) >= 2:
        cand_legs = pos_rows[:3]
        sum_sub_asks = sum(r["ask_yes"] for r in cand_legs)
        sum_sub_prob = min(0.999, sum(r["prob"] for r in cand_legs))
        min_sub_sh = min(r["ask_yes_shares"] for r in cand_legs)
        net_edge_set = sum_sub_prob - sum_sub_asks
        if sum_sub_asks <= 0.88 and sum_sub_prob >= 0.72 and net_edge_set >= 0.09 and min_sub_sh >= 5.0:
            eq_sh = max(5.0, min(min_sub_sh, math.floor(float(target_budget_usd) / max(0.10, sum_sub_asks))))
            best_subset = {
                "mode": "CONSTRAINED_SUBSET_BASKET",
                "sum_asks": round(sum_sub_asks, 5),
                "combined_prob": round(sum_sub_prob, 5),
                "expected_edge_per_set": round(net_edge_set, 5),
                "equal_shares": float(eq_sh),
                "total_cost_usd": round(eq_sh * sum_sub_asks, 4),
                "max_loss_usd": round(eq_sh * sum_sub_asks, 4),
                "legs": cand_legs,
            }

    return {
        "partition_verified": partition_ok,
        "quoted_buckets": len(rows),
        "total_buckets": len(spec.buckets),
        "full_slate_arb": full_slate,
        "subset_basket": best_subset,
    }
