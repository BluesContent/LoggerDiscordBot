"""Diagnostico: para cada projeto cadastrado no Supabase, le a pasta MIDIAS e
mostra a estrutura + status Multicorder. NAO envia nada pro Discord. So leitura.

Uso:
  python diagnostico.py            -> usa a data de hoje
  python diagnostico.py 20260714   -> forca uma data especifica
"""
import sys

import config
import db
from drive import Drive

date_override = sys.argv[1] if len(sys.argv) > 1 else None

settings = db.get_settings()
timezone = settings.get("timezone", "America/Sao_Paulo")
date_format = settings.get("date_format", "%Y%m%d")

d = Drive(config.google_credentials())

for row in db.list_projects():
    name = row["name"]
    folder_id = str(row.get("midias_folder_id") or "")
    required = set(int(n) for n in (row.get("required_indices") or []))
    print("=" * 60)
    print(f"PROJETO: {name}")
    print(f"  índices exigidos: {sorted(required)}")

    if not folder_id:
        print("  (pasta ainda não configurada)")
        continue

    if date_override:
        date_name = date_override
        date_folder = d._find_child_folder_by_name(folder_id, date_name)
    else:
        date_folder, date_name = d.get_today_folder(folder_id, timezone, date_format)

    print(f"  data procurada: {date_name}")
    if not date_folder:
        print("  !! pasta da data NÃO encontrada.")
        continue

    rows = d.walk_recording_folders(date_folder["id"])
    if not rows:
        print("  (nenhuma subpasta encontrada)")
        continue

    for r in sorted(rows, key=lambda x: x["path"]):
        nums = ",".join(str(n) for n in sorted(r["numbers"])) or "-"
        complete = d.is_complete(r["numbers"], required)
        falta = sorted(required - r["numbers"])
        status = "COMPLETO ✅" if complete else f"faltando {falta}"
        notified = " (já avisado)" if db.is_notified(r["id"]) else ""
        print(f"    {r['path']:<28} tem=[{nums:<11}] -> {status}{notified}")

    completas = [r for r in rows if d.is_complete(r["numbers"], required) and not db.is_notified(r["id"])]
    print(f"  >> {len(completas)} pasta(s) disparariam mensagem agora:")
    for r in completas:
        print(f"       - {r['path']}")
