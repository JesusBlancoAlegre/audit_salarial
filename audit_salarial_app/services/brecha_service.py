import pandas as pd
from audit_salarial_app.models import Resultado, Dimension, RecomendacionCatalogo, AuditoriaRecomendacion, Auditoria
from audit_salarial_app.extensions import db

def _evaluar_riesgo_global(brecha_pct, num_anomalias=0):
    # Score ponderado (Fase 2)
    # Brecha: 60%
    score_brecha = min(60.0, max(0.0, brecha_pct * 2.4)) if brecha_pct > 0 else 0.0 # 25% brecha = 60 pts
    
    # Anomalías: 30%
    score_anomalias = min(30.0, num_anomalias * 5.0) # 6 anomalías = 30 pts
    
    # Antigüedad: 10% (Por defecto)
    score_antiguedad = 10.0
    
    score_total = score_brecha + score_anomalias + score_antiguedad
    
    if score_total >= 75:
        return 'CRÍTICO', score_total
    elif score_total >= 50:
        return 'ALTO', score_total
    elif score_total >= 25:
        return 'MEDIO', score_total
    else:
        return 'BAJO', score_total

def _calcular_metricas(df, col_sexo, col_salario):
    m_hombres = df[df[col_sexo] == 'Hombre'][col_salario]
    m_mujeres = df[df[col_sexo] == 'Mujer'][col_salario]
    
    n_hombres = len(m_hombres)
    n_mujeres = len(m_mujeres)
    n_total = n_hombres + n_mujeres
    
    media_hombres = float(m_hombres.mean()) if n_hombres > 0 else 0.0
    media_mujeres = float(m_mujeres.mean()) if n_mujeres > 0 else 0.0
    mediana_hombres = float(m_hombres.median()) if n_hombres > 0 else 0.0
    mediana_mujeres = float(m_mujeres.median()) if n_mujeres > 0 else 0.0
    
    salario_minimo = float(df[col_salario].min()) if n_total > 0 else 0.0
    salario_maximo = float(df[col_salario].max()) if n_total > 0 else 0.0
    desviacion_tipica = float(df[col_salario].std()) if n_total > 1 else 0.0
    
    brecha_media_pct = ((media_hombres - media_mujeres) / media_hombres * 100) if media_hombres > 0 else 0.0
    brecha_mediana_pct = ((mediana_hombres - mediana_mujeres) / mediana_hombres * 100) if mediana_hombres > 0 else 0.0
    brecha_media_euros = (media_hombres - media_mujeres) if media_hombres > 0 else 0.0
    
    return {
        "n_total": n_total,
        "n_hombres": n_hombres,
        "n_mujeres": n_mujeres,
        "media_hombres": media_hombres,
        "media_mujeres": media_mujeres,
        "mediana_hombres": mediana_hombres,
        "mediana_mujeres": mediana_mujeres,
        "salario_minimo": salario_minimo,
        "salario_maximo": salario_maximo,
        "desviacion_tipica": desviacion_tipica,
        "brecha_media_pct": float(brecha_media_pct),
        "brecha_mediana_pct": float(brecha_mediana_pct),
        "brecha_media_euros": float(brecha_media_euros)
    }

