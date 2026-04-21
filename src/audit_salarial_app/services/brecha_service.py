import pandas as pd
from audit_salarial_app.models import Resultado, Dimension
from audit_salarial_app.extensions import db

def _calcular_metricas(sub_df, col_sexo, col_salario):
    """Calcula las métricas de un subconjunto de datos."""
    hombres = sub_df[sub_df[col_sexo].str.upper() == 'HOMBRE'][col_salario]
    mujeres = sub_df[sub_df[col_sexo].str.upper() == 'MUJER'][col_salario]
    
    n_hombres = len(hombres)
    n_mujeres = len(mujeres)
    n_total = len(sub_df)
    
    media_h = hombres.mean() if n_hombres > 0 else 0
    media_m = mujeres.mean() if n_mujeres > 0 else 0
    mediana_h = hombres.median() if n_hombres > 0 else 0
    mediana_m = mujeres.median() if n_mujeres > 0 else 0
    
    # Brecha = (Hombre - Mujer) / Hombre * 100
    brecha_media_pct = ((media_h - media_m) / media_h * 100) if media_h > 0 else 0
    brecha_mediana_pct = ((mediana_h - mediana_m) / mediana_h * 100) if mediana_h > 0 else 0
    brecha_media_eur = media_h - media_m
    
    return {
        "n_total": n_total,
        "n_hombres": n_hombres,
        "n_mujeres": n_mujeres,
        "media_hombres": media_h,
        "media_mujeres": media_m,
        "mediana_hombres": mediana_h,
        "mediana_mujeres": mediana_m,
        "salario_minimo": sub_df[col_salario].min() if n_total > 0 else 0,
        "salario_maximo": sub_df[col_salario].max() if n_total > 0 else 0,
        "brecha_media_pct": brecha_media_pct,
        "brecha_mediana_pct": brecha_mediana_pct,
        "brecha_media_euros": brecha_media_eur
    }

def calcular_estadisticas(auditoria_id, df_info):
    """
    Calcula la brecha salarial global y por grupos profesionales.
    Persiste los datos en el modelo Resultado.
    """
    if not df_info.get("valido") or df_info.get("df") is None:
        return False, "Datos no válidos para el cálculo."
        
    df = df_info["df"]
    col_sexo = df_info["col_sexo"]
    col_grupo = df_info["col_grupo"]
    col_salario = 'Retribucion_Total_Calculada'
    
    try:
        # Asegurar dimensiones básicas en base de datos si no existen
        dim_global = Dimension.query.filter_by(codigo='GLOBAL').first()
        if not dim_global:
            dim_global = Dimension(codigo='GLOBAL', nombre='Global de la empresa')
            db.session.add(dim_global)
            
        dim_grupo = Dimension.query.filter_by(codigo='GRUPO_PROFESIONAL').first()
        if not dim_grupo:
            dim_grupo = Dimension(codigo='GRUPO_PROFESIONAL', nombre='Grupo Profesional')
            db.session.add(dim_grupo)
            
        db.session.commit()
        
        # Limpiar resultados anteriores de esta auditoría
        Resultado.query.filter_by(auditoria_id=auditoria_id).delete()
        
        # 1. Cálculo GLOBAL
        m_global = _calcular_metricas(df, col_sexo, col_salario)
        res_global = Resultado(
            auditoria_id=auditoria_id,
            dimension_id=dim_global.id,
            dimension_valor='TODOS',
            **m_global
        )
        db.session.add(res_global)
        
        # 2. Cálculo por GRUPO PROFESIONAL
        if col_grupo:
            grupos = df[col_grupo].astype(str).unique()
            for g in grupos:
                sub_df = df[df[col_grupo].astype(str) == g]
                if len(sub_df) > 0:
                    m_grupo = _calcular_metricas(sub_df, col_sexo, col_salario)
                    res_grupo = Resultado(
                        auditoria_id=auditoria_id,
                        dimension_id=dim_grupo.id,
                        dimension_valor=g,
                        **m_grupo
                    )
                    db.session.add(res_grupo)
                    
        db.session.commit()
        return True, "Cálculos realizados y guardados correctamente."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error en cálculo y guardado: {str(e)}"
