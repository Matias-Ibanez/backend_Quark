import unittest
from quark_video import stage_options, render_request, audit_agent
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, AsyncMock
import hashlib
import json


class StageTests(unittest.TestCase):
    def test_nonvideo_request_is_unchanged(self):
        value = {'max_iterations':40,'enabled_toolsets':['terminal','file','vision']}
        self.assertIs(stage_options(value,{}),value)

    def test_stage_limits_and_tools(self):
        for stage,limit,tools in [('create',16,['file','skills','terminal']),('revise',8,['file','skills','terminal']),('review',3,['vision'])]:
            result = stage_options({'max_iterations':40,'enabled_toolsets':['terminal','file','skills','vision','video']},{'quark_video_stage':stage})
            self.assertEqual(result,{'max_iterations':limit,'enabled_toolsets':tools})
        self.assertEqual(stage_options({'max_iterations':2,'enabled_toolsets':['file']},{'quark_video_stage':'create'})['max_iterations'],2)

    def test_unknown_stage_fails_closed(self):
        with self.assertRaises(ValueError): stage_options({}, {'quark_video_stage':'anything'})

    def test_audit_only_counts_successful_contact_sheet_inspections(self):
        agent=SimpleNamespace(_hermes_api_runtime={},tool_complete_callback=None)
        audit_agent(agent, {'quark_video_stage':'review'})
        path='/workspace/hermes/'+'a'*32+'/.quark-review.png'
        agent.tool_complete_callback('1','vision_analyze',{'image_url':path},'{"error":"missing"}')
        agent.tool_complete_callback('1b','vision_analyze',{'image_url':path},'{"success":false,"analysis":"error"}')
        agent.tool_complete_callback('2','read_file',{'image_url':path},'success')
        self.assertEqual(agent._hermes_api_runtime['reviewed_images'],[])
        agent.tool_complete_callback('3','vision_analyze',{'image_url':path},'Image loaded into your context')
        self.assertEqual(agent._hermes_api_runtime['reviewed_images'],[path])

    def test_runtime_sanitizer_preserves_only_safe_review_receipts(self):
        from gateway.platforms.api_server import APIServerAdapter
        path='/workspace/hermes/'+'a'*32+'/.quark-review.png'
        value=APIServerAdapter._sanitize_runtime_metadata(runtime={'provider':'deepseek','model':'deepseek-flash','reviewed_images':[path,'/etc/private'], 'api_key':'never forward'})
        self.assertEqual(value['reviewed_images'],[path])
        self.assertNotIn('api_key',value)

    def test_raw_completion_turn_carries_review_receipt_without_a_model_lock(self):
        from gateway.platforms.api_server import APIServerAdapter
        path='/workspace/hermes/'+'a'*32+'/.quark-review.png'
        agent=SimpleNamespace(_hermes_api_runtime={'reviewed_images':[path]},provider='deepseek',model='deepseek-flash')
        adapter=object.__new__(APIServerAdapter)
        result,usage=adapter._finish_turn_result(agent,{},'test',route=None,requested_runtime=None,route_source='global',confirmed_runtime_lock=False)
        self.assertEqual(result['runtime']['reviewed_images'],[path])
        self.assertEqual(usage['runtime']['reviewed_images'],[path])


class RequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_requests_never_launch_renderer(self):
        base = {'project_id':'a'*32,'operation':'preview','width':1080,'height':1920,'seconds':10,'source_hash':'x','require_audio':False}
        for request in [{}, {**base,'project_id':'../../etc'}, {**base,'operation':'shell'}, {**base,'seconds':True}, {**base,'width':9999}, {**base,'extra':'command'}]:
            with self.assertRaises(ValueError): await render_request(request)

    async def test_missing_required_audio_preserves_previous_final(self):
        with TemporaryDirectory() as root:
            folder=Path(root)/('a'*32);folder.mkdir()
            source=folder/'Video.tsx';source.write_text('source')
            old=folder/'final.mp4';old.write_bytes(b'previous')
            staged=folder/'.quark-final.mp4';staged.write_bytes(b'silent new video')
            node=SimpleNamespace(returncode=0,communicate=AsyncMock(return_value=(b'{"ok":true,"elapsedSeconds":1}',b'')))
            probe=SimpleNamespace(returncode=0,communicate=AsyncMock(return_value=(json.dumps({'format':{'duration':'10'},'streams':[{'codec_type':'video','width':1080,'height':1920}]}).encode(),b'')))
            body={'project_id':'a'*32,'operation':'export','width':1080,'height':1920,'seconds':10,'source_hash':hashlib.sha256(source.read_bytes()).hexdigest(),'require_audio':True}
            with patch('quark_video.Path',side_effect=lambda p: Path(root) if p=='/workspace/hermes' else Path(p)), patch('quark_video.asyncio.create_subprocess_exec',new=AsyncMock(side_effect=[node,probe])):
                with self.assertRaises(RuntimeError): await render_request(body)
            self.assertEqual(old.read_bytes(),b'previous')
            self.assertFalse(staged.exists())


if __name__ == '__main__': unittest.main()
