
"""
Modul zum Abrufen von Daten aus Skool-Communities.
Enthält die Klasse SkoolFetcher, die HTTP-Anfragen stellt und Cookies aus DB oder Datei lädt.
"""
import os, json, time, re
from dotenv import load_dotenv
load_dotenv()
import requests
from bs4 import BeautifulSoup
from .config import settings

class SkoolFetcher:
    """
    Hilfsklasse zum Abrufen von Daten aus Skool-Gruppen.
    Verwaltet Session, Cookie und stellt Methoden zum Laden von Daten bereit.
    """
    def __init__(self, base_url: str, group_path: str, cookie_header: str, tenant_slug: str):
        self.base_url = base_url.rstrip("/")
        self.group_path = group_path.strip("/")
        # NEU: Cookie aus DB ODER aus cookie.txt holen
        self.cookie_header = self._cookie_from_db_or_file(cookie_header)
        self.tenant = tenant_slug
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.user_agent,
            "Accept": "text/html,application/json",
        })

    # --- NEU: Cookie-Loader (DB -> Datei) ---------------------------------
    def _cookie_from_db_or_file(self, cookie_header: str | None) -> str:
        """
        Lädt den Cookie entweder direkt aus dem Parameter oder aus der Umgebungsvariable.
        """
        if cookie_header and cookie_header.strip() and "auth_token=" in cookie_header:
            return cookie_header.strip()
        env_cookie = os.getenv("SKOOL_COOKIE")
        if env_cookie and "auth_token=" in env_cookie:
            return env_cookie.strip()
        raise RuntimeError("Kein gültiger Cookie gefunden. Bitte SKOOL_COOKIE in .env setzen.")

    # --------- intern: Next.js Data-Routen robust abrufen (ohne 307) ----------
    def _get_next_data_json(self, url: str, referer_tail: str):
        """
        Holt eine Next.js-Datenroute so, dass keine 307-Redirects passieren.
        Wichtig: x-nextjs-data + sinnvoller Referer + Cookie.
        """
        headers = {
            "Cookie": self.cookie_header,
            "Accept": "*/*",
            "x-nextjs-data": "1",
            "Referer": f"{self.base_url}/{self.group_path}/{referer_tail}".rstrip("/"),
        }
        resp = self.session.get(url, headers=headers, timeout=30, allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            raise RuntimeError(f"Next.js Redirect {resp.status_code} für {url} – meist fehlt x-nextjs-data/Referer/Cookie.")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("pageProps", {}).get("__N_REDIRECT"):
            raise RuntimeError(f"Next.js Redirect-JSON für {url} – prüfe Cookie/Referer/Build-ID.")
        return data

    # --------- Hilfen zum Speichern / buildId finden ----------
    def _safe_name(self, text: str) -> str:
        import re as _re
        cleaned = _re.sub(r'[^A-Za-z0-9._-]+', '_', text)
        return cleaned[:140]

    def _save_raw(self, route_path: str, build_id: str | None, data: dict):
        ts = time.strftime("%Y%m%dT%H%M%S")
        safe_route = self._safe_name(route_path.strip("/"))
        fname = f"{self._safe_name(self.tenant)}__{safe_route}__{ts}.json"
        from .config import settings as cfg
        outdir = os.path.join(cfg.raw_dir, self.tenant)
        os.makedirs(outdir, exist_ok=True)
        fpath = os.path.join(outdir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return fpath

    def _discover_build_id_from(self, page_tail: str) -> str:
        url = f"{self.base_url}/{self.group_path}/{page_tail}" if self.group_path else f"{self.base_url}/{page_tail}"
        resp = self.session.get(url, timeout=30, headers={"Cookie": self.cookie_header})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.text:
            m = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
            if not m:
                raise RuntimeError("Konnte buildId nicht finden.")
            return m.group(1)
        data = json.loads(script.text)
        build = data.get("buildId")
        if not build:
            raise RuntimeError("buildId fehlt in __NEXT_DATA__.")
        return build

    def discover_build_id(self) -> str:
        return self._discover_build_id_from("-/members")

    # --------- Members JSON ----------
    def fetch_members_json(self, build_id: str):
        group = self.group_path
        route = f"/_next/data/{build_id}/{group}/-/members.json?group={group}" if group else f"/_next/data/{build_id}/-/members.json"
        url = f"{self.base_url}{route}"
        data = self._get_next_data_json(url, referer_tail="-/members")
        fpath = self._save_raw(route, build_id, data)
        return data, route, fpath

    def fetch_members_json_with_params(self, build_id: str, extra_params: dict | None = None):
        group = self.group_path
        base = f"/_next/data/{build_id}/{group}/-/members.json?group={group}" if group else f"/_next_data/{build_id}/-/members.json"
        if extra_params:
            from urllib.parse import urlencode
            route = base + "&" + urlencode(extra_params, doseq=True)
        else:
            route = base
        url = f"{self.base_url}{route}"
        data = self._get_next_data_json(url, referer_tail="-/members")
        fpath = self._save_raw(route, build_id, data)
        return data, route, fpath

    def fetch_members_json_page(self, build_id: str, page: int):
        params = {} if page in (None, 1) else {"page": page}
        return self.fetch_members_json_with_params(build_id, params)

    # --------- Leaderboards JSON (Plural!) ----------
    def _looks_like_leaderboard(self, data: dict) -> bool:
        try:
            def deep_iter(x):
                if isinstance(x, dict):
                    yield x
                    for v in x.values():
                        yield from deep_iter(v)
                elif isinstance(x, list):
                    for it in x:
                        yield from deep_iter(it)
            for node in deep_iter(data):
                if isinstance(node, dict):
                    keys = set(node.keys())
                    if {"userId", "points"}.issubset(keys) or {"user", "points"}.issubset(keys):
                        return True
            return False
        except Exception:
            return False

    def fetch_leaderboard_json(self, window: str = None, build_id: str | None = None):
        group = self.group_path

        def add_win(route: str) -> str:
            if window:
                sep = "&" if "?" in route else "?"
                return f"{route}{sep}window={window}"
            return route

        candidates = [
            add_win(f"/{group}/-/leaderboards.json?group={group}"),
            add_win(f"/leaderboards.json?group={group}"),
            add_win(f"/api/leaderboards?group={group}"),
            add_win(f"/api/leaderboards.json?group={group}"),
        ]

        if not build_id:
            try:
                build_id = self.discover_build_id()
            except Exception:
                build_id = None
        if build_id:
            candidates.append(add_win(f"/_next/data/{build_id}/{group}/-/leaderboards.json?group={group}"))

        last_err = None
        for route in candidates:
            url = f"{self.base_url}{route}"
            try:
                if "/_next/data/" in route:
                    data = self._get_next_data_json(url, referer_tail="-/leaderboards")
                else:
                    headers = {
                        "Cookie": self.cookie_header,
                        "Accept": "application/json",
                        "Referer": f"{self.base_url}/{group}/-/leaderboards",
                        "User-Agent": settings.user_agent,
                    }
                    resp = self.session.get(url, headers=headers, timeout=30, allow_redirects=False)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        raise RuntimeError(f"Redirect {resp.status_code} für {route}")
                    resp.raise_for_status()
                    data = resp.json()

                if not isinstance(data, dict):
                    raise RuntimeError("Antwort ist kein JSON-Objekt.")
                if self._looks_like_leaderboard(data):
                    fpath = self._save_raw(route, build_id, data)
                    return data, route, fpath
                last_err = RuntimeError(f"Kein Leaderboard-Schema bei {route}")
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(f"Keine Leaderboard-Route gefunden. Letzter Fehler: {last_err}")

    def fetch_leaderboard_page(self, window: str, offset: int = 0, limit: int = 100):
        group = self.group_path
        route = f"/leaderboards.json?group={group}&window={window}&offset={offset}&limit={limit}"
        url = f"{self.base_url}{route}"
        headers = {
            "Cookie": self.cookie_header,
            "Accept": "application/json",
            "Referer": f"{self.base_url}/{group}/-/leaderboards",
            "User-Agent": settings.user_agent,
        }
        resp = self.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        fpath = self._save_raw(route, None, data)
        return data, route, fpath

