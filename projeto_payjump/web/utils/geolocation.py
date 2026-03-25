import time

import pandas as pd
import requests
import streamlit as st

from .pdf_config import (
    DELAY_NOMINATIM,
    LOTE_IP_API,
    TIMEOUT_IP_API,
    TIMEOUT_NOMINATIM,
    URL_IP_API,
    URL_NOMINATIM,
    USER_AGENT_NOMINATIM,
)


def buscar_localizacao_ips(df_ips: pd.DataFrame, cache_ips: dict) -> pd.DataFrame:
    """Busca cidade, estado e país de cada IP via ip-api.com em lotes.
    Atualiza cache_ips in-place e retorna df_ips com colunas CIDADE/ESTADO/PAIS."""
    ips_unicos = df_ips['IP'].dropna().unique().tolist()
    ips_novos  = [ip for ip in ips_unicos if ip not in cache_ips]

    for i in range(0, len(ips_novos), LOTE_IP_API):
        lote = ips_novos[i:i + LOTE_IP_API]
        try:
            payload = [{'query': ip, 'fields': 'status,message,query,city,regionName,country,lat,lon'}
                       for ip in lote]
            resp = requests.post(URL_IP_API, json=payload, timeout=TIMEOUT_IP_API)
            resp.raise_for_status()  # levanta HTTPError para respostas 4xx/5xx
            for item in resp.json():
                falhou = item.get('status') == 'fail'
                cache_ips[item['query']] = {
                    'CIDADE':    item.get('city')       if not falhou else None,
                    'ESTADO':    item.get('regionName') if not falhou else None,
                    'PAIS':      item.get('country')    if not falhou else None,
                    'LATITUDE':  item.get('lat')        if not falhou else None,
                    'LONGITUDE': item.get('lon')        if not falhou else None,
                    '_motivo':   item.get('message'),   # ex: 'private range', 'reserved range'
                }
        except Exception as erro:
            st.warning(f'⚠️ Falha ao buscar geolocalização de {len(lote)} IP(s): {erro}')
            for ip in lote:
                cache_ips[ip] = {'CIDADE': None, 'ESTADO': None, 'PAIS': None,
                                 'LATITUDE': None, 'LONGITUDE': None, '_motivo': str(erro)}

    # Aviso quando IPs sem geolocalização são retornados pela API (ex: IPs privados/reservados)
    ips_sem_geo = [ip for ip in ips_unicos
                   if cache_ips.get(ip, {}).get('CIDADE') is None
                   and cache_ips.get(ip, {}).get('_motivo')]
    if ips_sem_geo:
        motivos = {cache_ips[ip].get('_motivo') for ip in ips_sem_geo}
        st.info(
            f'ℹ️ {len(ips_sem_geo)} IP(s) sem dados geográficos disponíveis '
            f'({", ".join(m for m in motivos if m)}).',
        )

    df_ips = df_ips.copy()
    df_ips['CIDADE']    = df_ips['IP'].map(lambda x: cache_ips.get(x, {}).get('CIDADE'))
    df_ips['ESTADO']    = df_ips['IP'].map(lambda x: cache_ips.get(x, {}).get('ESTADO'))
    df_ips['PAIS']      = df_ips['IP'].map(lambda x: cache_ips.get(x, {}).get('PAIS'))
    df_ips['LATITUDE']  = df_ips['IP'].map(lambda x: cache_ips.get(x, {}).get('LATITUDE'))
    df_ips['LONGITUDE'] = df_ips['IP'].map(lambda x: cache_ips.get(x, {}).get('LONGITUDE'))
    return df_ips


def buscar_geocodificacao_reversa(df_coordenadas: pd.DataFrame, cache_geo: dict) -> pd.DataFrame:
    """Busca cidade, estado e país de cada par (lat, lon) via Nominatim.
    Exibe barra de progresso enquanto processa, atualiza cache_geo in-place
    e retorna df enriquecido com colunas CIDADE/ESTADO/PAIS."""
    coords_unicas = df_coordenadas[['LATITUDE', 'LONGITUDE']].drop_duplicates()
    coords_novas  = coords_unicas[
        ~coords_unicas.apply(lambda r: (r['LATITUDE'], r['LONGITUDE']) in cache_geo, axis=1)
    ]

    if not coords_novas.empty:
        total_novas = len(coords_novas)
        barra_geo   = st.progress(0, text=f'Buscando localização... 0/{total_novas}')
        for idx, (_, row) in enumerate(coords_novas.iterrows()):
            lat, lon = row['LATITUDE'], row['LONGITUDE']
            try:
                resp = requests.get(
                    URL_NOMINATIM,
                    params={'format': 'json', 'lat': lat, 'lon': lon},
                    headers={'User-Agent': USER_AGENT_NOMINATIM},
                    timeout=TIMEOUT_NOMINATIM,
                )
                addr = resp.json().get('address', {})
                cache_geo[(lat, lon)] = {
                    'CIDADE': addr.get('city') or addr.get('town') or addr.get('village'),
                    'ESTADO': addr.get('state'),
                    'PAIS':   addr.get('country'),
                }
            except Exception:
                cache_geo[(lat, lon)] = {'CIDADE': None, 'ESTADO': None, 'PAIS': None}
            time.sleep(DELAY_NOMINATIM)
            barra_geo.progress(
                (idx + 1) / total_novas,
                text=f'Buscando localização... {idx + 1}/{total_novas}',
            )
        barra_geo.empty()

    df_coordenadas = df_coordenadas.copy()
    df_coordenadas['CIDADE'] = df_coordenadas.apply(
        lambda r: cache_geo.get((r['LATITUDE'], r['LONGITUDE']), {}).get('CIDADE'), axis=1
    )
    df_coordenadas['ESTADO'] = df_coordenadas.apply(
        lambda r: cache_geo.get((r['LATITUDE'], r['LONGITUDE']), {}).get('ESTADO'), axis=1
    )
    df_coordenadas['PAIS'] = df_coordenadas.apply(
        lambda r: cache_geo.get((r['LATITUDE'], r['LONGITUDE']), {}).get('PAIS'), axis=1
    )
    return df_coordenadas
