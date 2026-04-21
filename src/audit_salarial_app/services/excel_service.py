import pandas as pd
import numpy as np

def procesar_archivo_rahe(ruta_archivo):
    """
    Lee y valida la pestaña DATOS de la herramienta oficial RAHE.
    Extrae un DataFrame limpio de empleados.
    """
    try:
        # La cabecera útil con los nombres cortos de los campos y conceptos
        # retributivos en la herramienta oficial RAHE está en la fila 8 (índice 7).
        df = pd.read_excel(ruta_archivo, sheet_name="DATOS", header=7)
        
        # Identificar la columna Sexo para filtrar filas vacías
        col_sexo = next((c for c in df.columns if str(c).strip().lower() == 'sexo'), None)
        
        if col_sexo:
            # Nos quedamos solo con las filas que tienen valor en Sexo
            # (ignora sumatorios o filas en blanco del final)
            df = df.dropna(subset=[col_sexo])
            
            # Normalizar los valores de sexo (Hombre/Mujer)
            df[col_sexo] = df[col_sexo].astype(str).str.strip().str.capitalize()
            
            # Identificamos el Grupo Profesional si existe
            col_grupo = next((c for c in df.columns if 'grupo' in str(c).lower() or 'clasificaci' in str(c).lower()), None)
            
            # Calcular una "Retribución Total" aproximada sumando todas las numéricas
            # (En un uso real se separarían conceptos normalizables, anualizables, etc.)
            cols_numericas = df.select_dtypes(include=[np.number]).columns
            
            # Para la prueba, sumamos todo lo que parezca salarial como Total Efectivo
            df['Retribucion_Total_Calculada'] = df[cols_numericas].sum(axis=1)
            
            return {
                "valido": True,
                "df": df,
                "col_sexo": col_sexo,
                "col_grupo": col_grupo,
                "mensaje": f"Procesados {len(df)} registros correctamente."
            }
        else:
            return {
                "valido": False,
                "df": None,
                "mensaje": "No se encontró la columna 'Sexo' indispensable para el cálculo."
            }
            
    except Exception as e:
        return {
            "valido": False,
            "df": None,
            "mensaje": f"Error leyendo el archivo: {str(e)}"
        }
