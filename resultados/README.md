# resultados/ — artefactos de la revision mayor SEGAN-D-26-03850

Todo lo que hay aqui se regenera con los comandos de `CHANGELOG_REVISION.md`.
Cada corrida deja un log fechado en `logs/`.

| Carpeta o archivo | Contenido | Script |
|---|---|---|
| `v_enviada/` | Resultados congelados de la version enviada. **No se sobrescriben nunca.** | (copia) |
| `fase0_model_agnostic.md` | Informe de la Fase 0, el hallazgo central | redactado desde los CSV |
| `fase0/` | Tabla por modelo base, diagnostico de 15 celdas, diferencias bootstrap | `fase0_*.py` |
| `fase1/` | Hiperparametros en CSV y el float LaTeX, leidos del codigo | `fase1_hiperparametros.py` |
| `fase2/` | Ablaciones y aporte marginal por componente | `fase2_ablaciones.py` |
| `fase3/` | Seleccion por origen rodante, sensibilidad sobre el test, JSON de elegidos | `fase3_seleccion_hiperparametros.py` |
| `fase4/` | Metricas completas, efecto de la cota de alpha, benchmarks, diferencias | `fase4_metricas_benchmarks.py` |
| `fase5/` | Diagnostico de dependencia, remedios, cobertura desagregada | `fase5_dependencia_panel.py` |
| `fase6/` | Series mensuales, puntos de cambio y su sensibilidad, Wasserstein, descomposicion estacional, verificacion de 24 afirmaciones | `fase6_cronologia.py` |
| `fase8/` | Candidatas de Crossref y referencias verificadas por DOI | `fase8_buscar_referencias.py` |
| `tablas_tex/` | Los diez floats de tabla del manuscrito, generados desde los CSV | `fase9_tablas_tex.py` |
| `verificacion_manuscrito.csv` | Las 43 afirmaciones en prosa del manuscrito contra su archivo fuente | `verificar_manuscrito.py` |
| `logs/` | Un log con timestamp por corrida | todas |

## Comprobacion rapida antes de enviar

```
$VENV flagship/revision/verificar_manuscrito.py    # debe dar 43 de 43
```
