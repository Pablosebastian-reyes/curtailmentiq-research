#!/usr/bin/env python3
"""Figuras descriptivas del data paper (Data in Brief) — dataset v1.0.

Genera en figures/ (PDF vectorial + PNG 300 dpi):
  fig1_plants_map      mapa de Chile: 300 centrales, color/forma por tecnologia,
                       tamano ∝ curtailment acumulado 2022-2026.
  fig2_temporal_coverage  cobertura mensual de las tablas diaria y horaria por
                       tecnologia (ene-2022 a may-2026).

Lee exclusivamente release/v1.0/*.parquet (el release congelado) y
scripts/chile_boundary.geojson (Natural Earth 1:50m, dominio publico).
Paleta categorica validada (CVD ΔE adyacente >= 21.6; ver dataviz validator);
el relieve para los tonos de bajo contraste es la forma del marcador y las
etiquetas de fila/leyenda (la identidad nunca depende solo del color).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as MplPolygon

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / "release" / "v1.0"
FIGURES = REPO / "figures"
FIGURES.mkdir(exist_ok=True)

# --- estilo comun (sobrio, misma fuente, sin titulos dentro de la figura) ---
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.labelcolor": "#52514e",
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "xtick.color": "#898781",
    "ytick.color": "#898781",
    "axes.edgecolor": "#c3c2b7",
    "axes.linewidth": 0.6,
    "savefig.facecolor": "white",
    "pdf.fonttype": 42,  # fuentes embebidas como TrueType (requisito editorial)
})

# tecnologia (valores del dataset) -> etiqueta EN, color validado, marcador
TECNOLOGIAS = {
    "Solar":         ("Solar",              "#eda100", "o"),
    "Eólica":        ("Wind",               "#2a78d6", "^"),
    "Hidro Pasada":  ("Run-of-river hydro", "#1baf7a", "s"),
    "Hidro Embalse": ("Reservoir hydro",    "#4a3aa7", "D"),
}
GRIS_TENUE = "#f0efec"
TINTA_2 = "#52514e"
TINTA_MUTED = "#898781"


# ============================================================ FIGURA 1: MAPA
def figura_1():
    meta = pd.read_parquet(RELEASE / "plants_metadata.parquet",
                           columns=["central_codigo", "latitud", "longitud"])
    plants = pd.read_parquet(RELEASE / "plants.parquet")
    daily = pd.read_parquet(RELEASE / "curtailment_daily.parquet",
                            columns=["central_codigo", "mwh"])
    acum = daily.groupby("central_codigo")["mwh"].sum().rename("mwh_total")
    df = plants.merge(meta, on="central_codigo").join(acum, on="central_codigo")
    df["mwh_total"] = df["mwh_total"].fillna(0.0)
    assert len(df) == 300 and df["latitud"].notna().all()

    fig, ax = plt.subplots(figsize=(4.9, 7.3))

    # contorno continental de Chile (se descartan slivers diminutos del
    # dataset Natural Earth que no son costa real)
    borde = json.load(open(REPO / "scripts" / "chile_boundary.geojson"))
    for poly in borde["features"][0]["geometry"]["coordinates"]:
        anillo = poly[0]
        xs, ys = [p[0] for p in anillo], [p[1] for p in anillo]
        if len(anillo) < 8 and (max(xs) - min(xs)) + (max(ys) - min(ys)) < 0.25:
            continue
        ax.add_patch(MplPolygon(anillo, closed=True, facecolor=GRIS_TENUE,
                                edgecolor="#c3c2b7", linewidth=0.5, zorder=1))

    # area del marcador ∝ curtailment acumulado; piso minimo para que las 300
    # centrales (incluidas las de 0 MWh) sean visibles
    S_MIN, S_MAX = 5.0, 260.0
    vmax = df["mwh_total"].max()
    escala = (S_MAX - S_MIN) / vmax
    df["s"] = S_MIN + df["mwh_total"] * escala

    # dibujar por tecnologia, burbujas grandes debajo
    for tec, (etq, color, marca) in TECNOLOGIAS.items():
        sub = df[df["tecnologia"] == tec].sort_values("s", ascending=False)
        ax.scatter(sub["longitud"], sub["latitud"], s=sub["s"], marker=marca,
                   facecolor=color, edgecolor="white", linewidth=0.35,
                   alpha=0.78, zorder=3)

    ax.set_xlim(-76.3, -66.6)
    ax.set_ylim(-43.6, -17.2)
    ax.set_aspect(1.0 / np.cos(np.radians(30)))
    ax.set_xticks(range(-76, -66, 4))
    ax.set_xticklabels([f"{abs(x)}°W" for x in range(-76, -66, 4)])
    ax.set_yticks(range(-40, -16, 5))
    ax.set_yticklabels([f"{abs(y)}°S" for y in range(-40, -16, 5)])
    ax.tick_params(length=2.5, width=0.5)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)

    # leyenda 1: tecnologia (identidad = color + forma, tamano fijo)
    leg_tec = [Line2D([], [], linestyle="", marker=m, markersize=6.5,
                      markerfacecolor=c, markeredgecolor="white",
                      markeredgewidth=0.35, label=e)
               for e, c, m in TECNOLOGIAS.values()]
    l1 = ax.legend(handles=leg_tec, title="Technology",
                   loc="upper left", bbox_to_anchor=(1.02, 1.0),
                   frameon=False, fontsize=7.5, title_fontsize=8,
                   alignment="left", handletextpad=0.35, labelspacing=0.55)
    l1.get_title().set_color(TINTA_2)
    for t in l1.get_texts():
        t.set_color(TINTA_2)
    ax.add_artist(l1)

    # leyenda 2: escala de tamano (GWh acumulados)
    refs_gwh = [10, 100, 400]
    leg_tam = [Line2D([], [], linestyle="", marker="o",
                      markersize=np.sqrt(S_MIN + g * 1000 * escala),
                      markerfacecolor="none", markeredgecolor=TINTA_MUTED,
                      markeredgewidth=0.7, label=f"{g:,}")
               for g in refs_gwh]
    l2 = ax.legend(handles=leg_tam, title="Cumulative curtailment\n2022–2026 (GWh)",
                   loc="upper left", bbox_to_anchor=(1.02, 0.72),
                   frameon=False, fontsize=7.5, title_fontsize=8,
                   alignment="left", labelspacing=1.15, handletextpad=0.6,
                   borderaxespad=0.0)
    l2.get_title().set_color(TINTA_2)
    for t in l2.get_texts():
        t.set_color(TINTA_2)

    fig.savefig(FIGURES / "fig1_plants_map.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "fig1_plants_map.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig1_plants_map: OK")


# ================================================ FIGURA 2: COBERTURA TEMPORAL
def figura_2():
    meses = pd.period_range("2022-01", "2026-05", freq="M")
    idx = {m: i for i, m in enumerate(meses)}

    def presencia(archivo):
        df = pd.read_parquet(RELEASE / archivo, columns=["fecha", "tecnologia"])
        df["mes"] = pd.PeriodIndex(pd.to_datetime(df["fecha"]), freq="M")
        pres = df.groupby(["tecnologia", "mes"]).size()
        return {(tec, m) for (tec, m) in pres.index}

    pres_d = presencia("curtailment_daily.parquet")
    pres_h = presencia("curtailment_hourly.parquet")

    filas = []  # (etiqueta, color, set de meses presentes)
    for tabla, pres in (("Daily", pres_d), ("Hourly", pres_h)):
        for tec, (etq, color, _m) in TECNOLOGIAS.items():
            filas.append((tabla, etq, color,
                          sorted(idx[m] for t, m in pres if t == tec)))

    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    n = len(filas)
    ALTO = 0.58
    for y, (tabla, etq, color, cols) in enumerate(filas):
        yy = n - 1 - y
        # pista tenue = extension total posible; encima, tramos con datos
        ax.broken_barh([(0, len(meses))], (yy - ALTO / 2, ALTO),
                       facecolor=GRIS_TENUE, edgecolor="none", zorder=1)
        if cols:
            # agrupar meses consecutivos en tramos
            tramos, ini, prev = [], cols[0], cols[0]
            for c in cols[1:]:
                if c != prev + 1:
                    tramos.append((ini, prev - ini + 1))
                    ini = c
                prev = c
            tramos.append((ini, prev - ini + 1))
            ax.broken_barh(tramos, (yy - ALTO / 2, ALTO),
                           facecolor=color, edgecolor="none", zorder=2)
            # fecha de inicio dentro de la pista vacia, cuando no parte en ene-2022
            if cols[0] > 0:
                ax.text(cols[0] - 0.7, yy, meses[cols[0]].strftime("%b %Y"),
                        fontsize=6.5, color=TINTA_MUTED, ha="right", va="center",
                        zorder=3)

    # separador y titulos de grupo (Daily / Hourly)
    ax.axhline(3.5, color="#c3c2b7", linewidth=0.6, zorder=3)
    etiquetas = [f[1] for f in filas]
    ax.set_yticks(range(n))
    ax.set_yticklabels(etiquetas[::-1], fontsize=7.5, color=TINTA_2)
    for lado, frac in (("Daily table", 0.70), ("Hourly table", 0.24)):
        ax.text(-0.315, frac, lado, transform=ax.transAxes, rotation=90,
                ha="center", va="center", fontsize=8, color=TINTA_2)

    # eje X: marca en enero de cada anio + hairlines de anio
    enero = [idx[m] for m in meses if m.month == 1]
    for x in enero:
        ax.axvline(x, color="#e1e0d9", linewidth=0.5, zorder=0)
    ax.set_xticks([x + 0.5 for x in enero])
    ax.set_xticklabels([str(meses[x].year) for x in enero])
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(-0.5, len(meses) + 0.5)
    ax.set_ylim(-0.6, n - 0.4 + 0.5)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")

    fig.subplots_adjust(left=0.33)
    fig.savefig(FIGURES / "fig2_temporal_coverage.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "fig2_temporal_coverage.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig2_temporal_coverage: OK")


if __name__ == "__main__":
    figura_1()
    figura_2()
