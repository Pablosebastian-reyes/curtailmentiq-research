#!/usr/bin/env python3
"""Figuras finales del manuscrito SEGAN (flagship) — calidad de publicacion.

Genera en flagship/segan/figuras/ (PDF vectorial para LaTeX + PNG 300 dpi):

  fig1_plants_map       columna simple. Mapa de Chile continental con las 300
                        centrales del release v1.0; color y forma por tecnologia,
                        area del marcador proporcional al curtailment acumulado
                        2022-2026.
  fig2_distribution     columna simple, dos paneles. Arriba: fraccion de dias
                        sin curtailment (ceros) por tecnologia. Abajo: histograma
                        en escala log de las magnitudes positivas, con P50/P90/P99.
                        Justifica visualmente el modelo hurdle.
  fig3_rolling_coverage ancho doble. Cobertura rodante 90d en el tiempo (datos
                        reales, corrida CON embargo de 7 dias) para static split,
                        ventana 60d, ACI y transporte+ACI; banda de la ventana de
                        maxima divergencia respecto de la calibracion.
  fig4_coverage_width   ancho doble, dos paneles. Trade-off cobertura (con se
                        clusterizado por fecha) vs ancho medio, por metodo y
                        periodo.
  fig5_regime_changepoints  ancho doble, dos paneles. Media mensual de
                        log(Y|Y>0) para solar de Antofagasta y Atacama, cruda y
                        desestacionalizada, con los puntos de cambio detectados
                        (may-2023, ene-2024) y las ventanas de evaluacion
                        sombreadas. Sostiene la Seccion 3.3: el desplazamiento es
                        una rampa de ~18 meses, sin quiebre en oct-2024 ni en 2025.

Fuentes de datos (ver flagship/segan/REPORTE_FIGURAS.md):
  fig1, fig2  release/v1.0/*.parquet  (dataset congelado, corte 2026-05-31)
  fig3        recomputa las series conformal desde predicciones/pred_hurdle.csv
              reutilizando conformal_v3_real.py y conformal_metodos.py, con el
              MISMO orden de consumo del RNG que la corrida oficial (asi la
              figura corresponde exactamente a la tabla), y se autochequea contra
              conformal_v3_tabla.csv.
  fig4        flagship/conformal_v3_tabla.csv  (corrida oficial con embargo)

Estilo comun (definido una sola vez en STYLE + helpers): serif 8-9 pt para
combinar con el cuerpo del paper, textos en INGLES, sin titulo dentro de la
figura, sin spines superior/derecho, sin grillas pesadas. Paleta categorica
sobria validada con el validador de la skill dataviz (all-pairs: peor CVD dE 9.1,
peor vision-normal dE 16.3; ambos sobre el piso). La identidad NUNCA depende solo
del color: cada tecnologia lleva ademas marcador propio y cada metodo lleva
ademas estilo de linea / hatch propio.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as MplPolygon, Patch

REPO = Path(__file__).resolve().parent.parent
FLAGSHIP = REPO / "flagship"
RELEASE = REPO / "release" / "v1.0"
OUT = FLAGSHIP / "segan" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(FLAGSHIP))

# --------------------------------------------------------------- estilo comun
COL_SIMPLE = 3.5   # ancho de columna simple (pulgadas)
COL_DOBLE = 7.2    # ancho de columna doble (pulgadas)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",   # math tipo Times para los simbolos gamma
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.labelcolor": "#52514e",
    "axes.titlesize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "xtick.color": "#898781",
    "ytick.color": "#898781",
    "axes.edgecolor": "#c3c2b7",
    "axes.linewidth": 0.6,
    "lines.linewidth": 1.4,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "pdf.fonttype": 42,   # fuentes embebidas como TrueType (requisito editorial)
    "ps.fonttype": 42,
})

TINTA_1 = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUTED = "#898781"
GRIS_TENUE = "#f0efec"
HAIRLINE = "#e1e0d9"

# tecnologia (valor del dataset) -> (etiqueta EN, color validado, marcador)
TECNOLOGIAS = {
    "Solar":         ("Solar",              "#eda100", "o"),
    "Eólica":        ("Wind",               "#2a78d6", "^"),
    "Hidro Pasada":  ("Run-of-river hydro", "#1baf7a", "s"),
    "Hidro Embalse": ("Reservoir hydro",    "#4a3aa7", "D"),
}

# metodo (columna de conformal_v3_tabla.csv) -> (etiqueta EN, color, ls, marker, hatch)
METODOS = {
    "1_estatico_pit":         ("Static split",              "#52514e", "-",  "o", ""),
    "2_ventana60d_pit":       ("Sliding window 60d",        "#2a78d6", "--", "s", "////"),
    "3_aci_pit_g05":          (r"ACI ($\gamma=0.05$)",       "#eb6834", "-.", "^", "...."),
    "4_transporte_banda_g05": (r"Transport + ACI ($\gamma=0.05$)", "#4a3aa7", "-", "D", "xxxx"),
}
# periodos en orden, con etiqueta legible para el eje
PERIODOS_ETQ = {
    "test_pre":  "Pre-transition\n(Sep '24)",
    "test_ramp": "Transition\n(Oct–Dec '24)",
    "2025-S1":   "2025-H1",
    "2025-S2":   "2025-H2",
    "2026-S1":   "2026-H1",
}
# Ventana de maxima divergencia respecto de la distribucion de calibracion
# (W1 = 1.25 contra 0.28-0.76 de las demas). Las fronteras NO cambian: son las
# mismas de conformal_metodos.PERIODOS; solo cambia como se rotulan.
TRANS_INI = pd.Timestamp("2024-10-01")
TRANS_FIN = pd.Timestamp("2025-01-01")
# ventana de calibracion, para sombrearla en la figura 5
CAL_INI = pd.Timestamp("2024-01-01")
CAL_FIN = pd.Timestamp("2024-09-01")


def _despejar(ax, izq=True):
    """Quita spines superior/derecho; deja ejes hairline sobrios."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    if not izq:
        ax.spines["left"].set_visible(False)
    ax.tick_params(length=2.5, width=0.5)


