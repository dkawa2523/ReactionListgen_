from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional
import json

import requests


@dataclass(slots=True)
class SimpleHttpClient:
    timeout_s: int = 20
    cache_dir: Optional[Path] = None
    user_agent: str = "plasma-reaction-builder/0.9"

    def __post_init__(self) -> None:
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str, params: Optional[Dict[str, Any]]) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        payload = json.dumps({"url": url, "params": params or {}}, sort_keys=True).encode("utf-8")
        return self.cache_dir / f"{sha256(payload).hexdigest()}.json"

    def get_json(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cache_path = self._cache_path(url, params)
        if cache_path and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        response = requests.get(url, params=params, timeout=self.timeout_s, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        payload = response.json()
        if cache_path:
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload


    def head_headers(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        response = requests.head(url, params=params, timeout=self.timeout_s, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        return dict(response.headers)

    def get_text(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> str:
        cache_path = self._cache_path(url, params)
        if cache_path and cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload["text"]

        response = requests.get(url, params=params, timeout=self.timeout_s, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        text = response.text
        if cache_path:
            cache_path.write_text(json.dumps({"text": text}, ensure_ascii=False, indent=2), encoding="utf-8")
        return text
