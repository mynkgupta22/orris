from pathlib import Path

# Get root directory
ROOT_DIR = Path(__file__).parent.parent.parent

# Configuration paths
CONFIG_DIR = ROOT_DIR / "config"
WEBHOOK_CHANNELS_PATH = CONFIG_DIR / "webhook_channels.json"
SERVICE_ACCOUNT_PATH = CONFIG_DIR / "service-account.json"
ENV_FILE_PATH = CONFIG_DIR / ".env"

# Directory paths
DOCS_DIR = ROOT_DIR / "docs"
SCRIPTS_DIR = ROOT_DIR / "scripts"
TESTS_DIR = ROOT_DIR / "tests"