def _guardar(fig, nombre):
    fig.savefig(OUT / f"{nombre}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{nombre}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  {nombre}: OK")


# ==================================================== FIGURA 1: MAPA (col simple)
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

    fig, ax = plt.subplots(figsize=(COL_SIMPLE, 6.4))

    # contorno continental de Chile (Natural Earth 1:50m, dominio publico); se
    # descartan slivers diminutos que no son costa real
    borde = json.load(open(REPO / "scripts" / "chile_boundary.geojson"))
    for poly in borde["features"][0]["geometry"]["coordinates"]:
        anillo = poly[0]
        xs, ys = [p[0] for p in anillo], [p[1] for p in anillo]
        if len(anillo) < 8 and (max(xs) - min(xs)) + (max(ys) - min(ys)) < 0.25:
            continue
        ax.add_patch(MplPolygon(anillo, closed=True, facecolor=GRIS_TENUE,
                                edgecolor="#c3c2b7", linewidth=0.5, zorder=1))

    # area del marcador proporcional al curtailment acumulado; piso minimo para
    # que las 300 centrales (incluidas las de 0 MWh) sean visibles
    S_MIN, S_MAX = 5.0, 240.0
    vmax = df["mwh_total"].max()
    escala = (S_MAX - S_MIN) / vmax
    df["s"] = S_MIN + df["mwh_total"] * escala

    for tec, (etq, color, marca) in TECNOLOGIAS.items():
        sub = df[df["tecnologia"] == tec].sort_values("s", ascending=False)
        ax.scatter(sub["longitud"], sub["latitud"], s=sub["s"], marker=marca,
                   facecolor=color, edgecolor="white", linewidth=0.3,
                   alpha=0.80, zorder=3)

    ax.set_xlim(-76.3, -66.6)
    ax.set_ylim(-43.8, -17.2)
    ax.set_aspect(1.0 / np.cos(np.radians(30)))
    ax.set_xticks(range(-76, -66, 4))
    ax.set_xticklabels([f"{abs(x)}°W" for x in range(-76, -66, 4)])
    ax.set_yticks(range(-40, -16, 5))
    ax.set_yticklabels([f"{abs(y)}°S" for y in range(-40, -16, 5)])
    _despejar(ax)

    # Leyendas en el Pacifico (oeste), area vacia de datos: para un mapa de
    # columna simple, N-S muy alargado, ubicar las leyendas en el oceano evita
    # encoger el mapa y no solapa ninguna central (todas caen en la franja este).
    leg_tec = [Line2D([], [], linestyle="", marker=m, markersize=6.0,
                      markerfacecolor=c, markeredgecolor="white",
                      markeredgewidth=0.3, label=e)
               for e, c, m in TECNOLOGIAS.values()]
    l1 = ax.legend(handles=leg_tec, title="Technology",
                   loc="upper left", bbox_to_anchor=(0.015, 0.985),
                   frameon=False, title_fontsize=8, alignment="left",
                   handletextpad=0.35, labelspacing=0.5)
    l1.get_title().set_color(TINTA_2)
    for t in l1.get_texts():
        t.set_color(TINTA_2)
    ax.add_artist(l1)

    # referencias visibles a tamano real: la mas chica (10 GWh) daba un marcador
    # de ~2.9 pt, invisible en el PDF compilado, y su etiqueta "10" quedaba
    # flotando dentro del mapa. Se usan referencias cuyo circulo se ve con
    # claridad (>= 6 pt) y que cubren el rango hasta el maximo (~745 GWh).
    refs_gwh = [100, 400, 700]
    leg_tam = [Line2D([], [], linestyle="", marker="o",
                      markersize=np.sqrt(S_MIN + g * 1000 * escala),
                      markerfacecolor="none", markeredgecolor=TINTA_MUTED,
                      markeredgewidth=0.7, label=f"{g:,}")
               for g in refs_gwh]
    l2 = ax.legend(handles=leg_tam, title="Cumulative curtailment\n2022–2026 (GWh)",
                   loc="upper left", bbox_to_anchor=(0.015, 0.60),
                   frameon=False, title_fontsize=8, alignment="left",
                   labelspacing=2.2, handletextpad=0.9, borderaxespad=0.0)
    l2.get_title().set_color(TINTA_2)
    for t in l2.get_texts():
        t.set_color(TINTA_2)

    _guardar(fig, "fig1_plants_map")


