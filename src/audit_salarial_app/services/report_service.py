import os
from datetime import datetime
from flask import current_app
from docx import Document
from docx.shared import Pt, Inches
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from ..extensions import db
from ..models import Auditoria, AuditoriaArchivo, Resultado, Dimension

def generar_informe_word(auditoria_id):
    auditoria = db.session.get(Auditoria, auditoria_id)
    if not auditoria:
        return False, "Auditoría no encontrada"
        
    doc = Document()
    doc.add_heading(f"Informe Técnico de Auditoría Salarial #{auditoria_id}", 0)
    
    p = doc.add_paragraph(f"Empresa: {auditoria.empresa.nombre}\n")
    p.add_run(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    # Global
    doc.add_heading("1. Análisis Global", level=1)
    res_global = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == auditoria_id,
        Dimension.codigo == 'GLOBAL'
    ).first()
    
    if res_global:
        doc.add_paragraph(f"Nº Total Empleados: {res_global.n_total}")
        doc.add_paragraph(f"Hombres: {res_global.n_hombres} - Mujeres: {res_global.n_mujeres}")
        doc.add_paragraph(f"Brecha Media: {res_global.brecha_media_pct:.2f}%")
        doc.add_paragraph(f"Brecha Mediana: {res_global.brecha_mediana_pct:.2f}%")
    else:
        doc.add_paragraph("No hay datos globales calculados.")
        
    # Grupos
    doc.add_heading("2. Análisis por Grupo Profesional", level=1)
    res_grupos = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == auditoria_id,
        Dimension.codigo == 'GRUPO_PROFESIONAL'
    ).order_by(Resultado.dimension_valor).all()
    
    if res_grupos:
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Grupo'
        hdr_cells[1].text = 'Media Hombres'
        hdr_cells[2].text = 'Media Mujeres'
        hdr_cells[3].text = 'Brecha (%)'
        
        for res in res_grupos:
            row_cells = table.add_row().cells
            row_cells[0].text = str(res.dimension_valor)
            row_cells[1].text = f"{res.media_hombres:.2f} €" if res.media_hombres else "0.00 €"
            row_cells[2].text = f"{res.media_mujeres:.2f} €" if res.media_mujeres else "0.00 €"
            row_cells[3].text = f"{res.brecha_media_pct:.2f}%" if res.brecha_media_pct else "0.00%"
    else:
        doc.add_paragraph("No hay datos por grupos calculados.")
        
    filename = f"Informe_Tecnico_Audit_{auditoria_id}_{datetime.now().strftime('%Y%m%d%H%M')}.docx"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    doc.save(filepath)
    
    aa = AuditoriaArchivo(
        auditoria_id=auditoria_id,
        tipo='WORD_TECNICO',
        ruta=filepath,
        nombre=filename
    )
    db.session.add(aa)
    db.session.commit()
    
    return True, filename

def generar_informe_pdf(auditoria_id):
    auditoria = db.session.get(Auditoria, auditoria_id)
    if not auditoria:
        return False, "Auditoría no encontrada"
        
    filename = f"Informe_Ejecutivo_Audit_{auditoria_id}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph(f"Informe Ejecutivo - Auditoría Salarial #{auditoria_id}", styles['Title']))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph(f"<b>Empresa:</b> {auditoria.empresa.nombre}", styles['Normal']))
    elements.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    res_global = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == auditoria_id,
        Dimension.codigo == 'GLOBAL'
    ).first()
    
    if res_global:
        elements.append(Paragraph("Resumen Global", styles['Heading2']))
        
        data = [
            ["Métrica", "Valor"],
            ["Total Empleados", str(res_global.n_total)],
            ["Hombres", str(res_global.n_hombres)],
            ["Mujeres", str(res_global.n_mujeres)],
            ["Brecha Salarial Media", f"{res_global.brecha_media_pct:.2f}%"],
            ["Brecha Salarial Mediana", f"{res_global.brecha_mediana_pct:.2f}%"]
        ]
        
        t = Table(data, colWidths=[200, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    
    doc.build(elements)
    
    aa = AuditoriaArchivo(
        auditoria_id=auditoria_id,
        tipo='PDF_EJECUTIVO',
        ruta=filepath,
        nombre=filename
    )
    db.session.add(aa)
    db.session.commit()
    
    return True, filename
