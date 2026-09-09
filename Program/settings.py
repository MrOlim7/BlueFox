"""Temporary compatibility aliases for the former settings module."""
from .config import API_KEY_FIELDS, CONFIG, CONFIG_FILE, config

load_local_config = config.load
save_local_config = config.save
