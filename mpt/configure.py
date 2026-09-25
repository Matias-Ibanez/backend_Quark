"""Configure MoneyPrinterTurbo from deployment environment without storing keys in Git."""
import os
import shutil
from pathlib import Path

import toml

root = Path("/MoneyPrinterTurbo")
target = root / "config.toml"
if not target.exists():
    shutil.copyfile(root / "config.example.toml", target)
configuration = toml.load(target)
app = configuration["app"]
app["llm_provider"] = "deepseek"
app["deepseek_api_key"] = os.environ.get("DEEPSEEK_API_KEY", "")
app["deepseek_model_name"] = "deepseek-v4-flash"
app["video_source"] = "pexels"
app["pexels_api_keys"] = [os.environ["PEXELS_API_KEY"]] if os.environ.get("PEXELS_API_KEY") else []
app["max_concurrent_tasks"] = 1
app["max_queued_tasks"] = 2
app["api_key"] = os.environ.get("SHORTS_API_KEY", "")
target.write_text(toml.dumps(configuration), encoding="utf-8")
target.chmod(0o600)
