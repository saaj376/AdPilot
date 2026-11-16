import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

import main
import api.research as api
import api.campaigns as campaigns
import services.video_research as service
from models.research import ResearchRequest, VideoInput, video_id

URL = 'https://www.youtube.com/watch?v=abcdefghijk'


def payload():
    return {
        'product_name': 'HomeSweep', 'product_description': 'A vacuum designed for pet-owning households.',
        'audience': 'Apartment households with pets', 'product_facts': ['Washable filter'],
        'videos': [{'url': URL, 'transcript': '[02:15] Cleaning this filter is expensive.'}],
    }


def analysis(evidence_id='abcdefghijk:0'):
    return {'summary': 'Maintenance cost may be a useful message to test.', 'findings': [{
        'problem': 'Filter maintenance costs', 'category': 'pain_point',
        'evidence_ids': [evidence_id], 'product_fact_ids': [0],
        'hypothesis': 'A washable filter message may address maintenance concerns.',
        'keywords': ['vacuum washable filter'], 'headline': 'Washable Filter Vacuum',
        'description': 'Explore a vacuum with a washable filter.',
        'landing_page_change': 'Explain how to wash the filter.',
        'experiment': 'Compare a filter message with a generic vacuum message.',
        'success_metric': 'Compare purchase conversion rate.'}],
        'limitations': ['Small sample; captions may be inaccurate.']}


@pytest.fixture
def store(monkeypatch):
    records = {}
    async def save(brief):
        records[brief['id']] = json.loads(json.dumps(brief))
    async def load(identifier):
        value = records.get(identifier)
        return json.loads(json.dumps(value)) if value else None
    for module in (service, api):
        monkeypatch.setattr(module, 'save_brief', save)
        monkeypatch.setattr(module, 'load_brief', load)
    monkeypatch.setattr(campaigns, 'load_brief', load)
    return records


@pytest.fixture
def client(monkeypatch):
    async def noop():
        pass
    monkeypatch.setattr(main, 'startup', noop)
    monkeypatch.setattr(main, 'shutdown', noop)
    with TestClient(main.app) as client:
        yield client


@pytest.mark.parametrize('url', [URL, 'https://youtu.be/abcdefghijk?t=3', 'https://youtube.com/shorts/abcdefghijk'])
def test_video_urls_normalized(url):
    assert VideoInput(url=url).url == URL


@pytest.mark.parametrize('url', ['https://evil.com/watch?v=abcdefghijk', 'http://youtu.be/abcdefghijk',
                                'https://youtube.com.evil.com/watch?v=abcdefghijk',
                                'https://youtube.com/playlist?list=123', 'https://youtube.com/watch?v=short'])
def test_non_video_urls_rejected(url):
    with pytest.raises(ValueError):
        video_id(url)


def test_timestamped_fallback_keeps_exact_evidence():
    source = service.collect_source(VideoInput(**payload()['videos'][0]), ['en'])
    assert source['origin'] == 'user_supplied'
    assert source['evidence'][0] == {'id': 'abcdefghijk:0', 'text': 'Cleaning this filter is expensive.',
                                     'seconds': 135, 'url': URL + '&t=135s'}
    with pytest.raises(ValueError):
        VideoInput(url=URL, transcript='untimed text')


def test_caption_fetch_uses_real_snippet_shape(monkeypatch):
    class Transcript(list):
        language_code = 'hi'
        is_generated = True
    monkeypatch.setattr(service, 'YouTubeTranscriptApi', lambda **kwargs: SimpleNamespace(
        fetch=lambda *args, **kwargs: Transcript([SimpleNamespace(start=22.4, text='Filter is hard to clean')])
    ))
    result = service.collect_source(VideoInput(url=URL), ['hi'])
    assert result['language'] == 'hi'
    assert result['origin'] == 'automatic_captions'
    assert result['evidence'][0]['seconds'] == 22.4


def test_create_get_export_and_campaign_handoff(client, store, monkeypatch):
    monkeypatch.setattr(service, 'generate_analysis', AsyncMock(return_value=analysis()))
    response = client.post('/research', json=payload())
    assert response.status_code == 202
    identifier = response.json()['id']
    result = client.get(f'/research/{identifier}').json()
    assert result['status'] == 'ready'
    assert 'transcript' not in result['input']['videos'][0]
    assert result['sources'][0]['evidence'][0]['seconds'] == 135
    assert client.get(f'/research/{identifier}/export').status_code == 200
    assert client.get('/research/missing').status_code == 404
    saved = []
    monkeypatch.setattr(campaigns, 'save_context', AsyncMock(side_effect=lambda *args: saved.append(args[1])))
    monkeypatch.setattr(campaigns, 'add_active_campaign', AsyncMock())
    worker = AsyncMock()
    monkeypatch.setattr(campaigns, 'run_crew', worker)
    response = client.post('/campaigns', json={'business_description': payload()['product_description'],
                                              'monthly_budget': 500, 'research_brief_id': identifier})
    assert response.status_code == 202
    assert saved[0].research_brief['analysis'] == analysis()
    assert worker.call_args.kwargs['research_brief']['id'] == identifier


def test_all_sources_unavailable_fails_without_fabrication(client, store, monkeypatch):
    monkeypatch.setattr(service, 'collect_source', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('blocked')))
    generate = AsyncMock()
    monkeypatch.setattr(service, 'generate_analysis', generate)
    response = client.post('/research', json=payload())
    identifier = response.json()['id']
    result = client.get(f'/research/{identifier}').json()
    assert result['status'] == 'failed'
    assert result['analysis'] is None
    generate.assert_not_called()
    assert client.get(f'/research/{identifier}/export').status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize('bad', ['citation', 'fact'])
async def test_model_references_are_checked(monkeypatch, bad):
    result = analysis('made-up:0' if bad == 'citation' else 'abcdefghijk:0')
    if bad == 'fact':
        result['findings'][0]['product_fact_ids'] = [99]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'message': {'content': json.dumps(result)}}))
    original = httpx.AsyncClient
    monkeypatch.setattr(service.httpx, 'AsyncClient', lambda **kwargs: original(transport=transport, **kwargs))
    request = ResearchRequest(**payload())
    sources = [service.collect_source(request.videos[0], ['en'])]
    with pytest.raises(ValueError):
        await service.generate_analysis(request, sources)


def test_duplicate_sources_and_empty_facts_rejected(client):
    value = payload()
    value['videos'] *= 2
    assert client.post('/research', json=value).status_code == 422
    value = payload()
    value['product_facts'] = ['  ']
    assert client.post('/research', json=value).status_code == 422
