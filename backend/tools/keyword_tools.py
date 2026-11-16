"""Local heuristic keyword ideas; no external advertising API."""
from crewai.tools import tool

@tool("Get keyword ideas")
def get_keyword_ideas(seed_keywords: list[str], location: str) -> list[dict]:
    """
    Generates keyword ideas using heuristic expansions.
    This avoids Google Keyword Planner access requirements while still
    producing structured keyword candidates for the pipeline.

    Args:
        seed_keywords: starting keywords e.g. ["pizza austin", "italian food"]
        location:      target location e.g. "Austin, TX"

    Returns:
        List of dicts with text, avg_monthly_searches, cpc, competition
    """
    seeds = [s.strip().lower() for s in seed_keywords if s and s.strip()]
    if not seeds:
        seeds = ["local business"]

    location_phrase = (location or "near me").strip().lower()
    modifiers = [
        "near me",
        location_phrase,
        "best",
        "affordable",
        "same day",
        "open now",
        "reviews",
        "offers",
    ]

    # Keep stable output order while deduplicating expanded variants.
    phrases: list[str] = []
    seen = set()
    for seed in seeds:
        candidates = [
            seed,
            f"{seed} near me",
            f"{seed} {location_phrase}",
            f"best {seed}",
            f"{seed} deals",
            f"{seed} price",
            f"{seed} online",
        ]
        for mod in modifiers:
            candidates.append(f"{seed} {mod}")
        for phrase in candidates:
            clean = " ".join(phrase.split())
            if clean and clean not in seen:
                seen.add(clean)
                phrases.append(clean)

    def _estimate_metrics(text: str, rank: int) -> tuple[int, float, str]:
        score = (sum(ord(ch) for ch in text) % 700) + 200
        volume = max(60, score - (rank * 12))
        cpc = round(0.45 + ((score % 180) / 100), 2)
        if cpc >= 1.8:
            competition = "HIGH"
        elif cpc >= 1.1:
            competition = "MEDIUM"
        else:
            competition = "LOW"
        return volume, cpc, competition

    results = []
    for idx, phrase in enumerate(phrases[:40]):
        volume, cpc, competition = _estimate_metrics(phrase, idx)
        results.append(
            {
                "text": phrase,
                "avg_monthly_searches": volume,
                "cpc": cpc,
                "competition": competition,
                "estimated": True,
                "source": "heuristic expansion; not Google Keyword Planner data",
            }
        )

    return results


