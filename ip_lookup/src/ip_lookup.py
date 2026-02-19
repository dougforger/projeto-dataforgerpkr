# salvar como ip_lookup.py
# prereqs: pip install requests pandas openpyxl
import requests
import pandas as pd
import time
import os
# import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
INPUT_FILE = DATA_DIR / "ips.txt"   # coloque sua lista aí (um IP por linha; pode incluir cabeçalho que será ignorado)
OUTPUT_CSV = OUTPUT_DIR / "ip_geoloc.csv"
OUTPUT_XLSX = OUTPUT_DIR / "ip_geoloc.xlsx"

# ip-api.com batch endpoint
BATCH_URL = "http://ip-api.com/batch?fields=status,message,query,country,regionName,city,zip,timezone,isp,org,as,lat,lon,proxy,hosting"

def load_ips(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    ips = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # ignora possíveis cabeçalhos (não são IPs)
        if any(c.isalpha() for c in s):
            # se a linha tiver letras e for "IPADDRESS" ignora
            continue
        ips.append(s)
    return ips

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def lookup_ips(ips):
    results = []
    for batch in chunks(ips, 100):  # ip-api aceita até 100 por batch
        try:
            resp = requests.post(BATCH_URL, json=batch, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            # tentativa simples de retry depois de 1s
            print(f"Erro na requisição: {e}. Vou esperar 1s e tentar IPs do batch individualmente...")
            time.sleep(1)
            # fallback: consultar individualmente (mais lento)
            data = []
            for ip in batch:
                try:
                    r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,query,country,regionName,city,zip,timezone,isp,org,as,lat,lon,proxy,hosting", timeout=10)
                    r.raise_for_status()
                    data.append(r.json())
                except Exception as e2:
                    print(f"  Falha no IP {ip}: {e2}")
                    data.append({"status":"fail","message":str(e2),"query":ip})
        for item in data:
            results.append(item)
        # respeitar limites simples
        time.sleep(0.5)
    return results

def normalize(results):
    rows = []
    for r in results:
        row = {
            "ip_consultado": r.get("query"),
            "status": r.get("status"),
            "mensagem": r.get("message"),
            "pais": r.get("country"),
            "estado": r.get("regionName"),
            "cidade": r.get("city"),
            "cep": r.get("zip"),
            "fuso_horario": r.get("timezone"),
            "provedor_internet": r.get("isp"),
            "organizacao": r.get("org"),
            "sistema_autonomo": r.get("as"),
            "latitude": r.get("lat"),
            "longitude": r.get("lon"),
            "proxy": r.get("proxy"),
            "hospedagem": r.get("hosting")
        }
        rows.append(row)
    return rows

def main():
    if not Path(INPUT_FILE).exists():
        print(f"Arquivo {INPUT_FILE} não encontrado. Crie-o com um IP por linha e rode novamente.")
        return
    ips = load_ips(INPUT_FILE)
    if not ips:
        print("Nenhum IP válido encontrado no arquivo.")
        return
    print(f"Vou consultar {len(ips)} IPs em batches. (ip-api.com, até 100 por batch)")
    results = lookup_ips(ips)
    rows = normalize(results)
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    df.to_excel(OUTPUT_XLSX, index=False)
    time.sleep(1)  # garantir que o arquivo foi escrito antes de abrir
    os.startfile(str(OUTPUT_XLSX))
    # subprocess.Popen(
    #     ['start', 'excel.exe', str(OUTPUT_XLSX)],
    #     shell=True
    # )
    print(f"Pronto — salvei {len(df)} linhas em:\n - {OUTPUT_CSV}\n - {OUTPUT_XLSX}")
    
if __name__ == "__main__":
    main()
