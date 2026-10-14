# Simulación de Impuesto Predial con DAX

> ## ⚠ DATOS 100 % FICTICIOS
> Todos los datos de este repositorio —nombres, códigos prediales, áreas, avalúos, tarifas y montos— fueron
> **generados artificialmente** con [`src/generar_datos_ficticios.py`](src/generar_datos_ficticios.py).
> No corresponden a contribuyentes, predios ni valores reales de ninguna institución.
> Los nombres siguen el patrón `CONTRIBUYENTE FICTICIO 000123` y los códigos prediales usan el prefijo `99`.

## Qué es
Modelo analítico en **DAX** para **simular, conciliar y controlar el impuesto predial** de una planilla de
predios urbanos. Recalcula el impuesto bajo las reglas vigentes, lo compara con el valor emitido y clasifica
cada predio en **COBRAR**, **DEVOLVER** o **NO APLICA**.

El proyecto original se construyó sobre SQL Server y Power BI para una planilla de decenas de miles de predios.
En este repositorio la fuente es un CSV ficticio de 10 000 predios, de modo que cualquiera pueda ejecutarlo.

## Qué demuestra
- **DAX avanzado**: `VAR`, `CONCATENATEX`, contexto de filtro y selección condicional anidada.
- **Reglas de negocio normativas** expresadas como medidas: topes de tarifa de 0,25 ‰ a 5 ‰, tarifas por clasificación catastral, cambios de avalúo, de área y de clasificación.
- **Conciliación** entre un valor simulado y el emitido, con tolerancia de un centavo.
- **Trazabilidad**: cada resultado se explica por la rama de regla que lo produjo.

## Flujo de la simulación

```text
 Planilla de predios (1 fila = 1 predio)
              │
              ▼
 Selección de regla según cambios del predio
   ├─ sin cambios / solo cambió el área ──► TARIFA_IP_SIM            ► IP_SIM
   ├─ cambió el avalúo de construcción ───► TARIFA_IP_SIM_VARCONSTRU2 ► IP_SIM_VARCONSTRU2
   ├─ venía de la clasificación A21 ──────► TARIFA_IP_SIM_A21        ► IP_SIM_A21
   └─ cualquier otro caso ────────────────► TARIFA_IP_SIM            ► IP_SIM
              │
              ▼
 IMPUESTO PREDIAL (simulado)  −  valor emitido   = DIF_IP
 Solar no edificado simulado  −  valor emitido   = DIF_NoEdif
              │
              ▼
 DIF_TOTAL ──► ACCION: COBRAR (> 0,01) · DEVOLVER (< −0,01) · NO APLICA
```

## Estructura

```text
dax/    medidas DAX (originales + medidas auxiliares de la demo)
data/   planilla ficticia (CSV) y consulta de importación para Power Query
src/    generador de datos ficticios y réplica de la lógica en Python
```

## Modelo de datos
Una sola tabla, **`Planilla Predios Urbanos`**, con una fila por predio.

| Grupo | Columnas |
|---|---|
| Identificación (ficticia) | `Código Predial`, `Nombre`, `Año Vigencia`, `Estado Deuda` |
| Clasificación | `Clasificación Catastro`, `Clasificación Catastro (Año Anterior)`, `Cambio Clasificación Catastro`, `Clasificación Financiero`, `Cambio Clasificación Financiero` |
| Superficie y avalúos | `Area Solar`, `Area Solar (Año Anterior)`, `Cambio Area Solar`, `Avalúo Solar`, `Avalúo Solar (Después Reproceso)`, `Avalúo Solar (Año Anterior)`, `Avalúo Construcción`, `Avalúo Construcción (Año Anterior)`, `Cambio Avalúo Construcción` |
| Reproceso | `Pagado Antes Reproceso` |
| Año anterior y emitido | `Tarifa (Año Anterior)`, `Rubro01 ImpPredial (Año Anterior)`, `Rubro01 ImpPredial`, `Rubro07 SolarNoEdif` |

## Medidas

| Medida | Archivo | Qué hace |
|---|---|---|
| `TARIFA_IP_SIM`, `TARIFA_IP_SIM_VARCONSTRU2`, `TARIFA_IP_SIM_A21` | `dax/DAX_TARIFA_*.txt` | Tarifa simulada por variante de regla, con topes normativos |
| `TARIFA_SIM` | `dax/DAX_TARIFA_SIM.txt` | Elige la variante de tarifa aplicable |
| `IMPUESTO PREDIAL` | `dax/DAX_IMPUESTO PREDIAL.txt` | Elige el impuesto simulado aplicable |
| `Solar_no_edificado_SIM` | `dax/DAX_Solar_no_edificado_SIM.txt` | Recargo por solar no edificado según clasificación |
| `DIF_NoEdif`, `DIF_TOTAL`, `ACCION` | `dax/DAX_VARIAS.txt` | Conciliación y clasificación final |
| `IP_SIM`, `IP_SIM_VARCONSTRU2`, `IP_SIM_A21`, `DIF_IP` | `dax/DAX_Medidas_Auxiliares_DEMO.txt` | **Medidas auxiliares reconstruidas** (ver nota) |

> **Nota de transparencia.** Las cuatro medidas auxiliares no estaban en los archivos originales de este
> repositorio; se reconstruyeron por analogía con las medidas de tarifa para que el modelo de ejemplo se
> ejecute de punta a punta. Son una reconstrucción, no el código original, y el archivo lo indica en su encabezado.

## Cómo reproducirlo

**1. Generar los datos ficticios** (opcional, el CSV ya está incluido)
```bash
pip install -r requirements.txt
python src/generar_datos_ficticios.py
```
La semilla es fija, por lo que el CSV es idéntico en cada ejecución.

**2. Cargar en Power BI Desktop**
1. Crear un parámetro de texto `RutaDatos` con la carpeta `data\`.
2. Nueva consulta en blanco, pegar [`data/importar_powerquery.m`](data/importar_powerquery.m) y nombrar la tabla **`Planilla Predios Urbanos`**.
3. Crear las medidas en este orden: tarifas → `IP_SIM*` → `TARIFA_SIM` → `IMPUESTO PREDIAL` → `Solar_no_edificado_SIM` → `DIF_IP` → `DIF_NoEdif` → `DIF_TOTAL` → `ACCION`.
4. En una tabla, agregar `Código Predial` y las medidas. Al ser una fila por predio, cada medida se evalúa por predio.

**3. Verificar sin Power BI**
`src/logica_dax.py` replica las mismas reglas en Python (pandas). Es la referencia para comprobar los resultados.

## Resultado esperado con los datos ficticios

| ACCION | Predios | % | Σ DIF_TOTAL (USD ficticios) |
|---|---:|---:|---:|
| NO APLICA | 8 742 | 87,4 % | 0,00 |
| COBRAR | 626 | 6,3 % | 4 894,32 |
| DEVOLVER | 632 | 6,3 % | −6 115,80 |

Estas proporciones son un diseño del generador (≈ 12 % de predios con valor emitido distinto del simulado),
no una estadística de ninguna institución real.

## Stack
DAX · Power BI Desktop · Power Query (M) · Python (pandas, numpy) para generación y verificación

## Aviso
Proyecto de portafolio con fines demostrativos. No contiene información de contribuyentes, instituciones ni
sistemas reales.
