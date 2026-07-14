"""Envio de mensagens e consultas ao Discord via API REST (usando o token do bot).
Sem gateway/conexao persistente -> simples e compativel com serverless (Vercel)."""
from __future__ import annotations

import requests

API = "https://discord.com/api/v10"


class DiscordError(Exception):
    pass


class Discord:
    def __init__(self, token: str):
        self.token = (token or "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        })

    def _get(self, path: str):
        r = self.session.get(f"{API}{path}", timeout=15)
        if r.status_code == 401:
            raise DiscordError("Token do Discord invalido ou nao configurado.")
        if not r.ok:
            raise DiscordError(f"Discord GET {path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    # ---------- consultas para o painel ----------
    def list_guilds(self):
        return [{"id": g["id"], "name": g["name"]} for g in self._get("/users/@me/guilds")]

    def list_text_channels(self, guild_id: str):
        chans = self._get(f"/guilds/{guild_id}/channels")
        # type 0 = texto, 5 = anuncios, 15 = forum
        out = [c for c in chans if c.get("type") in (0, 5, 15)]
        out.sort(key=lambda c: (c.get("position", 0), c.get("name", "")))
        return [{"id": c["id"], "name": c["name"]} for c in out]

    def list_roles(self, guild_id: str):
        roles = self._get(f"/guilds/{guild_id}/roles")
        roles = [r for r in roles if r["name"] != "@everyone"]
        roles.sort(key=lambda r: r.get("position", 0), reverse=True)
        return [{"id": r["id"], "name": r["name"]} for r in roles]

    def guild_of_channel(self, channel_id: int | str):
        c = self._get(f"/channels/{channel_id}")
        return c.get("guild_id")

    # ---------- envio ----------
    def send_message(self, channel_id: int | str, content: str) -> dict:
        payload = {
            "content": content,
            "allowed_mentions": {"parse": ["roles", "users", "everyone"]},
        }
        r = self.session.post(f"{API}/channels/{channel_id}/messages", json=payload, timeout=15)
        if not r.ok:
            raise DiscordError(f"Falha ao enviar (canal {channel_id}) -> {r.status_code}: {r.text[:200]}")
        return r.json()