# ============================================ FIGURA 2: DISTRIBUCION (col simple)
def figura_2():
    daily = pd.read_parquet(RELEASE / "curtailment_daily.parquet",
                            columns=["tecnologia", "mwh"])

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(COL_SIMPLE, 4.7),
        gridspec_kw={"height_ratios": [1.0, 1.25], "hspace": 0.55})

    # --- panel superior: fraccion de dias en cero por tecnologia ---
    fr = (daily.assign(cero=daily["mwh"].eq(0))
          .groupby("tecnologia")["cero"].mean())
    orden = list(TECNOLOGIAS.keys())
    x = np.arange(len(orden))
    for i, tec in enumerate(orden):
        etq, color, _m = TECNOLOGIAS[tec]
        v = float(fr[tec])
        ax_top.bar(i, v, width=0.68, color=color, edgecolor="white",
                   linewidth=0.6, zorder=2)
        ax_top.text(i, v + 0.025, f"{v:.2f}", ha="center", va="bottom",
                    fontsize=7.5, color=TINTA_1)
    ax_top.set_xticks(x)
    ax_top.set_xticklabels([TECNOLOGIAS[t][0].replace(" ", "\n", 1) for t in orden],
                           fontsize=7)
    ax_top.set_ylim(0, 1.0)
    ax_top.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_top.set_ylabel("Fraction of\nzero-curtailment days")
    ax_top.axhline(0, color="#c3c2b7", linewidth=0.6)
    _despejar(ax_top)
    ax_top.tick_params(axis="x", length=0)

    # --- panel inferior: magnitudes positivas en escala log, con percentiles ---
    pos = daily.loc[daily["mwh"] > 0, "mwh"].to_numpy()
    lg = np.log10(pos)
    ax_bot.hist(lg, bins=48, color="#86b6ef", edgecolor="white", linewidth=0.25,
                zorder=2)
    p50, p90, p99 = np.percentile(pos, [50, 90, 99])
    ymax = ax_bot.get_ylim()[1]
    # etiquetas horizontales en la parte superior, escalonadas en altura para que
    # P90 y P99 (a media decada de distancia) no se solapen; cada una se apoya
    # sobre su linea guia con un recuadro blanco que la mantiene legible
    alturas = {"P50": 0.955, "P90": 0.83, "P99": 0.705}
    for p, etq in [(p50, "P50"), (p90, "P90"), (p99, "P99")]:
        xp = np.log10(p)
        ax_bot.axvline(xp, color=TINTA_2, linewidth=0.9, linestyle=(0, (4, 2)),
                       zorder=3)
        ax_bot.text(xp, alturas[etq] * ymax, f"{etq} = {p:,.0f} MWh",
                    ha="center", va="center", fontsize=6.8, color=TINTA_2, zorder=4,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                              edgecolor=HAIRLINE, linewidth=0.4, alpha=0.95))
    ax_bot.set_xlabel("Positive daily curtailment (MWh, log scale)")
    ax_bot.set_ylabel("Plant-days")
    ticks = [-1, 0, 1, 2, 3, 4]
    ax_bot.set_xticks(ticks)
    ax_bot.set_xticklabels(["0.1", "1", "10", "100", "1,000", "10,000"])
    ax_bot.set_xlim(min(lg.min(), -1.05), lg.max() + 0.1)
    ax_bot.axhline(0, color="#c3c2b7", linewidth=0.6)
    _despejar(ax_bot)

    _guardar(fig, "fig2_distribution")


