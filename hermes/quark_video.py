"""Private rendering bridge and bounded native-agent stages for QUARK motion videos."""
import asyncio
import hashlib
import json
import os
import re
import signal
from pathlib import Path


def stage_options(kwargs, options):
    stage = (options or {}).get('quark_video_stage')
    if stage is None:
        return kwargs
    policies = {'create': (16, {'terminal', 'file', 'skills'}), 'revise': (8, {'terminal', 'file', 'skills'}), 'review': (3, {'vision'})}
    if stage not in policies:
        raise ValueError('Unknown QUARK video stage')
    limit, tools = policies[stage]
    kwargs['max_iterations'] = min(kwargs['max_iterations'], limit)
    kwargs['enabled_toolsets'] = sorted(set(kwargs['enabled_toolsets']) & tools)
    return kwargs


def audit_agent(agent, options):
    if (options or {}).get('quark_video_stage') != 'review':
        return
    agent._hermes_api_runtime['reviewed_images'] = []
    previous = agent.tool_complete_callback
    def completed(call_id, name, args, result):
        if name == 'vision_analyze':
            path = str(args.get('image_url', '')).removeprefix('file://')
            try:
                data = json.loads(result) if isinstance(result,str) else result
                successful = isinstance(data,dict) and (data.get('_multimodal') is True or (data.get('success') is True and bool(data.get('analysis')))) and not data.get('error')
            except (ValueError, TypeError, AttributeError):
                successful = isinstance(result,str) and result.startswith(('Image loaded into your context', 'Image attached natively for the main model'))
            if successful and re.fullmatch(r'/workspace/hermes/[a-f0-9]{32}/\.quark-review\.png', path):
                agent._hermes_api_runtime['reviewed_images'].append(path)
        if previous:
            return previous(call_id, name, args, result)
    agent.tool_complete_callback = completed


async def render_request(body):
    if not isinstance(body, dict) or set(body) != {'project_id', 'operation', 'width', 'height', 'seconds', 'source_hash', 'require_audio'} or type(body['require_audio']) is not bool:
        raise ValueError('Invalid render request')
    pid, operation = body['project_id'], body['operation']
    if not isinstance(pid, str) or not re.fullmatch('[a-f0-9]{32}', pid) or operation not in ('preview', 'export'):
        raise ValueError('Invalid project or operation')
    for key, low, high in [('width', 320, 2160), ('height', 320, 2160), ('seconds', 5, 180)]:
        if type(body[key]) is not int or not low <= body[key] <= high:
            raise ValueError('Invalid dimensions or duration')
    folder = Path('/workspace/hermes') / pid
    source = folder / 'Video.tsx'
    if folder.resolve().parent != Path('/workspace/hermes').resolve() or source.resolve().parent != folder.resolve() or not source.is_file() or source.stat().st_size > 262144:
        raise ValueError('Source missing or outside project')
    expected = body['source_hash']
    if not isinstance(expected, str) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError('Source changed before rendering')
    destination = folder / ('.quark-review.png' if operation == 'preview' else '.quark-final.mp4')
    args = ['node', '/opt/quark-renderer/render-video.mjs']
    if operation == 'preview':
        args.append('--preview')
    args += [str(source), str(destination), *[str(body[k]) for k in ('width', 'height', 'seconds')]]
    process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=240)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        os.killpg(process.pid, signal.SIGKILL)  # Also stop Chromium/esbuild children on cancellation.
        await process.wait()
        raise
    if process.returncode:
        raise RuntimeError('Render process failed')
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        destination.unlink(missing_ok=True)
        raise ValueError('Source changed during rendering')
    result = json.loads(stdout.decode().strip().splitlines()[-1])
    if not result.get('ok'):
        raise RuntimeError('Render did not complete')
    if operation == 'export':
        probe = await asyncio.create_subprocess_exec('ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', str(destination), stdout=asyncio.subprocess.PIPE)
        raw, _ = await asyncio.wait_for(probe.communicate(), timeout=20)
        info = json.loads(raw)
        if probe.returncode or abs(float(info['format']['duration']) - body['seconds']) > .15 or not any(s.get('codec_type') == 'video' and s.get('width') == body['width'] and s.get('height') == body['height'] for s in info['streams']) or (body['require_audio'] and not any(s.get('codec_type') == 'audio' for s in info['streams'])):
            destination.unlink(missing_ok=True)
            raise RuntimeError('Invalid final video')
        destination.replace(folder / 'final.mp4')
    return {'ok': True, 'source_hash': expected, 'seconds': result['elapsedSeconds'], 'sheet': str(destination) if operation == 'preview' else None}
