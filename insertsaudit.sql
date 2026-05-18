USE audit_salarial;

INSERT INTO rol (nombre, descripcion) VALUES
('ADMIN', 'Administrador del sistema'),
('AUDITOR', 'Auditor interno/externo'),
('CLIENTE', 'Empresa cliente');

INSERT INTO dimension (codigo, nombre, descripcion) VALUES
('GLOBAL', 'Brecha Global', 'Brecha total de la empresa'),
('DEPARTAMENTO', 'Por departamento', 'Comparación por departamento'),
('PUESTO', 'Por puesto', 'Comparación por puesto'),
('CATEGORIA', 'Por categoría/grupo', 'Comparación por categoría'),
('CONTRATO', 'Por tipo de contrato', 'Indefinido/temporal/etc.'),
('JORNADA', 'Por jornada', 'Completa/parcial'),
('ANTIGUEDAD', 'Por antigüedad', 'Rangos de antigüedad');
