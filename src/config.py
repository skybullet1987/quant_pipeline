from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GCP Infrastructure
    gcp_project_id: str = Field(default="parnasa-498503")
    bq_dataset: str = Field(default="market_data")
    
    # Strategy & Execution Parameters
    bar_interval_hours: int = Field(default=4)
    forward_horizon_bars: int = Field(default=6)        # 24H horizon (6 x 4H bars)
    purge_embargo_bars: int = Field(default=18)          # 72H embargo
    max_gross_leverage: float = Field(default=2.0)
    top_quantile_selection: float = Field(default=0.15)  # Top/Bottom 15% universe
    base_friction_bps: float = Field(default=2.0)        # Maker Post-Only baseline
    
    # Hyperliquid Credentials
    hyperliquid_api_url: str = Field(default="https://api.hyperliquid.xyz")
    hyperliquid_private_key: str = Field(default="")
    hyperliquid_master_address: str = Field(default="")

settings = PipelineSettings()
