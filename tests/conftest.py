import os
import tempfile

# All modules share an isolated database and never inherit paid provider credentials.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="quark-test-")
os.environ.pop("DEEPSEEK_API_KEY", None)
