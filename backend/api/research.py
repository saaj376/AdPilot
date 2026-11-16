import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response

from models.research import ResearchRequest
from services.video_research import save_brief, load_brief, run_research

router = APIRouter()


@router.post('', status_code=202)
async def create_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    identifier = str(uuid4())
    brief = {'id': identifier, 'status': 'pending', 'created_at': datetime.now(timezone.utc).isoformat(),
             'input': request.model_dump(exclude={'videos': {'__all__': {'transcript'}}}),
             'sources': [], 'analysis': None, 'error': None}
    await save_brief(brief)
    background_tasks.add_task(run_research, identifier, request)
    return brief


@router.get('/{identifier}')
async def get_research(identifier: str):
    brief = await load_brief(identifier)
    if brief is None:
        raise HTTPException(404, 'Research brief not found or expired')
    return brief


@router.get('/{identifier}/export')
async def export_research(identifier: str):
    brief = await get_research(identifier)
    if brief['status'] != 'ready':
        raise HTTPException(409, 'The research brief is not ready for export')
    return Response(json.dumps(brief, indent=2), media_type='application/json',
                    headers={'Content-Disposition': 'attachment; filename="campaign-research.json"'})
