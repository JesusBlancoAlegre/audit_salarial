import pandas as pd
import numpy as np

# Columnas de retribución que la herramienta RAHE oficial calcula y normaliza.
# 'TOTAL Retrib Eq' = Total Retribución Equiparada (normalizada, la mejor métrica)
# 'TOTAL Retrib Ef' = Total Retribución Efectiva (valor real pagado)
_COL_SALARIO_PRINCIPAL = 'TOTAL Retrib Eq'
_COL_SALARIO_ALTERNATIVA = 'TOTAL Retrib Ef'
_COL_SALARIO_FALLBACK = 'TOTAL SALARIO Eq'

# Columnas de agrupación profesional por orden de preferencia
_COLS_GRUPO_PREFERENCIA = [
    'Grupo profesional',
    'Categoría profesional',
    'AGRUP. CLAS. PROF.',
    'AGRUP. VALOR. PTO.',
    'Puesto-empresa',
    'Escala-empresa',
    'Dpto-empresa',
]


def procesar_archivo_rahe(ruta_archivo):
    """
    Lee y valida la hoja DATOS de la herramienta oficial RAHE (RD 902/2020).
    - Cabecera útil en la fila 8 (índice 7).
    - Columna de sexo: 'Sexo'
    - Columna de salario principal: 'TOTAL Retrib Eq' (retribución equiparada)
    - Columna de grupo: primera disponible en la lista de preferencia.
    """
    try:
        df = pd.read_excel(ruta_archivo, sheet_name="DATOS", header=7)

        # ── 1. Columna SEXO ──────────────────────────────────────────────────
        col_sexo = next(
            (c for c in df.columns if str(c).strip().lower() == 'sexo'),
            None
        )
        if col_sexo is None:
            return {
                "valido": False, "df": None,
                "mensaje": "No se encontró la columna 'Sexo' en la hoja DATOS. "
                           "Verifica que el archivo sea la herramienta RAHE oficial."
            }

        # Filtrar filas vacías (sumatorios, notas al pie, etc.)
        df = df.dropna(subset=[col_sexo])
        df = df[df[col_sexo].astype(str).str.strip().str.lower().isin(['hombre', 'mujer'])]

        if len(df) == 0:
            return {
                "valido": False, "df": None,
                "mensaje": "No se encontraron filas con valores válidos en 'Sexo' (esperados: Hombre / Mujer)."
            }

        # Normalizar sexo
        df[col_sexo] = df[col_sexo].astype(str).str.strip().str.capitalize()

        # ── 2. Columna SALARIO ───────────────────────────────────────────────
        col_salario = None
        for candidato in [_COL_SALARIO_PRINCIPAL, _COL_SALARIO_ALTERNATIVA, _COL_SALARIO_FALLBACK]:
            if candidato in df.columns:
                # Verificar que tenga valores numéricos reales
                serie = pd.to_numeric(df[candidato], errors='coerce')
                if serie.notna().sum() > 0 and serie.max() > 100:  # >100 € = razonable
                    col_salario = candidato
                    df[col_salario] = serie
                    break

        if col_salario is None:
            # Último recurso: sumar solo conceptos salariales conocidos
            cols_sal = [c for c in df.columns if any(
                pat in str(c) for pat in ['S.BASE', 'SALARIO BASE', 'Conc.Sal.']
            )]
            if cols_sal:
                for c in cols_sal:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                df['Retribucion_Total_Calculada'] = df[cols_sal].sum(axis=1)
                col_salario = 'Retribucion_Total_Calculada'
            else:
                return {
                    "valido": False, "df": None,
                    "mensaje": "No se encontraron columnas salariales reconocibles "
                               "(esperadas: 'TOTAL Retrib Eq' o similares)."
                }
        
        # Asegurar nombre consistente para el motor de cálculo
        df['Retribucion_Total_Calculada'] = df[col_salario]

        # ── 3. Columna GRUPO PROFESIONAL ─────────────────────────────────────
        col_grupo = None
        for candidato in _COLS_GRUPO_PREFERENCIA:
            if candidato in df.columns:
                serie = df[candidato].astype(str).str.strip()
                valores_validos = serie[~serie.isin(['nan', '', 'None', 'NaN'])].nunique()
                if valores_validos >= 1:
                    col_grupo = candidato
                    df[col_grupo] = serie.replace({'nan': 'Sin Grupo Asignado', '': 'Sin Grupo Asignado', 'None': 'Sin Grupo Asignado'})
                    break

        # ── 4. ID de fila original para trazabilidad de anomalías ───────────
        df['id_fila_excel'] = df.index + 9

        return {
            "valido": True,
            "df": df,
            "col_sexo": col_sexo,
            "col_grupo": col_grupo,
            "col_salario_usada": col_salario,
            "mensaje": (
                f"Procesados {len(df)} registros. "
                f"Salario: '{col_salario}'. "
                f"Grupo: '{col_grupo or 'Sin columna de grupo detectada'}'."
            )
        }

    except ValueError as e:
        # Pestaña DATOS no encontrada
        if "Worksheet named" in str(e):
            return {
                "valido": False, "df": None,
                "mensaje": "No se encontró la hoja 'DATOS' en el archivo. "
                           "Asegúrate de usar la herramienta RAHE oficial del Ministerio."
            }
        return {"valido": False, "df": None, "mensaje": f"Error de formato: {e}"}
    except Exception as e:
        return {"valido": False, "df": None, "mensaje": f"Error leyendo el archivo: {e}"}
