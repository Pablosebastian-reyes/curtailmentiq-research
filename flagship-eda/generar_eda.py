#!/usr/bin/env python3
"""EDA descriptivo para el diseno del paper metodologico (flagship).

Genera 6 figuras (PDF vectorial + PNG 300 dpi) y un resumen de estadisticos
(eda_resumen.txt) en flagship-eda/, leyendo EXCLUSIVAMENTE el release
congelado release/v1.0/*.parquet. No entrena modelos: todo es descriptivo.

Analisis:
  1. estructura de ceros (motiva el modelo de dos partes)
  2. distribucion de magnitudes positivas (cola)
  3. perfil horario por estacion y anio (solar y eolica)
  4. drift interanual: distancia Wasserstein-1 de la distribucion horaria
  5. correlacion espacial del diario (top 20 centrales)
  6. persistencia temporal (ACF, lags 1 a 30)

Paletas validadas con el validador CVD del metodo de visualizacion
(peor par adyacente dE >= 21.6 en ambas paletas de 4 categorias).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import wasserstein_distance

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / "release" / "v1.0"
OUT = REPO / "flagship-eda"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.labelcolor": "#52514e",
    "axes.titlesize": 8,
    "axes.titlecolor": "#52514e",
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.color": "#898781",
    "ytick.color": "#898781",
    "axes.edgecolor": "#c3c2b7",
    "axes.linewidth": 0.6,
    "legend.fontsize": 7.5,
    "savefig.facecolor": "white",
    "pdf.fonttype": 42,
})
TINTA_1, TINTA_2, TINTA_MUTED = "#0b0b0b", "#52514e", "#898781"
GRID = "#e1e0d9"

TEC = {  # valores del dataset -> etiqueta EN + color (paleta validada)
    "Solar": ("Solar", "#eda100"),
    "Eólica": ("Wind", "#2a78d6"),
    "Hidro Pasada": ("Run-of-river hydro", "#1baf7a"),
    "Hidro Embalse": ("Reservoir hydro", "#4a3aa7"),
}
ESTACION_MESES = {"Summer": (12, 1, 2), "Autumn": (3, 4, 5),
                  "Winter": (6, 7, 8), "Spring": (9, 10, 11)}
ESTACION_COLOR = {"Summer": "#eda100", "Autumn": "#e34948",
                  "Winter": "#2a78d6", "Spring": "#1baf7a"}
MES_A_ESTACION = {m: e for e, ms in ESTACION_MESES.items() for m in ms}

resumen = []
def R(txt=""):
    resumen.append(txt)
    print(txt)

def guardar(fig, nombre):
    fig.savefig(OUT / f"{nombre}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{nombre}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] {nombre}")

def despinar(ax, lados=("top", "right")):
    for l in lados:
        ax.spines[l].set_visible(False)

print("Cargando release v1.0...")
daily = pd.read_parquet(RELEASE / "curtailment_daily.parquet")
daily["fecha"] = pd.to_datetime(daily["fecha"])
hourly = pd.read_parquet(RELEASE / "curtailment_hourly.parquet",
                         columns=["fecha", "hora", "central_codigo", "tecnologia", "mwh"])
hourly["fecha"] = pd.to_datetime(hourly["fecha"])
meta = pd.read_parquet(RELEASE / "plants_metadata.parquet",
                       columns=["central_codigo", "region", "latitud"])

# =====================================================================
# 1. ESTRUCTURA DE CEROS
# =====================================================================
R("=" * 70)
R("1. ESTRUCTURA DE CEROS (diario, por central-dia)")
R("=" * 70)
por_tec = daily.groupby("tecnologia")["mwh"].agg(dias="size", ceros=lambda s: (s == 0).sum())
por_tec["pct_cero"] = 100 * por_tec["ceros"] / por_tec["dias"]
for tec, fila in por_tec.iterrows():
    R(f"  {TEC[tec][0]:20s}: {fila.pct_cero:5.1f}% de central-dias en cero "
      f"({int(fila.ceros):,} de {int(fila.dias):,})")

# % de ceros por central y rachas por central
zero_share = (daily.assign(cero=daily.mwh == 0)
              .groupby(["tecnologia", "central_codigo"])["cero"].mean() * 100)

rachas = {"cero": {}, "positivo": {}}  # estado -> tec -> lista de largos
for (tec, central), g in daily.sort_values("fecha").groupby(["tecnologia", "central_codigo"]):
    pos = (g["mwh"] > 0).to_numpy()
    cambios = np.flatnonzero(np.diff(pos)) + 1
    largos = np.diff(np.concatenate(([0], cambios, [len(pos)])))
    estados = pos[np.concatenate(([0], cambios))]
    for largo, est in zip(largos, estados):
        rachas["positivo" if est else "cero"].setdefault(tec, []).append(int(largo))

med = {e: {t: np.median(v) for t, v in d.items()} for e, d in rachas.items()}
R("  mediana del largo de racha (dias) [sin curtailment / con curtailment]:")
for tec in TEC:
    R(f"    {TEC[tec][0]:20s}: {med['cero'].get(tec, float('nan')):5.0f} / "
      f"{med['positivo'].get(tec, float('nan')):3.0f}")

fig, axs = plt.subplots(1, 3, figsize=(8.6, 2.7))
# (a) ECDF del % de dias en cero por central
ax = axs[0]
for tec, (etq, color) in TEC.items():
    v = np.sort(zero_share.loc[tec].to_numpy())
    ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=color,
            linewidth=1.6, label=etq)
ax.set_xlabel("Share of days with zero curtailment per plant (%)")
ax.set_ylabel("Cumulative share of plants")
ax.set_title("Zero share per plant", pad=3)
ax.set_xlim(0, 100); ax.set_ylim(0, 1.02)
# (b) y (c) supervivencia del largo de rachas
for ax, estado, titulo in ((axs[1], "cero", "Zero-curtailment runs"),
                           (axs[2], "positivo", "Positive-curtailment runs")):
    for tec, (etq, color) in TEC.items():
        v = np.sort(np.array(rachas[estado].get(tec, [1])))
        surv = 1 - np.arange(len(v)) / len(v)
        ax.step(v, surv, where="post", color=color, linewidth=1.6)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Run length (days)")
    ax.set_ylabel("Share of runs >= x")
    ax.set_title(titulo, pad=3)
for ax in axs:
    ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
    despinar(ax)
manejadores_tec = [plt.Line2D([], [], color=c, linewidth=1.6, label=e)
                   for e, c in TEC.values()]
fig.legend(handles=manejadores_tec, loc="upper center", ncol=4, frameon=False,
           bbox_to_anchor=(0.5, 1.09))
fig.tight_layout()
guardar(fig, "eda1_zero_structure")

# =====================================================================
# 2. MAGNITUDES POSITIVAS
# =====================================================================
R("")
R("=" * 70)
R("2. MAGNITUDES POSITIVAS (mwh diario cuando mwh > 0)")
R("=" * 70)
pos = daily[daily.mwh > 0]
R(f"  central-dias positivos: {len(pos):,} ({100 * len(pos) / len(daily):.1f}% del total)")
R("  percentiles del MWh diario positivo por tecnologia:")
R(f"    {'tecnologia':20s} {'p50':>8s} {'p90':>9s} {'p99':>10s} {'max':>10s}")
for tec in TEC:
    v = pos.loc[pos.tecnologia == tec, "mwh"]
    R(f"    {TEC[tec][0]:20s} {v.quantile(.5):8.2f} {v.quantile(.9):9.2f} "
      f"{v.quantile(.99):10.2f} {v.max():10.2f}")

fig, axs = plt.subplots(2, 4, figsize=(9.2, 3.9))
for j, (tec, (etq, color)) in enumerate(TEC.items()):
    v = pos.loc[pos.tecnologia == tec, "mwh"].to_numpy()
    axs[0, j].hist(v, bins=60, color=color, edgecolor="white", linewidth=0.2)
    axs[0, j].set_title(etq, pad=3)
    axs[1, j].hist(np.log10(v), bins=60, color=color, edgecolor="white", linewidth=0.2)
    ticks = range(-3, 5)
    axs[1, j].set_xticks(list(ticks))
    axs[1, j].set_xticklabels([f"$10^{{{k}}}$" for k in ticks])
    axs[1, j].set_xlim(-3.2, 4.2)
    axs[0, j].set_xlabel("Daily MWh (linear)")
    axs[1, j].set_xlabel("Daily MWh (log scale)")
for ax in axs.flat:
    ax.set_yscale("log")
    ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
    despinar(ax)
axs[0, 0].set_ylabel("Plant-days (log)")
axs[1, 0].set_ylabel("Plant-days (log)")
fig.tight_layout()
guardar(fig, "eda2_positive_magnitudes")

# =====================================================================
# 3. PERFIL HORARIO POR ESTACION Y ANIO
# =====================================================================
R("")
R("=" * 70)
R("3. PERFIL HORARIO POR ESTACION Y ANIO (media del MWh sistema por hora)")
R("=" * 70)
hh = hourly[hourly.tecnologia.isin(["Solar", "Eólica"])].copy()
sistema_h = (hh.groupby(["tecnologia", "fecha", "hora"], observed=True)["mwh"]
             .sum().reset_index())
sistema_h["anio"] = sistema_h.fecha.dt.year
sistema_h["estacion"] = sistema_h.fecha.dt.month.map(MES_A_ESTACION)
perfil = (sistema_h.groupby(["tecnologia", "anio", "estacion", "hora"], observed=True)["mwh"]
          .mean().reset_index())

anios = [2022, 2023, 2024, 2025, 2026]
fig, axs = plt.subplots(2, 5, figsize=(10.2, 4.2), sharex=True)
for i, tec in enumerate(("Solar", "Eólica")):
    ymax = perfil.loc[perfil.tecnologia == tec, "mwh"].max() * 1.06
    for j, anio in enumerate(anios):
        ax = axs[i, j]
        sub = perfil[(perfil.tecnologia == tec) & (perfil.anio == anio)]
        for est, color in ESTACION_COLOR.items():
            s = sub[sub.estacion == est]
            if len(s):
                ax.plot(s.hora, s.mwh, color=color, linewidth=1.5, label=est)
        ax.set_ylim(0, ymax)
        ax.set_xlim(1, 24); ax.set_xticks([4, 8, 12, 16, 20, 24])
        ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
        despinar(ax)
        if i == 0:
            ax.set_title(str(anio) + (" (Jan-May)" if anio == 2026 else ""), pad=3)
        if j == 0:
            ax.set_ylabel(f"{TEC[tec][0]}\nmean MWh per hour")
        else:
            ax.set_yticklabels([])
        if i == 1:
            ax.set_xlabel("Hour of day (1-24)")
manejadores = [plt.Line2D([], [], color=c, linewidth=1.6, label=e)
               for e, c in ESTACION_COLOR.items()]
fig.legend(handles=manejadores, loc="upper center", ncol=4, frameon=False,
           bbox_to_anchor=(0.5, 1.04))
fig.tight_layout()
guardar(fig, "eda3_hourly_profiles_by_season")

# hora pico solar por anio-estacion (para el resumen)
R("  hora pico del perfil solar por anio y estacion:")
solar_p = perfil[perfil.tecnologia == "Solar"]
for anio in anios:
    picos = []
    for est in ESTACION_MESES:
        s = solar_p[(solar_p.anio == anio) & (solar_p.estacion == est)]
        if len(s):
            picos.append(f"{est} h{int(s.loc[s.mwh.idxmax(), 'hora'])}")
    R(f"    {anio}: " + " | ".join(picos))

# bimodalidad: cuota matinal (h8-13) vs vespertina (h14-19) del MWh solar
R("  cuota del MWh solar recortado por bloque horario (manana h8-13 / tarde h14-19):")
solar_sis = sistema_h[sistema_h.tecnologia == "Solar"].copy()
solar_sis["anio"] = solar_sis.fecha.dt.year
for anio in anios:
    s = solar_sis[solar_sis.anio == anio]
    tot = s.mwh.sum()
    man = s.loc[s.hora.between(8, 13), "mwh"].sum() / tot * 100
    tar = s.loc[s.hora.between(14, 19), "mwh"].sum() / tot * 100
    R(f"    {anio}: manana {man:4.1f}% | tarde {tar:4.1f}%")

# =====================================================================
# 4. DRIFT INTERANUAL (WASSERSTEIN-1 SOBRE LA DISTRIBUCION HORARIA)
# =====================================================================
R("")
R("=" * 70)
R("4. DRIFT INTERANUAL: W1 entre distribuciones hora-del-dia (YoY, mes a mes)")
R("   (distribucion = en que hora del dia se recorta la energia del mes;")
R("    peso = MWh por hora; W1 en unidades de horas)")
R("=" * 70)
hreg = hourly.merge(meta[["central_codigo", "region"]], on="central_codigo")
hreg["mes"] = hreg.fecha.dt.to_period("M")

def pesos_horarios(df):
    """mes -> (horas, pesos MWh) de la distribucion hora-del-dia."""
    g = df.groupby(["mes", "hora"], observed=True)["mwh"].sum().reset_index()
    return {m: (sub.hora.to_numpy(), sub.mwh.to_numpy())
            for m, sub in g.groupby("mes") if sub.mwh.sum() > 0}

alcances = {
    "System": pesos_horarios(hreg),
    "Antofagasta": pesos_horarios(hreg[hreg.region == "Antofagasta"]),
    "Atacama": pesos_horarios(hreg[hreg.region == "Atacama"]),
}
COLOR_ALCANCE = {"System": TINTA_1, "Antofagasta": "#eda100", "Atacama": "#2a78d6"}

# distribucion de MAGNITUDES: valores horarios del sistema/region por mes
def valores_horarios(df):
    g = df.groupby(["mes", "fecha", "hora"], observed=True)["mwh"].sum().reset_index()
    return {m: sub.mwh.to_numpy() for m, sub in g.groupby("mes")}

alcances_mag = {
    "System": valores_horarios(hreg),
    "Antofagasta": valores_horarios(hreg[hreg.region == "Antofagasta"]),
    "Atacama": valores_horarios(hreg[hreg.region == "Atacama"]),
}

def serie_w1_yoy(dic, con_pesos):
    pares = []
    for m in sorted(dic):
        m_prev = m - 12
        if m_prev in dic:
            if con_pesos:
                u_h, u_w = dic[m]; v_h, v_w = dic[m_prev]
                w1 = wasserstein_distance(u_h, v_h, u_w, v_w)
            else:
                w1 = wasserstein_distance(dic[m], dic[m_prev])
            pares.append((m, w1))
    return pares

series_w1 = {n: serie_w1_yoy(d, True) for n, d in alcances.items()}
series_w1_mag = {n: serie_w1_yoy(d, False) for n, d in alcances_mag.items()}

fig, axs = plt.subplots(1, 3, figsize=(11.4, 3.0))
ticks_anio = [pd.Period(f"{a}-01", "M").to_timestamp() for a in (2023, 2024, 2025, 2026)]
for ax, series, ylab in ((axs[0], series_w1, "W1 of hour-of-day distribution (hours)"),
                         (axs[1], series_w1_mag, "W1 of hourly MWh distribution (MWh)")):
    for nombre, pares in series.items():
        x = [p[0].to_timestamp() for p in pares]
        y = [p[1] for p in pares]
        ax.plot(x, y, color=COLOR_ALCANCE[nombre], linewidth=1.5, label=nombre,
                marker="o", markersize=2.2)
    ax.set_ylabel(ylab)
    ax.set_xlabel("Month (vs same month previous year)")
    ax.set_xticks(ticks_anio)
    ax.set_xticklabels([t.year for t in ticks_anio])
    ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
    despinar(ax)
axs[0].legend(frameon=False, loc="upper right")

# panel c: perfil hora-del-dia normalizado de marzo, 2023 a 2026 (sistema)
ax = axs[2]
azules = {2023: "#9ec5f4", 2024: "#5598e7", 2025: "#256abf", 2026: "#0d366b"}
for anio, color in azules.items():
    m = pd.Period(f"{anio}-03", "M")
    if m in alcances["System"]:
        h, w = alcances["System"][m]
        ax.plot(h, w / w.sum(), color=color, linewidth=1.6, label=f"Mar {anio}")
ax.set_xlabel("Hour of day (1-24)")
ax.set_ylabel("Share of monthly curtailed MWh")
ax.set_xlim(1, 24); ax.set_xticks([4, 8, 12, 16, 20, 24])
ax.legend(frameon=False, loc="upper left")
ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
despinar(ax)
fig.tight_layout()
guardar(fig, "eda4_wasserstein_drift")

for nombre in series_w1:
    p_forma = series_w1[nombre]
    p_mag = series_w1_mag[nombre]
    prom = lambda pares, a: np.mean([w for m, w in pares if m.year == a])
    R(f"  {nombre}:")
    R(f"    forma (h)   : prom 2024 = {prom(p_forma, 2024):.2f} | 2025 = {prom(p_forma, 2025):.2f} | 2026 = {prom(p_forma, 2026):.2f}")
    R(f"    magnitud(MWh): prom 2024 = {prom(p_mag, 2024):,.0f} | 2025 = {prom(p_mag, 2025):,.0f} | 2026 = {prom(p_mag, 2026):,.0f}")

# =====================================================================
# 5. CORRELACION ESPACIAL (TOP 20 CENTRALES)
# =====================================================================
R("")
R("=" * 70)
R("5. CORRELACION ESPACIAL: diario, top 20 centrales por acumulado")
R("=" * 70)
top20 = daily.groupby("central_codigo")["mwh"].sum().nlargest(20).index.tolist()
orden_meta = meta.set_index("central_codigo").loc[top20]
orden_reg = (orden_meta.groupby("region")["latitud"].median()
             .sort_values(ascending=False).index.tolist())  # norte -> sur
orden = []
for reg in orden_reg:
    bloque = orden_meta[orden_meta.region == reg].sort_values("latitud", ascending=False)
    orden.extend(bloque.index.tolist())

ancho = daily[daily.central_codigo.isin(top20)].pivot_table(
    index="fecha", columns="central_codigo", values="mwh")
corr = ancho[orden].corr()

cmap = LinearSegmentedColormap.from_list("divergente", ["#2a78d6", "#f0efec", "#e34948"])
fig, ax = plt.subplots(figsize=(6.4, 5.6))
im = ax.imshow(corr.to_numpy(), cmap=cmap, vmin=-1, vmax=1)
ax.set_xticks(range(20)); ax.set_yticks(range(20))
ax.set_xticklabels(orden, rotation=90, fontsize=6)
ax.set_yticklabels(orden, fontsize=6)
# separadores y etiquetas por region
limites, pos0 = [], 0
for reg in orden_reg:
    n = (orden_meta.region == reg).sum()
    limites.append((reg, pos0, pos0 + n))
    pos0 += n
for reg, a, b in limites[:-1]:
    ax.axhline(b - 0.5, color="white", linewidth=1.6)
    ax.axvline(b - 0.5, color="white", linewidth=1.6)
for reg, a, b in limites:
    ax.text(20.0, (a + b - 1) / 2, reg, fontsize=6.5, color=TINTA_2,
            va="center", ha="left", rotation=0)
ax.tick_params(length=0)
cbar = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.16)
cbar.set_label("Pearson correlation of daily MWh", fontsize=7.5, color=TINTA_2)
cbar.ax.tick_params(labelsize=6.5)
cbar.outline.set_visible(False)
guardar(fig, "eda5_spatial_correlation")

dentro, fuera = [], []
reg_de = orden_meta["region"].to_dict()
for i, a in enumerate(orden):
    for j, b in enumerate(orden):
        if i < j:
            (dentro if reg_de[a] == reg_de[b] else fuera).append(corr.iloc[i, j])
R(f"  correlacion media intra-region: {np.mean(dentro):.3f} | inter-region: {np.mean(fuera):.3f}")
R(f"  top 20 concentran {100 * daily[daily.central_codigo.isin(top20)].mwh.sum() / daily.mwh.sum():.1f}% del curtailment total")

# =====================================================================
# 6. PERSISTENCIA TEMPORAL (ACF)
# =====================================================================
R("")
R("=" * 70)
R("6. PERSISTENCIA: ACF del diario, sistema y 5 centrales grandes (lags 1-30)")
R("=" * 70)

def acf(x, kmax=30):
    x = np.asarray(x, dtype=float)
    return [np.corrcoef(x[:-k], x[k:])[0, 1] for k in range(1, kmax + 1)]

sistema_d = daily.groupby("fecha")["mwh"].sum().sort_index()
top5 = top20[:5]
fig, ax = plt.subplots(figsize=(5.6, 3.2))
lags = range(1, 31)
acf_sys = acf(sistema_d.to_numpy())
for central in top5:
    s = ancho[central].dropna().sort_index()
    tec_c = daily.loc[daily.central_codigo == central, "tecnologia"].iloc[0]
    ax.plot(lags, acf(s.to_numpy()), color=TEC[tec_c][1], linewidth=1.0,
            alpha=0.65)
ax.plot(lags, acf_sys, color=TINTA_1, linewidth=2.2, label="System total")
ax.axhline(0, color="#c3c2b7", linewidth=0.6)
ax.set_xlabel("Lag (days)")
ax.set_ylabel("Autocorrelation of daily MWh")
ax.set_xlim(1, 30); ax.set_xticks([1, 7, 14, 21, 28])
ax.set_ylim(-0.1, 1)
ax.legend(handles=[plt.Line2D([], [], color=TINTA_1, linewidth=2.2, label="System total"),
                   plt.Line2D([], [], color="#eda100", linewidth=1.0, alpha=0.65,
                              label="Top-5 plants (by technology color)")],
          frameon=False, loc="upper right")
ax.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
despinar(ax)
fig.tight_layout()
guardar(fig, "eda6_persistence_acf")

R(f"  ACF sistema: lag1 = {acf_sys[0]:.3f} | lag7 = {acf_sys[6]:.3f} | lag30 = {acf_sys[29]:.3f}")
for central in top5:
    a = acf(ancho[central].dropna().to_numpy())
    R(f"  {central:22s}: lag1 = {a[0]:.3f} | lag7 = {a[6]:.3f}")

(OUT / "eda_resumen.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
print(f"\nResumen escrito en {OUT / 'eda_resumen.txt'}")
