#!/usr/bin/env python3
"""willhaben-Watcher mit mehreren Suchagenten.

Env:
  SEARCHES     JSON-Liste, z. B.
               [{"name": "rennrad", "url": "https://...", "topic": "mein-topic",
                 "max_price": 800, "exclude": ["defekt", "bastler"]}]
               Pflicht: name (eindeutig), url, topic. Optional: max_price, exclude.
  NTFY_SERVER  optional, Default https://ntfy.sh
  (Legacy: SEARCH_URLS + NTFY_TOPIC funktionieren weiterhin als einfache Variante.)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

STATE_FILE = Path("seen.json")  # Format: {agent_name: {ad_id: timestamp}}
MAX_SEEN = 1000                 # IDs pro Agent
MAX_PUSHES_PER_RUN = 8          # pro Agent und Lauf
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
}
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def fetch_ads(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    m = NEXT_DATA_RE.search(r.text)
    if not m:
        raise RuntimeError("__NEXT_DATA__ nicht gefunden (Seitenstruktur geändert oder geblockt?)")
    data = json.loads(m.group(1))
    summaries = data["props"]["pageProps"]["searchResult"]["advertSummaryList"]["advertSummary"]

    ads = []
    for ad in summaries:
        attrs = {
            a["name"]: a.get("values", [])
            for a in ad.get("attributes", {}).get("attribute", [])
        }

        def first(key: str) -> str:
            vals = attrs.get(key) or []
            return vals[0] if vals else ""

        try:
            price_num = float(first("PRICE").replace(",", "."))
        except ValueError:
            price_num = None

        ad_id = str(ad["id"])
        seo = first("SEO_URL")
        link = (
            f"https://www.willhaben.at/{seo.lstrip('/')}"
            if seo
            else f"https://www.willhaben.at/iad/object?adId={ad_id}"
        )
        ads.append(
            {
                "id": ad_id,
                "title": ad.get("description", "(ohne Titel)"),
                "price": first("PRICE_FOR_DISPLAY"),
                "price_num": price_num,
                "location": first("LOCATION"),
                "url": link,
            }
        )
    return ads


def notify(server: str, topic: str, title: str, message: str, click: str | None = None):
    payload = {"topic": topic, "title": title, "message": message, "tags": ["mag"]}
    if click:
        payload["click"] = click
    r = requests.post(server, json=payload, timeout=15)
    r.raise_for_status()


def load_searches() -> list[dict]:
    raw = os.environ.get("SEARCHES", "").strip()
    if raw:
        searches = json.loads(raw)
    else:  # Legacy-Modus
        urls = [u.strip() for u in os.environ.get("SEARCH_URLS", "").splitlines() if u.strip()]
        topic = os.environ.get("NTFY_TOPIC", "").strip()
        searches = (
            [{"name": f"suche{i + 1}", "url": u, "topic": topic} for i, u in enumerate(urls)]
            if urls and topic
            else []
        )
    for s in searches:
        for key in ("name", "url", "topic"):
            if not s.get(key):
                raise ValueError(f"Suchagent ohne '{key}': {s}")
    names = [s["name"] for s in searches]
    if len(set(names)) != len(names):
        raise ValueError("Agent-Namen müssen eindeutig sein")
    return searches


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    # altes Flat-Format (id -> timestamp) ignorieren, Agenten starten dann neu
    if not all(isinstance(v, dict) for v in state.values()):
        return {}
    return state


def prune(seen: dict) -> dict:
    items = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)[:MAX_SEEN]
    return dict(items)


def matches(ad: dict, s: dict) -> bool:
    max_price = s.get("max_price")
    if max_price is not None and ad["price_num"] is not None and ad["price_num"] > max_price:
        return False
    title = ad["title"].lower()
    return not any(w.lower() in title for w in s.get("exclude", []))


def main() -> int:
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").strip()
    try:
        searches = load_searches()
    except Exception as e:  # noqa: BLE001
        print(f"Konfigurationsfehler: {e}", file=sys.stderr)
        return 2
    if not searches:
        print("Keine Suchagenten konfiguriert (SEARCHES setzen)", file=sys.stderr)
        return 2

    old_state = load_state()
    new_state = {}
    now = int(time.time())
    cache: dict[str, list[dict]] = {}
    errors = 0

    for s in searches:
        name = s["name"]
        try:
            if s["url"] not in cache:
                cache[s["url"]] = fetch_ads(s["url"])
            ads = cache[s["url"]]
        except Exception as e:  # noqa: BLE001
            errors += 1
            print(f"[{name}] Fehler: {e}", file=sys.stderr)
            if name in old_state:
                new_state[name] = old_state[name]
            continue

        seen = old_state.get(name)
        first_run = seen is None
        seen = dict(seen or {})
        new_ads = [a for a in ads if a["id"] not in seen]
        for a in new_ads:
            seen[a["id"]] = now

        try:
            if first_run:
                print(f"[{name}] Erster Lauf: {len(new_ads)} Anzeigen vorgemerkt")
                notify(server, s["topic"], f"Suchagent '{name}' aktiv",
                       f"{len(new_ads)} bestehende Anzeigen vorgemerkt. Ab jetzt nur neue.")
            else:
                hits = [a for a in new_ads if matches(a, s)]
                print(f"[{name}] {len(new_ads)} neu, {len(hits)} passen zu den Filtern")
                for ad in hits[:MAX_PUSHES_PER_RUN]:
                    body = " · ".join(x for x in (ad["price"], ad["location"]) if x) or "Neue Anzeige"
                    try:
                        notify(server, s["topic"], ad["title"][:100], body, click=ad["url"])
                    except Exception as e:  # noqa: BLE001
                        print(f"[{name}] Push fehlgeschlagen, neuer Versuch beim nächsten Lauf: {e}",
                              file=sys.stderr)
                        seen.pop(ad["id"], None)
                if len(hits) > MAX_PUSHES_PER_RUN:
                    notify(server, s["topic"], f"'{name}': weitere neue Anzeigen",
                           f"+{len(hits) - MAX_PUSHES_PER_RUN} weitere, bitte auf willhaben nachsehen.")
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] Benachrichtigung fehlgeschlagen: {e}", file=sys.stderr)

        new_state[name] = prune(seen)

    STATE_FILE.write_text(json.dumps(new_state, indent=0, ensure_ascii=False), encoding="utf-8")
    # Nur hart fehlschlagen, wenn ALLE Agenten kaputt waren -> GitHub schickt dir dann eine Mail
    return 1 if errors == len(searches) else 0


if __name__ == "__main__":
    sys.exit(main())
