"""
SecureIoT-X Core Configuration Module.

Loads settings from .env and YAML config files.
Provides a single Settings object used throughout the application.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# ── Resolve project root ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# Load .env (if present)
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fall back to .env.example for defaults during development
    _env_example = PROJECT_ROOT / ".env.example"
    if _env_example.exists():
        load_dotenv(_env_example)


def _load_yaml(filename: str) -> Dict[str, Any]:
    """Load a YAML configuration file from the config directory."""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Settings(BaseSettings):
    """Application-wide settings loaded from env vars and config files."""

    # ── Application ────────────────────────────────────────────
    app_name: str = Field(default="SecureIoT-X")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")

    # ── Server ─────────────────────────────────────────────────
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    frontend_port: int = Field(default=3000)

    # ── Database — MongoDB ONLY ────────────────────────────────
    mongodb_uri: str = Field(default="mongodb://localhost:27017/secureiot_x")

    # ── Ganache Blockchain ─────────────────────────────────────
    ganache_rpc_url: str = Field(default="http://127.0.0.1:7545")
    ganache_chain_id: int = Field(default=1337)
    ganache_private_key: str = Field(default="")
    contract_address: str = Field(default="")

    # ── JWT ────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_MIN_32_CHARS")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_minutes: int = Field(default=60)

    # ── MQTT ───────────────────────────────────────────────────
    mqtt_host: str = Field(default="localhost")
    mqtt_port: int = Field(default=1883)
    mqtt_username: str = Field(default="")
    mqtt_password: str = Field(default="")
    mqtt_keepalive: int = Field(default=60)

    # ── Default Admin ──────────────────────────────────────────
    default_admin_username: str = Field(default="admin")
    default_admin_password: str = Field(default="SecureIoT2024!")
    default_admin_email: str = Field(default="admin@secureiot.local")

    # ── AI Engine ──────────────────────────────────────────────
    ml_models_dir: str = Field(default="models")
    ml_dataset_path: str = Field(default="datasets/RT_IOT2022.csv")
    ml_random_seed: int = Field(default=42)
    ml_test_size: float = Field(default=0.2)
    ml_validation_size: float = Field(default=0.1)

    # ── Blockchain ─────────────────────────────────────────────
    blockchain_difficulty: int = Field(default=2)
    blockchain_db_path: str = Field(default="blockchain_ledger.json")

    # ── SDN ────────────────────────────────────────────────────
    sdn_mode: str = Field(default="mock")
    ryu_host: str = Field(default="localhost")
    ryu_port: int = Field(default=6633)

    # ── Telegram Bot Notifications ─────────────────────────────
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # ── YAML-loaded configs (populated post-init) ──────────────
    security_config: Dict[str, Any] = Field(default_factory=dict)
    ml_config: Dict[str, Any] = Field(default_factory=dict)
    mqtt_config: Dict[str, Any] = Field(default_factory=dict)
    app_config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def model_post_init(self, __context: Any) -> None:
        """Load YAML configs after pydantic initialisation."""
        self.app_config = _load_yaml("app.yaml")
        self.security_config = _load_yaml("security.yaml")
        self.ml_config = _load_yaml("ml.yaml")
        self.mqtt_config = _load_yaml("mqtt.yaml")

    # ── Convenience helpers ────────────────────────────────────

    @property
    def risk_thresholds(self) -> Dict[str, Any]:
        return self.security_config.get("risk_thresholds", {})

    @property
    def response_rules(self) -> Dict[str, str]:
        return self.security_config.get("response_rules", {})

    @property
    def severity_weights(self) -> Dict[str, float]:
        return self.security_config.get("severity_weights", {})

    @property
    def attack_severity_scores(self) -> Dict[str, int]:
        return self.security_config.get("attack_severity_scores", {})

    @property
    def confidence_thresholds(self) -> Dict[str, float]:
        return self.security_config.get("confidence_thresholds", {})

    @property
    def cors_origins(self) -> List[str]:
        server = self.app_config.get("server", {})
        return server.get("cors_origins", [
            f"http://localhost:{self.frontend_port}",
            f"http://127.0.0.1:{self.frontend_port}",
        ])

    @property
    def active_mode(self) -> str:
        modes = self.app_config.get("modes", {})
        return modes.get("active_mode", "simulation")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


# Singleton instance
settings = Settings()
