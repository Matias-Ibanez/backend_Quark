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
text = text.replace(before_chat, after_chat)

# Keep QUARK policy local to authenticated requests; other Hermes consumers stay unchanged.
before_stage = '        agent = AIAgent(**agent_kwargs)'
after_stage = '''        from quark_video import stage_options
        agent_kwargs = stage_options(agent_kwargs, model_options)
        agent = AIAgent(**agent_kwargs)'''
before_route = '            ("POST", "/api/jobs", self._handle_create_job),'
after_route = before_route + '\n            ("POST", "/quark/video/render", self._handle_quark_video_render),'
before_handler = '    async def _handle_health(self, request: "web.Request") -> "web.Response":'
after_handler = '''    @_require_auth
    async def _handle_quark_video_render(self, request: "web.Request") -> "web.Response":
        from quark_video import render_request
        try:
            result = await render_request(await request.json())
            return web.json_response(result)
        except (ValueError, OSError):
            return _invalid_request("Invalid QUARK render request")
        except (RuntimeError, asyncio.TimeoutError):
            logger.exception("QUARK local render failed")
            return _error_response("Local render failed", 422)

''' + before_handler
for old, new in [(before_stage, after_stage), (before_route, after_route), (before_handler, after_handler)]:
    if text.count(old) != 1:
        raise SystemExit('Hermes video boundary changed; review local patch')
    text = text.replace(old, new)
before_audit = '        return agent\n\n    # -- HTTP handlers'
if text.count(before_audit) != 1:
    raise SystemExit('Hermes runtime boundary changed; review local audit patch')
text = text.replace(before_audit, '''        from quark_video import audit_agent
        audit_agent(agent, model_options)
        return agent

    # -- HTTP handlers''')
before_receipt = '''        if requested_runtime or payload.get("requested"):
            model, provider = cls._requested_ids(requested_runtime or payload.get("requested"))'''
after_receipt = '''        if isinstance(payload.get("reviewed_images"), list):
            result["reviewed_images"] = [path for path in payload["reviewed_images"][:6]
                if isinstance(path, str) and re.fullmatch(r"/workspace/hermes/[a-f0-9]{32}/\\.quark-review\\.png", path)]
''' + before_receipt
if text.count(before_receipt) != 1:
    raise SystemExit('Hermes runtime sanitization changed; review video receipt patch')
text = text.replace(before_receipt, after_receipt)
before_finish = '        if requested_runtime or route or confirmed_runtime_lock or (route_source and route_source != "global"):'
after_finish = '        if requested_runtime or route or confirmed_runtime_lock or (route_source and route_source != "global") or "reviewed_images" in getattr(agent, "_hermes_api_runtime", {}):'
if text.count(before_finish) != 1:
    raise SystemExit('Hermes turn metadata boundary changed; review video receipt patch')
text = text.replace(before_finish, after_finish)
source.write_text(text)

# The OpenAI-compatible envelope otherwise omits the runtime receipt entirely.
chat_source = Path('/opt/hermes/gateway/platforms/api_server_openai_routes.py')
chat_text = chat_source.read_text()
before_envelope = '            "usage": _chat_usage_payload(usage)}'
after_envelope = before_envelope + '''
        if isinstance(body.get("model_options"), dict) and body["model_options"].get("quark_video_stage"):
            response_data["runtime"] = self._result_runtime(result, usage)
'''
if chat_text.count(before_envelope) != 1:
    raise SystemExit('Hermes completion envelope changed; review video receipt patch')
chat_source.write_text(chat_text.replace(before_envelope, after_envelope))