def _detectar_anomalias(df, auditoria_id, dimension_id, dimension_valor, col_salario):
    from audit_salarial_app.models import Anomalia
    
    anomalias_detectadas = []
    if len(df) < 4:
        return 0 # No enough data for reliable IQR
        
    salarios = df[col_salario]
    
    # Método IQR
    Q1 = salarios.quantile(0.25)
    Q3 = salarios.quantile(0.75)
    IQR = Q3 - Q1
    limite_inferior = float(Q1 - 1.5 * IQR)
    limite_superior = float(Q3 + 1.5 * IQR)
    
    # Método Z-Score
    media = salarios.mean()
    std = salarios.std()
    
    for idx, row in df.iterrows():
        val = float(row[col_salario])
        id_fila = int(row.get('id_fila_excel', idx + 9))
        
        # IQR Check
        if val < limite_inferior or val > limite_superior:
            anomalia_iqr = Anomalia(
                auditoria_id=auditoria_id,
                dimension_id=dimension_id,
                dimension_valor=dimension_valor,
                metodo='IQR',
                campo=col_salario,
                valor=val,
                umbral_inferior=limite_inferior,
                umbral_superior=limite_superior,
                severidad='ALTA' if (val > limite_superior * 1.2 or val < limite_inferior * 0.8) else 'MEDIA',
                descripcion=f"Salario atípico detectado mediante Rango Intercuartil. Fila: {id_fila}",
                id_fila_excel=id_fila
            )
            anomalias_detectadas.append(anomalia_iqr)
            continue
            
        # Z-Score Check
        if std > 0:
            z_score = float((val - media) / std)
            if abs(z_score) > 3:
                anomalia_z = Anomalia(
                    auditoria_id=auditoria_id,
                    dimension_id=dimension_id,
                    dimension_valor=dimension_valor,
                    metodo='Z-SCORE',
                    campo=col_salario,
                    valor=val,
                    z_score=z_score,
                    severidad='ALTA',
                    descripcion=f"Salario anómalo detectado por desviación típica extrema (Z={z_score:.2f}). Fila: {id_fila}",
                    id_fila_excel=id_fila
                )
                anomalias_detectadas.append(anomalia_z)
                
    if anomalias_detectadas:
        db.session.bulk_save_objects(anomalias_detectadas)
        
    return len(anomalias_detectadas)

def _asegurar_catalogo_recomendaciones():
    if RecomendacionCatalogo.query.count() == 0:
        recs = [
            RecomendacionCatalogo(codigo="REC_URG_01", titulo="Revisión Urgente de Política Retributiva", descripcion="La brecha supera el 25% legal. Es imperativo justificar objetivamente o corregir inmediatamente la política retributiva.", tipo="URGENTE", coste_estimado_default=5000, impacto_default=100, meses_default=1),
            RecomendacionCatalogo(codigo="REC_REV_02", titulo="Auditoría Específica de Puestos", descripcion="Revisión de la valoración de puestos de trabajo para corregir desviaciones superiores al 15%.", tipo="PREVENTIVA", coste_estimado_default=2500, impacto_default=50, meses_default=3),
            RecomendacionCatalogo(codigo="REC_MON_03", titulo="Monitorización de Nuevas Contrataciones", descripcion="Establecer bandas salariales estrictas para evitar que la brecha crezca.", tipo="PROCESO", coste_estimado_default=0, impacto_default=20, meses_default=6)
        ]
        db.session.bulk_save_objects(recs)
        db.session.commit()

