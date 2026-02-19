# salvar como reverse_geocode.py
# prereqs: pip install requests pandas openpyxl
import pandas as pd
import requests
import time
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
INPUT_FILE = DATA_DIR / "coords.csv"   # arquivo com colunas lat,lon
OUTPUT_CSV = OUTPUT_DIR / "reverse_geocode.csv"
OUTPUT_XLSX = OUTPUT_DIR / "reverse_geocode.xlsx"

# INPUT_FILE = "ip_lookup/coords.csv"   # arquivo com colunas lat,lon
# OUTPUT_CSV = "ip_lookup/reverse_geocode.csv"
# OUTPUT_XLSX = "ip_lookup/reverse_geocode.xlsx"

def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 15,
        "addressdetails": 1
    }
    headers = {"User-Agent": "GeoLookupScript/1.0 (contact: exemplo@dominio.com)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        addr = data.get("address", {})
        return {
            "lat": lat,
            "lon": lon,
            "country": addr.get("country"),
            "state": addr.get("state"),
            "city": addr.get("city") or addr.get("town") or addr.get("village"),
            "suburb": addr.get("suburb"),
            "postcode": addr.get("postcode"),
            "display_name": data.get("display_name"),
        }
    except Exception as e:
        return {
            "lat": lat,
            "lon": lon,
            "error": str(e)
        }

def main():
    df = pd.read_csv(INPUT_FILE)
    if not {"lat", "lon"}.issubset(df.columns):
        raise ValueError("O arquivo precisa conter as colunas 'lat' e 'lon'")
    
    results = []
    for _, row in df.iterrows():
        lat, lon = row["lat"], row["lon"]
        print(f"Consultando {lat}, {lon}...")
        results.append(reverse_geocode(lat, lon))
        time.sleep(1)  # respeitar limite de uso público
    
    df_out = pd.DataFrame(results)

    # remove versões antigas se existirem (evita conflito de permissão, planilha aberta etc.)
    for f in [OUTPUT_CSV, OUTPUT_XLSX]:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"Arquivo antigo removido: {f}")
            except PermissionError:
                print(f"⚠️ Não consegui apagar {f}. Verifique se o arquivo está aberto e feche antes de rodar novamente.")
    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    df_out.to_excel(OUTPUT_XLSX, index=False)
    os.startfile(OUTPUT_XLSX)
    print(f"Pronto! Resultados salvos em:\n - {OUTPUT_CSV}\n - {OUTPUT_XLSX}")

if __name__ == "__main__":
    main()