# ----- recomputo de las series conformal (mismo orden de RNG que la corrida oficial)
def _series_conformal():
    """Devuelve (fecha, y, {metodo: U}) recomputando las 4 series con embargo,
    reutilizando conformal_v3_real.py. Reproduce el orden EXACTO de consumo del
    RNG de main() (pit_score -> transporte g02 -> transporte g05) para que las
    series correspondan a la misma corrida que conformal_v3_tabla.csv."""
    import conformal_metodos as cm
    import conformal_v3_real as v3

    h = v3.cargar()
    sigma = float(h.sigma.iloc[0])
    h["s"] = cm.pit_score(h.p.values, h.mu.values, sigma, h.y_real.values, v3.RNG)

    es_cal = (h.fecha >= v3.CAL_INI) & (h.fecha < v3.CAL_FIN)
    cal = h[es_cal]
    test = h[h.fecha >= v3.CAL_FIN].reset_index(drop=True)
    s_cal = cal.s.values
    fechas_test = np.sort(test.fecha.unique())
    p_t, mu_t, y_t, f_t = test.p.values, test.mu.values, test.y_real.values, test.fecha.values

    # 1. estatico
    qhat = cm.q_conformal(s_cal, v3.ALPHA)
    U_est = cm.pit_upper(p_t, mu_t, sigma, qhat)

    # 2. ventana deslizante 60d, refresco 7d, con embargo (identico a main)
    U_vent = np.full(len(test), np.nan)
    refrescos = pd.date_range("2024-09-01", "2026-05-31", freq="7D")
    fechas_h = h.fecha.values
    for t0 in refrescos:
        ini = np.datetime64((t0 - pd.Timedelta(days=60 + v3.EMBARGO_DIAS)).date())
        fin = np.datetime64((t0 - pd.Timedelta(days=v3.EMBARGO_DIAS)).date())
        win = (fechas_h >= ini) & (fechas_h < fin)
        obj = (f_t >= np.datetime64(t0.date())) & (f_t < np.datetime64((t0 + pd.Timedelta(days=7)).date()))
        if obj.sum() == 0 or win.sum() < 100:
            continue
        q_w = cm.q_conformal(h.s.values[win], v3.ALPHA)
        U_vent[obj] = cm.pit_upper(p_t[obj], mu_t[obj], sigma, q_w)

    # 3. ACI (g02 y luego g05; no consumen RNG)
    v3.correr_aci(np.sort(s_cal), test, p_t, mu_t, y_t, f_t, fechas_test, sigma, 0.02)
    U_aci = v3.correr_aci(np.sort(s_cal), test, p_t, mu_t, y_t, f_t, fechas_test, sigma, 0.05)[0]

    # 4. transporte + ACI (g02 consume RNG primero, luego g05: mismo orden que main)
    v3.correr_transporte_aci(h, test, s_cal, p_t, mu_t, y_t, f_t, fechas_test, sigma, 0.02, v3.RNG)
    U_tr = v3.correr_transporte_aci(h, test, s_cal, p_t, mu_t, y_t, f_t, fechas_test, sigma, 0.05, v3.RNG)[0]

    series = {"1_estatico_pit": U_est, "2_ventana60d_pit": U_vent,
              "3_aci_pit_g05": U_aci, "4_transporte_banda_g05": U_tr}

    # autochequeo: la cobertura/ancho agregada debe coincidir con la tabla oficial
    _verificar_contra_tabla(cm, f_t, y_t, series)
    return pd.to_datetime(f_t), y_t, series


