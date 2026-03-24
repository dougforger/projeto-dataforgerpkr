"""Utilitários de mapa interativo (Folium) para uso nas páginas Streamlit.

Centraliza a renderização de mapas Folium para reutilização entre as páginas
de Análise e de Relatórios.
"""
import folium
import streamlit as st
from streamlit_folium import st_folium

from .analise_geo import mapa_cores_hex_por_id


def exibir_mapa_folium(df, key: str) -> None:
    """Exibe mapa Folium interativo com marcadores coloridos por JOGADOR_ID e layer control.

    Espera colunas: LATITUDE, LONGITUDE.
    Opcionais: JOGADOR_ID, JOGADOR, CIDADE, ESTADO, PAIS.
    """
    colunas_mapa = ['LATITUDE', 'LONGITUDE'] + [
        c for c in ('JOGADOR', 'JOGADOR_ID', 'CIDADE', 'ESTADO', 'PAIS') if c in df.columns
    ]
    df_mapa = df[colunas_mapa].dropna(subset=['LATITUDE', 'LONGITUDE'])

    if df_mapa.empty:
        st.info('Sem coordenadas para exibir no mapa.')
        return

    lat_c = float(df_mapa['LATITUDE'].mean())
    lon_c = float(df_mapa['LONGITUDE'].mean())

    ids       = df_mapa['JOGADOR_ID'].dropna().unique().tolist() if 'JOGADOR_ID' in df_mapa.columns else []
    cores_hex = mapa_cores_hex_por_id(ids) if ids else {}

    m = folium.Map(location=[lat_c, lon_c], zoom_start=4, tiles=None)

    folium.TileLayer('OpenStreetMap', name='🗺️ Ruas').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Source: Esri, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP',
        name='🛰️ Satélite',
        show=False,
    ).add_to(m)

    for _, row in df_mapa.iterrows():
        id_  = row.get('JOGADOR_ID')
        cor  = cores_hex.get(id_, '#E31A1C') if ids else '#E31A1C'
        nome = row.get('JOGADOR', f'{row["LATITUDE"]:.4f}, {row["LONGITUDE"]:.4f}')
        popup_html = (
            f'<b>{nome}</b><br>'
            f'{row.get("CIDADE", "")} — {row.get("ESTADO", "")} — {row.get("PAIS", "")}'
        )
        folium.CircleMarker(
            location=[float(row['LATITUDE']), float(row['LONGITUDE'])],
            radius=8,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=nome,
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width='stretch', height=450, key=key, returned_objects=[])
    _exibir_legenda(df_mapa)


def _exibir_legenda(df_mapa) -> None:
    """Renderiza legenda de cores abaixo do mapa."""
    if 'JOGADOR_ID' not in df_mapa.columns:
        return
    ids = df_mapa['JOGADOR_ID'].dropna().unique().tolist()
    if not ids:
        return
    cores_hex = mapa_cores_hex_por_id(ids)
    st.caption('**Legenda**')
    cols = st.columns(min(len(ids), 5))
    for i, id_ in enumerate(sorted(ids)):
        nome = (
            df_mapa[df_mapa['JOGADOR_ID'] == id_]['JOGADOR'].iloc[0]
            if 'JOGADOR' in df_mapa.columns
            else str(id_)
        )
        hex_cor = cores_hex[id_]
        cols[i % 5].markdown(
            f'<span style="color:{hex_cor};font-size:1.3em">■</span> **{nome}**<br>'
            f'<small>ID: {id_}</small>',
            unsafe_allow_html=True,
        )
