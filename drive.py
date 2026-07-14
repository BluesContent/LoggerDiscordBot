"""Logica de acesso ao Google Drive: encontrar a pasta de hoje, varrer as pastas
de gravacao (em qualquer profundidade) e verificar se os arquivos Multicorder
estao completos."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Argumentos comuns para funcionar tanto em "Meu Drive" quanto em Drives Compartilhados.
_SHARED = {"supportsAllDrives": True, "includeItemsFromAllDrives": True}

_FOLDER_MIME = "application/vnd.google-apps.folder"

# Casa os arquivos de GRAVACAO: o numero vem logo apos "MultiCorder" (ex.: MultiCorder6,
# MultiCorder#3, MultiCorder03). NAO casa o sidecar "MultiCorder - 2026...xml" (tem espaco
# e nenhum indice), que nao deve ser contado.
_MULTICORDER_RE = re.compile(r"^\s*multicorder#?0*([1-9])(?!\d)", re.IGNORECASE)

# Profundidade maxima de recursao a partir da pasta da data (evita varreduras infinitas).
_MAX_DEPTH = 4


class Drive:
    def __init__(self, credentials_file: str):
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # ---------- helpers de listagem ----------
    def _list_children(self, parent_id: str, only_folders: bool = False):
        query = f"'{parent_id}' in parents and trashed = false"
        if only_folders:
            query += f" and mimeType = '{_FOLDER_MIME}'"
        items, page_token = [], None
        while True:
            resp = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageSize=1000,
                    pageToken=page_token,
                    **_SHARED,
                )
                .execute()
            )
            items.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items

    def _find_child_folder_by_name(self, parent_id: str, name: str):
        for folder in self._list_children(parent_id, only_folders=True):
            if folder["name"] == name:
                return folder
        return None

    # ---------- logica de negocio ----------
    def today_folder_name(self, tz: str, date_format: str) -> str:
        return datetime.now(ZoneInfo(tz)).strftime(date_format)

    def get_today_folder(self, midias_folder_id: str, tz: str, date_format: str):
        name = self.today_folder_name(tz, date_format)
        return self._find_child_folder_by_name(midias_folder_id, name), name

    def multicorder_numbers_present(self, folder_id: str) -> set[int]:
        """Numeros MultiCorder entre os arquivos DIRETOS desta pasta (ignora subpastas)."""
        numbers = set()
        for f in self._list_children(folder_id):
            if f["mimeType"] == _FOLDER_MIME:
                continue
            m = _MULTICORDER_RE.match(f["name"])
            if m:
                numbers.add(int(m.group(1)))
        return numbers

    @staticmethod
    def is_complete(numbers: set[int], required_indices: set[int]) -> bool:
        """Completo = todos os indices exigidos estao presentes (ex.: {1,2,3,5,6})."""
        return required_indices.issubset(numbers)

    def walk_recording_folders(self, root_id: str):
        """Percorre a arvore a partir de root_id e, para CADA pasta encontrada,
        devolve um dict com id, nome, caminho relativo e os numeros MultiCorder
        presentes nos seus arquivos diretos. Assim funciona tanto para pastas de
        video diretas (VIDEO 01) quanto aninhadas (VIRAL / CONVIDADO-A)."""
        results = []

        def _recurse(folder_id: str, path: str, depth: int):
            children = self._list_children(folder_id)
            subfolders = [c for c in children if c["mimeType"] == _FOLDER_MIME]

            numbers = set()
            for f in children:
                if f["mimeType"] == _FOLDER_MIME:
                    continue
                m = _MULTICORDER_RE.match(f["name"])
                if m:
                    numbers.add(int(m.group(1)))

            results.append({
                "id": folder_id,
                "name": path.split(" / ")[-1],
                "path": path,
                "numbers": numbers,
            })

            if depth < _MAX_DEPTH:
                for sub in subfolders:
                    child_path = f"{path} / {sub['name']}" if path else sub["name"]
                    _recurse(sub["id"], child_path, depth + 1)

        # nao incluimos a propria pasta-raiz (data) nos resultados; comecamos pelos filhos
        for sub in self._list_children(root_id, only_folders=True):
            _recurse(sub["id"], sub["name"], 1)

        return results

    @staticmethod
    def folder_link(folder_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{folder_id}"