def _verificar_contra_tabla(cm, f_t, y_t, series):
    tabla = pd.read_csv(FLAGSHIP / "conformal_v3_tabla.csv")
    problemas = []
    for metodo, U in series.items():
        for fila in cm.filas_por_periodo(metodo, f_t, y_t, U):
            ref = tabla[(tabla.metodo == metodo) & (tabla.periodo == fila["periodo"])]
            if ref.empty:
                continue
            dc = abs(float(ref.cobertura.iloc[0]) - fila["cobertura"])
            da = abs(float(ref.ancho_medio.iloc[0]) - fila["ancho_medio"])
            if dc > 0.15 or da > 1.0:
                problemas.append(f"{metodo}/{fila['periodo']}: dcob={dc:.2f} danc={da:.1f}")
    if problemas:
        raise AssertionError("fig3 no reproduce conformal_v3_tabla.csv:\n" + "\n".join(problemas))
    print("  [check] series de fig3 reproducen conformal_v3_tabla.csv")


# ================================== FIGURA 3: COBERTURA RODANTE (ancho doble)
def figura_3(ventana=90):
    fecha, y, series = _series_conformal()
    idx_full = pd.date_range(fecha.min(), fecha.max(), freq="D")

    fig, ax = plt.subplots(figsize=(COL_DOBLE, 3.1))

    # banda de la ventana de maxima divergencia respecto de la calibracion
    ax.axvspan(TRANS_INI, TRANS_FIN, color=GRIS_TENUE, zorder=0)
    ax.text(TRANS_INI + (TRANS_FIN - TRANS_INI) / 2, 99.4, "Max. divergence",
            ha="center", va="top", fontsize=7, color=TINTA_MUTED)
    # nominal 90%
    ax.axhline(90, color=TINTA_MUTED, linewidth=0.9, linestyle=(0, (1, 2)), zorder=1)
    ax.text(idx_full[3], 90, "90% nominal", ha="left", va="bottom",
            fontsize=6.8, color=TINTA_MUTED)

    for metodo, (etq, color, ls, mk, _h) in METODOS.items():
        d = pd.DataFrame({"fecha": fecha, "cub": (y <= series[metodo]).astype(float)})
        por_dia = d.groupby("fecha").cub.mean().reindex(idx_full)
        rod = 100 * por_dia.rolling(ventana, min_periods=int(ventana * 0.6)).mean()
        ax.plot(rod.index, rod.values, label=etq, color=color, linestyle=ls,
                linewidth=1.4, marker=mk, markevery=48, markersize=3.5,
                markerfacecolor=color, markeredgecolor="white",
                markeredgewidth=0.3, zorder=3)

    ax.set_ylim(78, 100)
    ax.set_ylabel(f"{ventana}-day rolling coverage (%)")
    ax.set_xlabel("Date")
    _despejar(ax)
    leg = ax.legend(loc="lower left", frameon=False, ncol=2,
                    handletextpad=0.5, columnspacing=1.3, labelspacing=0.35)
    for t in leg.get_texts():
        t.set_color(TINTA_2)

    _guardar(fig, "fig3_rolling_coverage")


