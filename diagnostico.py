"""Diagnostico: para cada projeto do projects.json, le a pasta MIDIAS e mostra a
estrutura + status Multicorder. NAO envia nada pro Discord. So leitura.

Uso:
  python diagnostico.py            -> usa a data de hoje
  python diagnostico.py 20260714   -> forca uma data especifica
"""
import json
import sys
from pathlib import Path

from drive import Drive

BASE = Path(__file__).resolve().parent
CREDS = str(BASE / "credentials/service_account.json")

date_override = sys.argv[1] if len(sys.argv) > 1 else None

projects = json.loads((BASE / "projects.json").read_text(encoding="utf-8"))["projects"]
d = Drive(CREDS)

for proj in projects:
    name = proj["name"]
    folder_id = str(proj["midias_folder_id"])
    required = set(int(n) for n in proj["required_indices"])
    print("=" * 60)
    print(f"PROJETO: {name}")
    print(f"  indices exigidos: {sorted(required)}")

    if folder_id.startswith("cole_") or not folder_id:
        print("  (pasta ainda nao configurada)")
        continue

    if date_override:
        date_name = date_override
        date_folder = d._find_child_folder_by_name(folder_id, date_name)
    else:
        date_folder, date_name = d.get_today_folder(folder_id, "America/Sao_Paulo", "%Y%m%d")

    print(f"  data procurada: {date_name}")
    if not date_folder:
        print("  !! pasta da data NAO encontrada.")
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
        print(f"    {r['path']:<28} tem=[{nums:<11}] -> {status}")

    completas = [r for r in rows if d.is_complete(r["numbers"], required)]
    print(f"  >> {len(completas)} pasta(s) disparariam mensagem:")
    for r in completas:
        print(f"       - {r['path']}")
