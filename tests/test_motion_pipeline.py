import asyncio
import json
import pytest
from fastapi import HTTPException
from backend import motion


class Response:
    status_code = 200
    def __init__(self, data): self.data = data
    def json(self): return self.data


class PipelineClient:
    def __init__(self, folder, reviews, source=True):
        self.folder, self.reviews, self.source = folder, iter(reviews), source
        self.calls = []
    async def post(self, url, headers, json):
        if url.endswith('/quark/video/render'):
            operation = json['operation']
            self.calls.append(operation)
            if operation == 'export': (self.folder/'final.mp4').write_bytes(b'new approved video')
            return Response({'ok':True,'source_hash':json['source_hash'],'seconds':1,'sheet':f"/workspace/hermes/{json['project_id']}/.quark-review.png" if operation=='preview' else None})
        stage = json['model_options']['quark_video_stage']
        self.calls.append(stage)
        if stage in ('create','revise') and self.source:
            (self.folder/'Video.tsx').write_text('export default () => null; // '+stage)
            (self.folder/'plan.md').write_text('Plan confirmado')
            (self.folder/'caption.txt').write_text('Copy para redes')
        content = next(self.reviews) if stage == 'review' else 'Listo.'
        return Response({'choices':[{'message':{'content':content}}], 'usage':{'input_tokens':100,'output_tokens':10,'cache_read_tokens':60},'runtime':{'reviewed_images':['/workspace/hermes/'+'a'*32+'/.quark-review.png'] if stage=='review' else []}})


def produce(client, tmp_path, metrics):
    return asyncio.run(motion.produce(client,'http://hermes:8642/v1/chat/completions',{}, {'messages':[{'role':'system','content':'Contexto confirmado'},{'role':'user','content':'Mi video'}]},tmp_path,'a'*32,{'dimensions':[1080,1920],'seconds':10},metrics))


def test_approved_first_round_exports_once_and_aggregates_usage(tmp_path):
    client = PipelineClient(tmp_path,['{"approved":true,"issues":[]}'])
    metrics = {}
    result = produce(client,tmp_path,metrics)
    assert client.calls == ['create','preview','review','export']
    assert metrics['usage'] == {'input_tokens':200,'output_tokens':20,'cache_read_tokens':120}
    assert 'Listo' in result['choices'][0]['message']['content']


def test_only_one_repair_then_one_recheck_and_one_export(tmp_path):
    client = PipelineClient(tmp_path,['{"approved":false,"issues":["Texto recortado"]}','{"approved":true,"issues":[]}'])
    produce(client,tmp_path,{})
    assert client.calls == ['create','preview','review','revise','preview','review','export']


def test_second_rejection_stops_preserves_sources_and_does_not_publish_old_video(tmp_path):
    old = tmp_path/'final.mp4'; old.write_bytes(b'previous video')
    client = PipelineClient(tmp_path,['{"approved":false,"issues":["Texto recortado"]}']*2)
    metrics = {}
    with pytest.raises(HTTPException,match='problemas visuales'): produce(client,tmp_path,metrics)
    assert client.calls.count('review') == 2 and client.calls.count('revise') == 1
    assert 'export' not in client.calls and old.read_bytes() == b'previous video'
    assert (tmp_path/'Video.tsx').is_file() and metrics['usage']['input_tokens'] == 400


@pytest.mark.parametrize('content',['Listo','{"approved":"true","issues":[]}','{"approved":true,"issues":["recorte"]}','{"approved":false,"issues":[]}','[]'])
def test_unverifiable_review_never_counts_as_approval(content):
    with pytest.raises(HTTPException): motion.verdict(content)


def test_unchanged_source_is_not_rendered_as_new_creation(tmp_path):
    (tmp_path/'Video.tsx').write_text('previous source')
    client = PipelineClient(tmp_path,[],source=False)
    with pytest.raises(HTTPException,match='preparar'): produce(client,tmp_path,{})
    assert client.calls == ['create']


def test_partial_costs_survive_invalid_review(tmp_path):
    client = PipelineClient(tmp_path,['not verified'])
    metrics = {}
    with pytest.raises(HTTPException): produce(client,tmp_path,metrics)
    assert metrics['usage']['input_tokens'] == 200 and 'export' not in client.calls


def test_source_changed_after_visual_approval_is_not_exported(tmp_path):
    class ChangingClient(PipelineClient):
        async def post(self,*args,**kwargs):
            response = await super().post(*args,**kwargs)
            if self.calls[-1] == 'review': (self.folder/'Video.tsx').write_text('unreviewed concurrent change')
            return response
    client = ChangingClient(tmp_path,['{"approved":true,"issues":[]}'])
    with pytest.raises(HTTPException,match='cambió'): produce(client,tmp_path,{})
    assert 'export' not in client.calls


def test_compilation_failure_uses_the_single_repair_budget(tmp_path):
    class BrokenClient(PipelineClient):
        async def post(self,*args,**kwargs):
            if kwargs['json'].get('operation') == 'preview' and 'preview' not in self.calls:
                self.calls.append('preview')
                response = Response({}); response.status_code=422; return response
            return await super().post(*args,**kwargs)
    client = BrokenClient(tmp_path,['{"approved":true,"issues":[]}'])
    produce(client,tmp_path,{})
    assert client.calls == ['create','preview','revise','preview','review','export']


def test_approval_without_native_image_inspection_is_rejected(tmp_path):
    class SkippingClient(PipelineClient):
        async def post(self,*args,**kwargs):
            response = await super().post(*args,**kwargs)
            if self.calls[-1] == 'review': response.data['runtime']['reviewed_images']=[]
            return response
    client = SkippingClient(tmp_path,['{"approved":true,"issues":[]}'])
    with pytest.raises(HTTPException,match='visualmente'): produce(client,tmp_path,{})
    assert 'export' not in client.calls