# =========================== FIGURA 4: COBERTURA vs SHARPNESS (ancho doble, 2 paneles)
def figura_4():
    tabla = pd.read_csv(FLAGSHIP / "conformal_v3_tabla.csv")
    metodos = list(METODOS.keys())
    periodos = list(PERIODOS_ETQ.keys())
    piv_cov = tabla.pivot(index="metodo", columns="periodo", values="cobertura")
    piv_se = tabla.pivot(index="metodo", columns="periodo", values="se_cluster")
    piv_anc = tabla.pivot(index="metodo", columns="periodo", values="ancho_medio")
    piv_inf = tabla.pivot(index="metodo", columns="periodo", values="pct_infinito")

    fig, (axc, axw) = plt.subplots(1, 2, figsize=(COL_DOBLE, 3.2))
    x = np.arange(len(periodos))
    nm = len(metodos)
    w = 0.80 / nm

    def _barras(ax, piv, con_error):
        for j, metodo in enumerate(metodos):
            etq, color, _ls, _mk, hatch = METODOS[metodo]
            vals = [piv.loc[metodo, p] for p in periodos]
            xpos = x + (j - (nm - 1) / 2) * w
            err = [piv_se.loc[metodo, p] for p in periodos] if con_error else None
            ax.bar(xpos, vals, width=w * 0.92, color=color, edgecolor="white",
                   linewidth=0.5, hatch=hatch, label=etq, zorder=2,
                   yerr=err, error_kw=dict(ecolor=TINTA_2, elinewidth=0.7,
                                           capsize=1.6, capthick=0.7))
        ax.set_xticks(x)
        # 6.0 pt: "Pre-transition" y "Transition" son etiquetas largas y contiguas;
        # a 6.8 pt sus cajas se tocan y el eje deja de leerse
        ax.set_xticklabels([PERIODOS_ETQ[p] for p in periodos], fontsize=6.0)
        _despejar(ax)
        ax.tick_params(axis="x", length=0)

    # panel izquierdo: cobertura con se clusterizado
    _barras(axc, piv_cov, con_error=True)
    axc.axhline(90, color=TINTA_MUTED, linewidth=0.9, linestyle=(0, (1, 2)), zorder=1)
    axc.text(x[-1] + 0.45, 90, "90%", ha="left", va="center", fontsize=6.8,
             color=TINTA_MUTED)
    axc.set_ylim(80, 100)
    axc.set_ylabel("Empirical coverage (%)")

    # panel derecho: ancho medio (sobre intervalos finitos); marca donde hay
    # una fraccion no trivial de intervalos infinitos (excluidos del promedio)
    _barras(axw, piv_anc, con_error=False)
    axw.set_ylabel("Mean interval width (MWh)")
    ymaxw = axw.get_ylim()[1]
    for j, metodo in enumerate(metodos):
        for i, p in enumerate(periodos):
            if piv_inf.loc[metodo, p] >= 1.0:
                xpos = x[i] + (j - (nm - 1) / 2) * w
                axw.text(xpos, piv_anc.loc[metodo, p] + ymaxw * 0.015, "*",
                         ha="center", va="bottom", fontsize=8, color=TINTA_2)

    handles = [Patch(facecolor=METODOS[m][1], edgecolor="white", hatch=METODOS[m][4],
                     label=METODOS[m][0]) for m in metodos]
    leg = fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
                     bbox_to_anchor=(0.5, 1.06), handletextpad=0.5, columnspacing=1.4)
    for t in leg.get_texts():
        t.set_color(TINTA_2)

    fig.subplots_adjust(wspace=0.32)
    _guardar(fig, "fig4_coverage_width")


