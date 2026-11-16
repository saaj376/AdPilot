"""Validated inputs and evidence references for product research."""
import re
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, Field, field_validator


def video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
        raise ValueError('Use an HTTPS YouTube video link')
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    candidate = ''
    if host == 'youtu.be' and len(parts) == 1:
        candidate = parts[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            candidate = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in {'shorts', 'embed', 'live'}:
            candidate = parts[1]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
        raise ValueError('Provide a YouTube watch, Shorts, or youtu.be video URL')
    return candidate


class VideoInput(BaseModel):
    url: str = Field(max_length=500)
    # A practical fallback for blocked or unavailable captions. One timed line per excerpt.
    transcript: str = Field(default='', max_length=30000)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        return f'https://www.youtube.com/watch?v={video_id(value.strip())}'

    @field_validator('transcript')
    @classmethod
    def validate_transcript(cls, value):
        for line in value.splitlines():
            if line.strip() and not re.match(r'^\[(?:\d{1,2}:)?\d{1,2}:[0-5]\d\]\s+\S', line.strip()):
                raise ValueError('Transcript lines must start with [MM:SS] or [HH:MM:SS]')
        return value.strip()


class ResearchRequest(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_description: str = Field(min_length=20, max_length=4000)
    audience: str = Field(min_length=5, max_length=1000)
    product_facts: list[str] = Field(min_length=1, max_length=15)
    videos: list[VideoInput] = Field(min_length=1, max_length=5)
    languages: list[str] = Field(default=['en', 'hi'], min_length=1, max_length=5)

    @field_validator('product_name', 'product_description', 'audience', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('product_facts', 'languages')
    @classmethod
    def clean_list(cls, values):
        result = list(dict.fromkeys(v.strip() for v in values if v.strip()))
        if not result or any(len(v) > 500 for v in result):
            raise ValueError('Provide nonempty values of at most 500 characters')
        return result

    @field_validator('videos')
    @classmethod
    def unique_videos(cls, values):
        if len({v.url for v in values}) != len(values):
            raise ValueError('Each source video must be unique')
        return values


class Finding(BaseModel):
    problem: str = Field(min_length=5, max_length=600)
    category: str = Field(pattern=r'^(pain_point|objection|desired_feature|purchase_question)$')
    evidence_ids: list[str] = Field(min_length=1, max_length=5)
    product_fact_ids: list[int] = Field(default=[], max_length=15)
    hypothesis: str = Field(min_length=10, max_length=600)
    keywords: list[str] = Field(min_length=1, max_length=8)
    headline: str = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=90)
    landing_page_change: str = Field(min_length=5, max_length=600)
    experiment: str = Field(min_length=10, max_length=600)
    success_metric: str = Field(min_length=5, max_length=300)


class BriefAnalysis(BaseModel):
    summary: str = Field(min_length=10, max_length=1500)
    findings: list[Finding] = Field(min_length=1, max_length=8)
    limitations: list[str] = Field(min_length=1, max_length=8)
