import re, json, time, random
from datetime import datetime, timezone
from dateutil import parser as dtparser
import os
from glob import glob
from pathlib import Path
from datetime import date as _date


def sleep_with_jitter(seconds_min: int, jitter_range=(3,7)):
	# Sleep with jitter to spread requests
	base = seconds_min
	jitter = random.randint(*jitter_range)
	time.sleep(base + jitter)

def to_utc_str(ts) -> str | None:
	# Convert various timestamp formats to ISO UTC string
	if not ts:
		return None
	try:
		if isinstance(ts, (int, float)):
			dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
			return dt.isoformat()
		dt = dtparser.parse(str(ts))
		if dt.tzinfo is None:
			dt = dt.replace(tzinfo=timezone.utc)
		return dt.astimezone(timezone.utc).isoformat()
	except Exception:
		return None

def get_in(obj, path: str):
	# Dot-Notation access with '|' alternatives, e.g. "user.firstName|member.firstName"
	alts = [p.strip() for p in path.split("|")]
	for alt in alts:
		cur = obj
		try:
			for part in alt.split("."):
				if part.endswith("]"):
					m = re.match(r"(.+)\[(\d+)\]", part)
					if not m:
						raise KeyError(part)
					name, idx = m.groups()
					cur = cur[name][int(idx)]
				else:
					cur = cur[part]
			return cur
		except Exception:
			continue
	return None

def deep_iter(obj):
	# Yield all dict nodes from nested structures
	if isinstance(obj, dict):
		yield obj
		for v in obj.values():
			yield from deep_iter(v)
	elif isinstance(obj, list):
		for it in obj:
			yield from deep_iter(it)

def find_member_entries(root):
	"""
	Robustere Heuristik:
	- Falls ein Knoten beide Keys 'user' und 'member' hat -> direkt Treffer.
	- Falls nur 'user' existiert und wie ein User-Objekt aussieht (firstName/lastName/name/id) -> wrappe zu {'user': node, 'member': {}}.
	- Falls nur 'member' existiert, wrappe zu {'user': {}, 'member': node}.
	"""
	for node in deep_iter(root):
		if not isinstance(node, dict):
			continue

		has_user = "user" in node and isinstance(node["user"], dict)
		has_member = "member" in node and isinstance(node["member"], dict)

		if has_user and has_member:
			yield node
			continue

		# User-ähnliche Objekte erkennen (ohne expliziten 'user'-Wrapper)
		if not has_user:
			keys = set(node.keys())
			looks_like_user = any(k in keys for k in ("firstName", "lastName", "name")) and ("id" in keys or "handle" in keys)
			if looks_like_user:
				yield {"user": node, "member": node.get("member", {})}
				continue

		# Member-ähnliche Objekte ohne 'user'
		if not has_member and "member" in node and isinstance(node["member"], dict):
			yield {"user": node.get("user", {}), "member": node["member"]}
			continue

def latest_raw_file(raw_dir: str, tenant: str, route_keyword: str = "members"):
	"""
	Finde die neueste RAW-JSON für einen Tenant (members/leaderboard).
	"""
	tdir = os.path.join(raw_dir, tenant)
	if not os.path.isdir(tdir):
		return None
	# z.B. ...members...json
	candidates = sorted(
		glob(os.path.join(tdir, f"*{route_keyword}*.json")),
		key=lambda p: os.path.getmtime(p),
		reverse=True,
	)
	return candidates[0] if candidates else None


def dict_paths(d, max_len=6, prefix=""):
	"""
	Generator: liefert (path, value)-Paare aller Keys (max depth), um Strukturen zu inspizieren.
	"""
	if max_len < 0:
		return
	if isinstance(d, dict):
		for k, v in d.items():
			p = f"{prefix}.{k}" if prefix else k
			yield p, v
			yield from dict_paths(v, max_len-1, p)
	elif isinstance(d, list):
		# Nur die ersten Einträge betrachten, damit es übersichtlich bleibt
		for i, v in enumerate(d[:3]):
			p = f"{prefix}[{i}]"
			yield p, v
			yield from dict_paths(v, max_len-1, p)


def guess_members_arrays(root):
	"""
	Heuristik: Finde Arrays, die wie eine Members-Liste aussehen.
	Kriterien:
	  - Liste von Objekten
	  - Jedes Objekt hat 'user' oder user-ähnliche Felder (firstName/lastName/name/id)
	Gibt Liste von (pfad, länge) zurück – größte zuerst.
	"""
	results = []
	for path, val in dict_paths(root, max_len=6):
		if isinstance(val, list) and val:
			good = 0
			for item in val[:3]:
				if isinstance(item, dict):
					if "user" in item and isinstance(item["user"], dict):
						good += 1
					else:
						keys = set(item.keys())
						if any(k in keys for k in ("firstName","lastName","name")) and ("id" in keys or "handle" in keys):
							good += 1
			if good >= 2:  # mind. 2 von 3 sehen wie User aus
				results.append((path, len(val)))
	results.sort(key=lambda x: x[1], reverse=True)
	return results

def guess_pagination_hints(root):
	hits = []
	KEYS = {"cursor","nextCursor","next","nextPage","page","hasMore","hasNext","endCursor"}
	for path, val in dict_paths(root, max_len=6):
		key = path.split(".")[-1]
		if key in KEYS:
			if isinstance(val, (int, float, bool)):
				preview = val
			elif isinstance(val, str):
				preview = (val[:80] + "...") if len(val) > 80 else val
			else:
				preview = type(val).__name__
			hits.append((path, preview))
	return hits


# helpers for agents
def reports_dir_for(slug: str) -> Path:
	d = Path("exports") / "reports" / slug
	d.mkdir(parents=True, exist_ok=True)
	return d

def datalake_members_dir_for(slug: str, day: _date | None = None) -> Path:
	base = Path("data_lake") / slug / "members"
	base.mkdir(parents=True, exist_ok=True)
	if day:
		part = base / f"dt={day.isoformat()}"
		part.mkdir(parents=True, exist_ok=True)
		return part
	return base

# re-export network helper
from .net import post_with_retry

__all__ = [
	"sleep_with_jitter",
	"to_utc_str",
	"get_in",
	"deep_iter",
	"find_member_entries",
	"latest_raw_file",
	"guess_pagination_hints",
	"reports_dir_for",
	"datalake_members_dir_for",
	"post_with_retry",
]
