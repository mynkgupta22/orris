# In file: app/core/paths.py

from pathlib import Path

# 1. Define the Backend Root Directory.
#    This is the most reliable anchor point. It finds the current file's directory
#    (which is 'core'), and goes up two levels (core -> app -> backend) to find
#    the root of your backend project as configured on Render.
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# 2. Define the path to a dedicated 'data' directory for storing state files.
#    It's better practice to use a 'data' folder than the 'config' folder
#    for files that your application writes to.
DATA_DIR = BACKEND_ROOT / "data"

# 3. Define the full, absolute path to the channels file.
#    This will now resolve to a correct and writable path on the Render server,
#    e.g., /opt/render/project/src/backend/data/webhook_channels.json
WEBHOOK_CHANNELS_PATH = DATA_DIR / "webhook_channels.json"


# --- You can keep your other paths if you need them, but define them from the root ---

# Configuration paths (Note: SERVICE_ACCOUNT_PATH is not used in the cloud-native approach)
CONFIG_DIR = BACKEND_ROOT / "config"
SERVICE_ACCOUNT_PATH = CONFIG_DIR / "service-account.json" # Legacy, for local dev
ENV_FILE_PATH = CONFIG_DIR / ".env" # Legacy, for local dev

# Other directory paths
DOCS_DIR = BACKEND_ROOT / "docs"
SCRIPTS_DIR = BACKEND_ROOT / "scripts"
TESTS_DIR = BACKEND_ROOT / "tests"
