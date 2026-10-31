"""Learning-video lookup. Never fabricates URLs: real API results when a key is configured and reachable,
otherwise clearly-marked YouTube *search* links."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from app.core.config import get_settings

SEARCHES = [("Full course", "full course for beginners", "beginner"), ("Tutorial", "tutorial", "beginner"),
            ("Hands-on projects", "projects", "intermediate"), ("Interview questions", "interview questions", "intermediate")]


def search_links(skill_name: str, slug: str) -> list[dict]:
    out = []
    for label, suffix, diff in SEARCHES:
        q = urllib.parse.quote_plus(f"{skill_name} {suffix}")
        out.append({"title": f"{skill_name}: {label}", "channel": None, "url": f"https://www.youtube.com/results?search_query={q}",
                    "skill": slug, "difficulty": diff, "duration": None, "is_search_url": True})
    return out


def _iso_to_minutes(d: str) -> int | None:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:\d+S)?", d or "")
    return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) if m else None


def resources_for(skill_name: str, slug: str) -> list[dict]:  # pragma: no cover - network path
    key = get_settings().YOUTUBE_API_KEY
    if not key:
        return search_links(skill_name, slug)
    try:
        params = urllib.parse.urlencode({"part": "snippet", "q": f"{skill_name} tutorial for beginners", "type": "video", "maxResults": 4, "key": key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/search?{params}", timeout=4) as r:
            items = json.load(r).get("items", [])
        vids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        if not vids:
            return search_links(skill_name, slug)
        p2 = urllib.parse.urlencode({"part": "contentDetails", "id": ",".join(vids), "key": key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/videos?{p2}", timeout=4) as r:
            dur = {i["id"]: _iso_to_minutes(i["contentDetails"]["duration"]) for i in json.load(r).get("items", [])}
        return [{"title": i["snippet"]["title"], "channel": i["snippet"]["channelTitle"], "url": f"https://www.youtube.com/watch?v={i['id']['videoId']}",
                 "skill": slug, "difficulty": None, "duration": dur.get(i["id"]["videoId"]), "is_search_url": False}
                for i in items if i.get("id", {}).get("videoId")]
    except Exception:
        return search_links(skill_name, slug)  # API down, quota, or no network: degrade gracefully
