"""Réplica en Python de las medidas DAX del modelo (una fila = un predio).

Sirve para dos cosas:
  1. Generar datos ficticios coherentes con las reglas (ver generar_datos_ficticios.py).
  2. Verificar los resultados esperados sin abrir Power BI.

Transparencia: las medidas IP_SIM, IP_SIM_VARCONSTRU2, IP_SIM_A21 y DIF_IP no están en los
archivos originales de la carpeta dax/. Aquí se reconstruyen por analogía con las medidas de
tarifa y se documentan en dax/DAX_Medidas_Auxiliares_DEMO.txt.
Todos los datos del repositorio son FICTICIOS.
"""
import numpy as np
import pandas as pd

TARIFA_MIN = 0.00025   # 0,25 por mil
TARIFA_MAX = 0.005     # 5 por mil
TOLERANCIA = 0.01      # diferencias menores a un centavo se consideran cero

# Clasificaciones catastrales (códigos ficticios) agrupadas según la regla de tarifa
GRUPO_D2 = ["D2", "D", "D5", "J1", "I1", "E2", "G1"]
GRUPO_SOLAR = ["G2", "J2", "F10"]


def _tope(x):
    """Aplica los topes normativos de tarifa (0,25 a 5 por mil)."""
    return np.clip(x, TARIFA_MIN, TARIFA_MAX)


def _tolerancia(x):
    """Equivale a IF(AND(x >= -0.01, x <= 0.01), 0, x)."""
    return np.where(np.abs(x) <= TOLERANCIA, 0.0, x)


def calcular(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve el DataFrame con las medidas calculadas fila por fila."""
    with np.errstate(divide="ignore", invalid="ignore"):
        par = df["Pagado Antes Reproceso"].eq("SI")
        cat = df["Clasificación Catastro"]
        cat_ant = df["Clasificación Catastro (Año Anterior)"]

        area = df["Area Solar"]
        area_ant = df["Area Solar (Año Anterior)"]
        const = df["Avalúo Construcción"]
        const_ant = df["Avalúo Construcción (Año Anterior)"]
        solar_ant = df["Avalúo Solar (Año Anterior)"]
        tarifa_ant = df["Tarifa (Año Anterior)"]
        rubro_ant = df["Rubro01 ImpPredial (Año Anterior)"]

        # AVALUO_SOLAR = IF(PAR = "SI", Avalúo Solar (Después Reproceso), Avalúo Solar)
        av_solar = np.where(par, df["Avalúo Solar (Después Reproceso)"], df["Avalúo Solar"])

        # --- Piezas comunes de las tres medidas de tarifa ---
        vm2 = av_solar / area
        avasim = vm2 * area_ant
        tarifa_sol = _tope(solar_ant * tarifa_ant / av_solar)

        # --- TARIFA_IP_SIM ---
        tarifa_f = _tope(rubro_ant / (avasim + const))
        tarifa_d2 = _tope(const_ant * tarifa_ant / const)
        t_ip_sim = np.select(
            [cat.isin(GRUPO_D2), cat.isin(GRUPO_SOLAR)],
            [tarifa_d2, tarifa_sol],
            default=tarifa_f,
        )

        # --- TARIFA_IP_SIM_VARCONSTRU2 (usa la construcción del año anterior) ---
        tarifa_f_v2 = _tope(rubro_ant / (avasim + const_ant))
        tarifa_d2_v2 = _tope(const_ant * tarifa_ant / const_ant)
        t_ip_sim_v2 = np.select(
            [cat.isin(GRUPO_D2), cat.isin(["G2", "J2"])],
            [tarifa_d2_v2, tarifa_sol],
            default=tarifa_f_v2,
        )

        # --- TARIFA_IP_SIM_A21 ---
        avaluo_total_ant = const_ant + solar_ant
        ip_a21_ant = tarifa_ant * avaluo_total_ant
        avaluo_simulado = const_ant + av_solar
        avaluo_sim_total = np.where(par, avaluo_simulado, avaluo_total_ant)
        tarifa_f_a21 = _tope(ip_a21_ant / avaluo_sim_total)
        t_ip_sim_a21 = np.select(
            [cat.isin(GRUPO_D2), cat.isin(["G2", "J2"])],
            [tarifa_d2_v2, tarifa_sol],
            default=tarifa_f_a21,
        )

        # --- Condiciones de selección (idénticas en TARIFA_SIM e IMPUESTO PREDIAL) ---
        sin_cambio_fin = df["Cambio Clasificación Financiero"].eq("NO") & df["Clasificación Financiero"].eq("SIN")
        sin_cambio_cat = df["Cambio Clasificación Catastro"].eq("NO")
        cambio_const = df["Cambio Avalúo Construcción"]
        cambio_area = df["Cambio Area Solar"]

        usa_base = sin_cambio_fin & sin_cambio_cat & cambio_const.eq("NO")      # (NO/NO) y (NO/SI en área)
        usa_v2 = sin_cambio_fin & sin_cambio_cat & cambio_const.eq("SI") & cambio_area.eq("NO")
        usa_a21 = sin_cambio_fin & cat_ant.eq("A21") & cat.ne("A21")

        # Medidas auxiliares reconstruidas (ver dax/DAX_Medidas_Auxiliares_DEMO.txt)
        ip_sim = t_ip_sim * (const + av_solar)
        ip_sim_v2 = t_ip_sim_v2 * (const_ant + av_solar)
        ip_sim_a21 = t_ip_sim_a21 * avaluo_sim_total

        # El orden de evaluación del IF anidado original: base -> base(área) -> v2 -> a21 -> default
        tarifa_sim = np.select([usa_base, usa_v2, usa_a21], [t_ip_sim, t_ip_sim_v2, t_ip_sim_a21], default=t_ip_sim)
        impuesto_predial = np.select([usa_base, usa_v2, usa_a21], [ip_sim, ip_sim_v2, ip_sim_a21], default=ip_sim)

        # --- Solar no edificado ---
        avaluo_to = const + av_solar
        solar_no_edif = np.select(
            [cat.eq("F2"), cat.eq("F1")],
            [avaluo_to * (2 / 1000), avaluo_to * (2 / 1000) + avaluo_to * (1 / 1000)],
            default=0.0,
        )

        dif_ip = impuesto_predial - df["Rubro01 ImpPredial"]
        dif_noedif = _tolerancia(solar_no_edif - df["Rubro07 SolarNoEdif"])
        dif_total = _tolerancia(dif_ip + dif_noedif)
        accion = np.select([dif_total < -TOLERANCIA, dif_total > TOLERANCIA], ["DEVOLVER", "COBRAR"], default="NO APLICA")

    out = df.copy()
    out["TARIFA_SIM"] = tarifa_sim
    out["IMPUESTO PREDIAL"] = impuesto_predial
    out["Solar_no_edificado_SIM"] = solar_no_edif
    out["DIF_IP"] = dif_ip
    out["DIF_NoEdif"] = dif_noedif
    out["DIF_TOTAL"] = dif_total
    out["ACCION"] = accion
    return out
