"""Genera la planilla de predios urbanos FICTICIA que alimenta el modelo DAX.

TODOS LOS DATOS SON FICTICIOS: no provienen de ninguna institución, predio o contribuyente real.
  - Nombres:         "CONTRIBUYENTE FICTICIO 000123"
  - Código predial:  prefijo "99" (zona inexistente), p. ej. 99-014-0123-045
  - Montos y áreas:  muestreados con distribuciones log-normales (semilla fija = reproducible)

Uso:  python src/generar_datos_ficticios.py
Salida: data/planilla_predios_urbanos_FICTICIO.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

from logica_dax import calcular

N_PREDIOS = 10_000
SEMILLA = 20240131

CLASES = ["A", "A21", "D", "D2", "D5", "E2", "G1", "G2", "I1", "J1", "J2", "F1", "F2", "F10"]
PESOS = [0.40, 0.06, 0.08, 0.08, 0.04, 0.03, 0.04, 0.03, 0.02, 0.02, 0.02, 0.06, 0.10, 0.02]
SIN_CONSTRUCCION = ["F1", "F2", "F10"]          # solares no edificados


def generar(n: int = N_PREDIOS, semilla: int = SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)

    cat = rng.choice(CLASES, n, p=PESOS)
    sin_const = np.isin(cat, SIN_CONSTRUCCION)

    # --- Áreas y avalúos del año vigente ---
    area = np.clip(np.round(rng.lognormal(np.log(220), 0.55, n), 2), 40, 5000)
    av_solar = np.round(area * rng.lognormal(np.log(70), 0.45, n), 2)
    av_const_prev = np.where(sin_const, 0.0, np.round(rng.lognormal(np.log(130), 0.5, n) * rng.lognormal(np.log(260), 0.3, n), 2))

    # --- Año anterior: reavalúo anual de 0 % a 10 % ---
    av_solar_ant = np.round(av_solar / (1 + rng.uniform(0.0, 0.10, n)), 2)
    av_const_ant = np.round(av_const_prev / (1 + rng.uniform(0.0, 0.08, n)), 2)

    # --- Cambios entre años (7 % amplía construcción, 6 % cambia el área del solar) ---
    cambio_const = (rng.random(n) < 0.07) & ~sin_const
    av_const = np.where(cambio_const, np.round(av_const_ant * rng.uniform(1.10, 1.60, n), 2), av_const_prev)
    cambio_area = rng.random(n) < 0.06
    area_ant = np.where(cambio_area, np.round(area * rng.uniform(0.70, 1.30, n), 2), area)

    # --- Clasificaciones ---
    cat_ant = cat.copy()
    cambia_cat = rng.random(n) < 0.05
    cat_ant[cambia_cat] = rng.choice(CLASES, cambia_cat.sum())
    viene_de_a21 = (rng.random(n) < 0.03) & (cat != "A21")
    cat_ant[viene_de_a21] = "A21"
    cambio_cat = cat != cat_ant

    clasif_fin = rng.choice(["SIN", "TERCERA EDAD", "DISCAPACIDAD", "EXONERADO"], n, p=[0.88, 0.06, 0.03, 0.03])
    cambio_fin = rng.random(n) < 0.03

    # --- Reproceso ---
    pagado_antes = rng.random(n) < 0.30
    reprocesado = rng.random(n) < 0.12
    av_solar_repro = np.where(reprocesado, np.round(av_solar * rng.uniform(0.92, 1.08, n), 2), av_solar)

    # --- Tarifa y rubro del año anterior ---
    tarifa_ant = np.round(np.clip(rng.lognormal(np.log(0.0012), 0.45, n), 0.00025, 0.005), 6)
    rubro_ant = np.round(tarifa_ant * (av_const_ant + av_solar_ant), 2)

    si_no = lambda m: np.where(m, "SI", "NO")  # noqa: E731
    df = pd.DataFrame({
        "Código Predial": [f"99-{rng.integers(1, 40):03d}-{i // 40 + 1:04d}-{i % 40 + 1:03d}" for i in range(n)],
        "Nombre": [f"CONTRIBUYENTE FICTICIO {i + 1:06d}" for i in range(n)],
        "Año Vigencia": 2024,
        "Estado Deuda": np.where(rng.random(n) < 0.62, "EN DEUDA", "PAGADO"),
        "Clasificación Catastro": cat,
        "Clasificación Catastro (Año Anterior)": cat_ant,
        "Cambio Clasificación Catastro": si_no(cambio_cat),
        "Clasificación Financiero": clasif_fin,
        "Cambio Clasificación Financiero": si_no(cambio_fin),
        "Pagado Antes Reproceso": si_no(pagado_antes),
        "Area Solar": area,
        "Area Solar (Año Anterior)": area_ant,
        "Cambio Area Solar": si_no(area_ant != area),
        "Avalúo Solar": av_solar,
        "Avalúo Solar (Después Reproceso)": av_solar_repro,
        "Avalúo Solar (Año Anterior)": av_solar_ant,
        "Avalúo Construcción": av_const,
        "Avalúo Construcción (Año Anterior)": av_const_ant,
        "Cambio Avalúo Construcción": si_no(cambio_const),
        "Tarifa (Año Anterior)": tarifa_ant,
        "Rubro01 ImpPredial (Año Anterior)": rubro_ant,
        "Rubro01 ImpPredial": 0.0,
        "Rubro07 SolarNoEdif": 0.0,
    })

    # --- Valores "emitidos": coinciden con la simulación salvo en un porcentaje de casos ---
    sim = calcular(df)
    ip = sim["IMPUESTO PREDIAL"].to_numpy()
    nedif = sim["Solar_no_edificado_SIM"].to_numpy()
    u = rng.random(n)
    emitido = np.where(u < 0.06, ip * rng.uniform(0.80, 0.97, n),        # emitido de menos -> COBRAR
              np.where(u < 0.12, ip * rng.uniform(1.03, 1.25, n), ip))   # emitido de más  -> DEVOLVER
    u2 = rng.random(n)
    emitido_noedif = np.where((u2 < 0.04) & (nedif > 0), nedif * rng.uniform(0.85, 1.15, n), nedif)
    df["Rubro01 ImpPredial"] = np.round(emitido, 2)
    df["Rubro07 SolarNoEdif"] = np.round(emitido_noedif, 2)
    return df


def resumen(df: pd.DataFrame) -> str:
    r = calcular(df)
    g = r.groupby("ACCION")["DIF_TOTAL"].agg(["count", "sum"]).round(2)
    g["% predios"] = (g["count"] / len(r) * 100).round(1)
    lineas = [f"Predios: {len(r):,}", g.to_string()]
    return "\n".join(lineas)


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    destino = raiz / "data" / "planilla_predios_urbanos_FICTICIO.csv"
    destino.parent.mkdir(exist_ok=True)
    datos = generar()
    datos.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Archivo generado: {destino} ({len(datos):,} filas, {destino.stat().st_size / 1e6:.1f} MB)")
    print(resumen(datos))
