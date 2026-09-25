"""Expose Hermes' existing cache counter in the chat completion usage payload."""
from pathlib import Path

source = Path("/opt/hermes/gateway/platforms/api_server.py")
before = '''        usage = {"input_tokens": getattr(agent, "session_prompt_tokens", 0) or 0,
                 "output_tokens": getattr(agent, "session_completion_tokens", 0) or 0,
                 "total_tokens": getattr(agent, "session_total_tokens", 0) or 0}'''
after = '''        usage = {"input_tokens": getattr(agent, "session_prompt_tokens", 0) or 0,
                 "output_tokens": getattr(agent, "session_completion_tokens", 0) or 0,
                 "cache_read_tokens": max(getattr(agent, "session_cache_read_tokens", 0) or 0,
                                          (getattr(agent, "session_prompt_tokens", 0) or 0)
                                          - (getattr(agent, "session_input_tokens", 0) or 0)),
                 "total_tokens": getattr(agent, "session_total_tokens", 0) or 0}'''
text = source.read_text()
if text.count(before) != 1:
    raise SystemExit("Hermes API usage shape changed; review cache usage patch")
text = text.replace(before, after)
before_chat = '''    return dict(zip(("prompt_tokens", "completion_tokens", "total_tokens"), values))'''
after_chat = '''    result = dict(zip(("prompt_tokens", "completion_tokens", "total_tokens"), values))
    result["cache_read_tokens"] = usage.get("cache_read_tokens", 0)
    return result'''
if text.count(before_chat) != 1:
    raise SystemExit("Hermes chat usage shape changed; review cache usage patch")
source.write_text(text.replace(before_chat, after_chat))