def calcular_estadisticas(auditoria_id, df_info):
    if not df_info.get("valido") or df_info.get("df") is None:
        return False, "Datos no válidos para el cálculo."
        
    df = df_info["df"]
    col_sexo = df_info["col_sexo"]
    col_grupo = df_info["col_grupo"]
    col_salario = 'Retribucion_Total_Calculada'
    
    try:
        _asegurar_catalogo_recomendaciones()
        
        dim_global = Dimension.query.filter_by(codigo='GLOBAL').first()
        if not dim_global:
            dim_global = Dimension(codigo='GLOBAL', nombre='Global de la empresa')
            db.session.add(dim_global)
            
        dim_grupo = Dimension.query.filter_by(codigo='GRUPO_PROFESIONAL').first()
        if not dim_grupo:
            dim_grupo = Dimension(codigo='GRUPO_PROFESIONAL', nombre='Grupo Profesional')
            db.session.add(dim_grupo)
            
        db.session.commit()
        
        Resultado.query.filter_by(auditoria_id=auditoria_id).delete()
        AuditoriaRecomendacion.query.filter_by(auditoria_id=auditoria_id).delete()
        from audit_salarial_app.models import Anomalia
        Anomalia.query.filter_by(auditoria_id=auditoria_id).delete()
        
        # 1. Cálculo GLOBAL
        m_global = _calcular_metricas(df, col_sexo, col_salario)
        num_anom_global = _detectar_anomalias(df, auditoria_id, dim_global.id, 'TODOS', col_salario)
        nivel_riesgo, score_riesgo = _evaluar_riesgo_global(m_global["brecha_media_pct"], num_anom_global)
        
        res_global = Resultado(
            auditoria_id=auditoria_id,
            dimension_id=dim_global.id,
            dimension_valor='TODOS',
            nivel_riesgo=nivel_riesgo,
            score_riesgo=score_riesgo,
            **m_global
        )
        db.session.add(res_global)
        
        # MOTOR DE RECOMENDACIONES Y ALERTAS
        from audit_salarial_app.services.alerta_service import generar_alerta
        
        if nivel_riesgo == 'CRÍTICO':
            rec_cat = RecomendacionCatalogo.query.filter_by(codigo="REC_URG_01").first()
            if rec_cat:
                ar = AuditoriaRecomendacion(auditoria_id=auditoria_id, recomendacion_id=rec_cat.id, prioridad='URGENTE', coste_estimado_eur=rec_cat.coste_estimado_default, impacto_reduccion_pct=rec_cat.impacto_default, meses_estimados=rec_cat.meses_default)
                db.session.add(ar)
            generar_alerta(auditoria_id, tipo='BRECHA_CRITICA', severidad='CRÍTICA', asunto=f'¡Riesgo Crítico! Brecha > 25% detectada en Auditoría #{auditoria_id}', mensaje=f'Se ha calculado una brecha media global del {m_global["brecha_media_pct"]:.2f}%. Por ley (art. 28 ET) debe ser justificada objetivamente. Revise las recomendaciones.')
        elif nivel_riesgo == 'ALTO':
            rec_cat = RecomendacionCatalogo.query.filter_by(codigo="REC_REV_02").first()
            if rec_cat:
                ar = AuditoriaRecomendacion(auditoria_id=auditoria_id, recomendacion_id=rec_cat.id, prioridad='ALTA', coste_estimado_eur=rec_cat.coste_estimado_default, impacto_reduccion_pct=rec_cat.impacto_default, meses_estimados=rec_cat.meses_default)
                db.session.add(ar)
            generar_alerta(auditoria_id, tipo='BRECHA_ALTA', severidad='ALTA', asunto=f'Riesgo Alto detectado en Auditoría #{auditoria_id}', mensaje=f'Se ha calculado una brecha media global del {m_global["brecha_media_pct"]:.2f}%. Se recomienda iniciar una auditoría de puestos.')
        elif nivel_riesgo == 'MEDIO':
            rec_cat = RecomendacionCatalogo.query.filter_by(codigo="REC_MON_03").first()
            if rec_cat:
                ar = AuditoriaRecomendacion(auditoria_id=auditoria_id, recomendacion_id=rec_cat.id, prioridad='MEDIA', coste_estimado_eur=rec_cat.coste_estimado_default, impacto_reduccion_pct=rec_cat.impacto_default, meses_estimados=rec_cat.meses_default)
                db.session.add(ar)
        
        # 2. Cálculo por GRUPO PROFESIONAL
        if col_grupo:
            grupos = df[col_grupo].astype(str).unique()
            for g in grupos:
                sub_df = df[df[col_grupo].astype(str) == g]
                if len(sub_df) > 0:
                    m_grupo = _calcular_metricas(sub_df, col_sexo, col_salario)
                    num_anom_grupo = _detectar_anomalias(sub_df, auditoria_id, dim_grupo.id, g, col_salario)
                    n_riesgo, s_riesgo = _evaluar_riesgo_global(m_grupo["brecha_media_pct"], num_anom_grupo)
                    res_grupo = Resultado(
                        auditoria_id=auditoria_id,
                        dimension_id=dim_grupo.id,
                        dimension_valor=g,
                        nivel_riesgo=n_riesgo,
                        score_riesgo=s_riesgo,
                        **m_grupo
                    )
                    db.session.add(res_grupo)
                    
        db.session.commit()
        return True, "Cálculos y recomendaciones generados correctamente."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error en cálculo y guardado: {str(e)}"
