import pytest
import pandas as pd
from audit_salarial_app.services.brecha_service import _calcular_metricas, _evaluar_riesgo_global

def test_calcular_metricas_standard_gap():
    # Caso 1: Los hombres ganan más que las mujeres
    data = {
        'Sexo': ['Hombre', 'Hombre', 'Hombre', 'Mujer', 'Mujer', 'Mujer'],
        'Salario': [50000.0, 60000.0, 40000.0, 30000.0, 40000.0, 20000.0]
    }
    df = pd.DataFrame(data)
    
    metrics = _calcular_metricas(df, 'Sexo', 'Salario')
    
    assert metrics['n_total'] == 6
    assert metrics['n_hombres'] == 3
    assert metrics['n_mujeres'] == 3
    assert metrics['media_hombres'] == 50000.0
    assert metrics['media_mujeres'] == 30000.0
    assert metrics['mediana_hombres'] == 50000.0
    assert metrics['mediana_mujeres'] == 30000.0
    assert metrics['salario_minimo'] == 20000.0
    assert metrics['salario_maximo'] == 60000.0
    
    # Brecha media: (50000 - 30000) / 50000 * 100 = 40%
    assert pytest.approx(metrics['brecha_media_pct']) == 40.0
    # Brecha mediana: (50000 - 30000) / 50000 * 100 = 40%
    assert pytest.approx(metrics['brecha_mediana_pct']) == 40.0
    # Brecha euros: 50000 - 30000 = 20000
    assert pytest.approx(metrics['brecha_media_euros']) == 20000.0

def test_calcular_metricas_reverse_gap():
    # Caso 2: Las mujeres ganan más que los hombres (brecha negativa)
    data = {
        'Sexo': ['Hombre', 'Hombre', 'Hombre', 'Mujer', 'Mujer', 'Mujer'],
        'Salario': [30000.0, 40000.0, 20000.0, 50000.0, 60000.0, 40000.0]
    }
    df = pd.DataFrame(data)
    
    metrics = _calcular_metricas(df, 'Sexo', 'Salario')
    
    assert metrics['media_hombres'] == 30000.0
    assert metrics['media_mujeres'] == 50000.0
    
    # Brecha media: (30000 - 50000) / 30000 * 100 = -66.67%
    assert pytest.approx(metrics['brecha_media_pct']) == -66.66666666666667
    assert pytest.approx(metrics['brecha_media_euros']) == -20000.0

def test_calcular_metricas_no_women():
    # Caso 3: Solo hay hombres
    data = {
        'Sexo': ['Hombre', 'Hombre', 'Hombre'],
        'Salario': [30000.0, 40000.0, 20000.0]
    }
    df = pd.DataFrame(data)
    
    metrics = _calcular_metricas(df, 'Sexo', 'Salario')
    
    assert metrics['n_hombres'] == 3
    assert metrics['n_mujeres'] == 0
    assert metrics['media_hombres'] == 30000.0
    assert metrics['media_mujeres'] == 0.0
    
    # Si no hay mujeres, la brecha debe ser 0.0 ya que no hay grupo de comparación
    assert metrics['brecha_media_pct'] == 0.0
    assert metrics['brecha_mediana_pct'] == 0.0
    assert metrics['brecha_media_euros'] == 0.0

def test_calcular_metricas_no_men():
    # Caso 4: Solo hay mujeres
    data = {
        'Sexo': ['Mujer', 'Mujer', 'Mujer'],
        'Salario': [30000.0, 40000.0, 20000.0]
    }
    df = pd.DataFrame(data)
    
    metrics = _calcular_metricas(df, 'Sexo', 'Salario')
    
    assert metrics['n_hombres'] == 0
    assert metrics['n_mujeres'] == 3
    assert metrics['media_hombres'] == 0.0
    assert metrics['media_mujeres'] == 30000.0
    
    # Si no hay hombres, la brecha debe ser 0.0 ya que no hay grupo de comparación
    assert metrics['brecha_media_pct'] == 0.0
    assert metrics['brecha_mediana_pct'] == 0.0
    assert metrics['brecha_media_euros'] == 0.0

def test_evaluar_riesgo_global_absolute_values():
    # Caso 5: Evaluar el riesgo con brecha positiva del 25% y 0 anomalías
    # 25% * 2.4 = 60.0. 60.0 + 10.0 = 70.0 (ALTO)
    riesgo, score = _evaluar_riesgo_global(25.0, 0)
    assert riesgo == 'ALTO'
    assert score == 70.0
    
    # Con 1 anomalía, el score llega a 75.0 (CRÍTICO)
    riesgo_crit, score_crit = _evaluar_riesgo_global(25.0, 1)
    assert riesgo_crit == 'CRÍTICO'
    assert score_crit == 75.0
    
    # Caso 6: Evaluar el riesgo con brecha negativa del -25% y las mismas condiciones
    # Por ley (RD 902/2020) esto es igualmente crítico/alto y debe arrojar el mismo score que el positivo
    riesgo_neg, score_neg = _evaluar_riesgo_global(-25.0, 0)
    assert riesgo_neg == 'ALTO'
    assert score_neg == 70.0
    
    riesgo_crit_neg, score_crit_neg = _evaluar_riesgo_global(-25.0, 1)
    assert riesgo_crit_neg == 'CRÍTICO'
    assert score_crit_neg == 75.0
