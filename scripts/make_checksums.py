#!/usr/bin/env python3
"""Calcula SHA-256 de todos los archivos en data-raw/ y los registra
con fecha en data-raw/CHECKSUMS.sha256. Idempotente: conserva la fecha
de primer registro de cada archivo y detecta si un archivo cambió (alerta)."""
import hashlib, os, sys
from datetime import date

RAW = os.path.join(os.path.dirname(__file__), "..", "data-raw")
OUT = os.path.join(RAW, "CHECKSUMS.sha256")

def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()

def load_existing():
    reg = {}
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            parts = line.strip().split("  ")
            if len(parts) == 3:
                reg[parts[2]] = (parts[0], parts[1])  # nombre -> (hash, fecha)
    return reg

def main():
    reg = load_existing()
    hoy = date.today().isoformat()
    alerta = False
    for name in sorted(os.listdir(RAW)):
        path = os.path.join(RAW, name)
        if not os.path.isfile(path) or name in ("CHECKSUMS.sha256", "README.md"):
            continue
        h = sha256(path)
        if name in reg:
            if reg[name][0] != h:
                print(f"[ALERTA] {name} CAMBIÓ desde su registro original. data-raw es inmutable.")
                alerta = True
        else:
            reg[name] = (h, hoy)
            print(f"[nuevo] {name} registrado ({hoy})")
    with open(OUT, "w", encoding="utf-8") as f:
        for name, (h, fecha) in sorted(reg.items()):
            f.write(f"{h}  {fecha}  {name}\n")
    print(f"\nRegistro escrito en {os.path.relpath(OUT)} ({len(reg)} archivos).")
    sys.exit(1 if alerta else 0)

if __name__ == "__main__":
    main()