# ============================ FIGURA 5: REGIMEN Y PUNTOS DE CAMBIO (ancho doble)
def _costo_l2(y):
    """Suma de desviaciones cuadraticas al promedio del segmento."""
    return float(((y - y.mean()) ** 2).sum()) if len(y) else 0.0


def _segmentacion_binaria(y, pen, min_size=3):
    """Segmentacion binaria exacta con coste L2 y penalizacion por quiebre.

    Equivalente a ruptures.Binseg(model='l2', min_size=3, jump=1) con la misma
    penalizacion; se implementa aqui en numpy para no agregar una dependencia
    al entorno del repositorio. Sobre la serie desestacionalizada de solar norte
    devuelve los mismos dos quiebres que PELT (2023-05 y 2024-01), lo que se
    verifica con la asercion al final de figura_5().
    """
    quiebres = []

    def recorrer(a, b):
        if b - a < 2 * min_size:
            return
        base = _costo_l2(y[a:b])
        mejor, mejor_ganancia = None, 0.0
        for k in range(a + min_size, b - min_size + 1):
            ganancia = base - _costo_l2(y[a:k]) - _costo_l2(y[k:b])
            if ganancia > mejor_ganancia:
                mejor_ganancia, mejor = ganancia, k
        if mejor is not None and mejor_ganancia > pen:
            quiebres.append(mejor)
            recorrer(a, mejor)
            recorrer(mejor, b)

    recorrer(0, len(y))
    return sorted(quiebres)


