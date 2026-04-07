from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote
import json

from .http import SimpleHttpClient
from ..model import IdentityRecord


class PubChemIdentityAdapter:
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, *, http: Optional[SimpleHttpClient] = None, snapshot_path: Optional[str] = None, live_api: bool = False) -> None:
        self.http = http or SimpleHttpClient()
        self.live_api = live_api
        self.snapshot: Dict[str, Dict[str, Any]] = {}
        if snapshot_path:
            self.snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))

    @staticmethod
    def snapshot_key(namespace: str, query: str) -> str:
        return f"{namespace}:{query}".lower()

    @staticmethod
    def record_to_snapshot_payload(record: IdentityRecord) -> Dict[str, Any]:
        return {
            "query": record.query,
            "namespace": record.namespace,
            "cid": record.cid,
            "title": record.title,
            "formula": record.formula,
            "molecular_weight": record.molecular_weight,
            "smiles": record.smiles,
            "inchi": record.inchi,
            "inchikey": record.inchikey,
            "synonyms": list(record.synonyms),
            "candidate_count": record.candidate_count,
            "ambiguous": record.ambiguous,
            "source_url": record.source_url,
        }

    @staticmethod
    def _snapshot_key(namespace: str, query: str) -> str:
        return PubChemIdentityAdapter.snapshot_key(namespace, query)

    def resolve(self, query: str, namespace: str = "name") -> Optional[IdentityRecord]:
        snap_key = self.snapshot_key(namespace, query)
        if snap_key in self.snapshot:
            return IdentityRecord(**self.snapshot[snap_key])
        if not self.live_api:
            return None

        cids = self._lookup_cids(query=query, namespace=namespace)
        if not cids:
            return IdentityRecord(query=query, namespace=namespace, candidate_count=0, ambiguous=False)

        selected_cid = cids[0]
        props = self._lookup_properties(selected_cid)
        synonyms = self._lookup_synonyms(selected_cid)
        return IdentityRecord(
            query=query,
            namespace=namespace,
            cid=selected_cid,
            title=props.get("Title") or props.get("IUPACName"),
            formula=props.get("MolecularFormula"),
            molecular_weight=float(props["MolecularWeight"]) if props.get("MolecularWeight") is not None else None,
            smiles=props.get("CanonicalSMILES"),
            inchi=props.get("InChI"),
            inchikey=props.get("InChIKey"),
            synonyms=synonyms,
            candidate_count=len(cids),
            ambiguous=len(cids) > 1,
            source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{selected_cid}",
        )

    def _lookup_cids(self, *, query: str, namespace: str) -> list[int]:
        encoded = quote(query, safe="")
        url = f"{self.BASE_URL}/compound/{namespace}/{encoded}/cids/JSON"
        payload = self.http.get_json(url)
        return payload.get("IdentifierList", {}).get("CID", [])

    def _lookup_properties(self, cid: int) -> Dict[str, Any]:
        props = "MolecularFormula,MolecularWeight,CanonicalSMILES,InChI,InChIKey,IUPACName,Title"
        url = f"{self.BASE_URL}/compound/cid/{cid}/property/{props}/JSON"
        payload = self.http.get_json(url)
        items = payload.get("PropertyTable", {}).get("Properties", [])
        return items[0] if items else {}

    def _lookup_synonyms(self, cid: int) -> list[str]:
        url = f"{self.BASE_URL}/compound/cid/{cid}/synonyms/JSON"
        payload = self.http.get_json(url)
        info = payload.get("InformationList", {}).get("Information", [])
        if not info:
            return []
        return list(info[0].get("Synonym", []))[:20]