def figura_5():
    """Serie mensual de la media de log(Y|Y>0) para solar del norte, cruda y
    desestacionalizada, con los puntos de cambio y las ventanas de evaluacion.

    Sostiene la afirmacion de la Seccion 3.3 de que el desplazamiento es una
    rampa de ~18 meses (quiebres en may-2023 y ene-2024) y que no hay quiebre
    ni en octubre de 2024 ni en 2025.
    """
    daily = pd.read_parquet(RELEASE / "curtailment_daily.parquet",
                            columns=["fecha", "central_codigo", "mwh"])
    daily["fecha"] = pd.to_datetime(daily["fecha"])
    plants = pd.read_parquet(RELEASE / "plants.parquet")
    meta = pd.read_parquet(RELEASE / "plants_metadata.parquet",
                           columns=["central_codigo", "region"])
    df = daily.merge(plants, on="central_codigo").merge(meta, on="central_codigo")

    # solar del norte: es donde se concentra el vertimiento del sistema
    norte = df[(df["tecnologia"] == "Solar")
               & (df["region"].isin(["Antofagasta", "Atacama"]))
               & (df["mwh"] > 0)]
    serie = (norte.groupby(norte["fecha"].values.astype("datetime64[M]"))["mwh"]
             .apply(lambda x: np.log(x).mean()))
    fechas = pd.to_datetime(serie.index)
    cruda = serie.values

    # desestacionalizacion robusta: mediana por mes calendario
    moy = fechas.month
    efecto = pd.Series(cruda, index=moy).groupby(level=0).median()
    resid = cruda - efecto.reindex(moy).values

    # quiebres sobre la serie desestacionalizada, penalizacion tipo BIC
    n = len(resid)
    sigma2 = np.var(np.diff(resid)) / 2
    pen = 3 * sigma2 * np.log(n)
    bk = _segmentacion_binaria(resid, pen)

    fig, (axa, axb) = plt.subplots(2, 1, figsize=(COL_DOBLE, 4.6), sharex=True)

    for ax in (axa, axb):
        ax.axvspan(CAL_INI, CAL_FIN, color=GRIS_TENUE, zorder=0)
        ax.axvspan(TRANS_INI, TRANS_FIN, color="#f3e2c8", zorder=0)
        _despejar(ax)

    # ---- panel superior: serie cruda, dominada por el ciclo anual
    axa.plot(fechas, cruda, color=TINTA_1, linewidth=1.3, zorder=3)
    axa.plot(fechas, cruda, color=TINTA_1, marker="o", markersize=2.2,
             linestyle="none", zorder=4)
    axa.set_ylabel("Mean $\\log Y$ (raw)")
    axa.text(CAL_INI + (CAL_FIN - CAL_INI) / 2, axa.get_ylim()[1], "calibration",
             ha="center", va="top", fontsize=6.8, color=TINTA_MUTED)
    axa.text(TRANS_INI + (TRANS_FIN - TRANS_INI) / 2, axa.get_ylim()[1],
             "max. div.", ha="center", va="top", fontsize=6.8, color=TINTA_MUTED)

    # ---- panel inferior: desestacionalizada, con quiebres y niveles por tramo
    axb.plot(fechas, resid, color=TINTA_1, linewidth=1.3, zorder=3)
    axb.plot(fechas, resid, color=TINTA_1, marker="o", markersize=2.2,
             linestyle="none", zorder=4)

    bordes = [0] + list(bk) + [n]
    for j in range(len(bordes) - 1):
        a, b = bordes[j], bordes[j + 1]
        nivel = resid[a:b].mean()
        fin = fechas[b - 1] + pd.offsets.MonthEnd(1)
        axb.hlines(nivel, fechas[a], fin, color="#eb6834", linewidth=1.6,
                   linestyle=(0, (4, 1.6)), zorder=5)

    for j, i in enumerate(bk):
        antes = resid[bordes[j]:i].mean()
        despues = resid[i:bordes[j + 2]].mean()
        axb.axvline(fechas[i], color="#eb6834", linewidth=0.9, zorder=2)
        axb.annotate(f"{fechas[i].strftime('%b %Y')}\n{despues - antes:+.2f}",
                     xy=(fechas[i], axb.get_ylim()[0]),
                     xytext=(4, 4), textcoords="offset points",
                     ha="left", va="bottom", fontsize=6.8, color="#eb6834")

    axb.axhline(0, color=HAIRLINE, linewidth=0.8, zorder=1)
    axb.set_ylabel("Mean $\\log Y$ (deseasonalised)")

    handles = [Line2D([], [], color=TINTA_1, marker="o", markersize=2.6,
                      linewidth=1.3, label="Monthly mean"),
               Line2D([], [], color="#eb6834", linewidth=1.6,
                      linestyle=(0, (4, 1.6)), label="Segment level"),
               Line2D([], [], color="#eb6834", linewidth=0.9,
                      label="Change point")]
    leg = axa.legend(handles=handles, loc="upper left", frameon=False,
                     ncol=1, handletextpad=0.5, borderpad=0.1,
                     labelspacing=0.35)
    for t in leg.get_texts():
        t.set_color(TINTA_2)

    fig.subplots_adjust(hspace=0.14)

    fechas_bk = [str(pd.Period(fechas[i], freq="M")) for i in bk]
    assert fechas_bk == ["2023-05", "2024-01"], fechas_bk
    print(f"  fig5: quiebres {fechas_bk}, penalizacion {pen:.4f}")
    _guardar(fig, "fig5_regime_changepoints")


if __name__ == "__main__":
    print("Generando figuras SEGAN en", OUT)
    figura_1()
    figura_2()
    figura_3()
    figura_4()
    figura_5()
    print("Listo.")
