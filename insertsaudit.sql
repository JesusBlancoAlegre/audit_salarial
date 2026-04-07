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

INSERT INTO usuario (rol_id, email, password_hash, nombre, activo) VALUES
(1, 'admin@admin.com', 'scrypt:32768:8:1$4bdeUOYDwXZa1m4U$74b278f05412ca144fdfeb5c69ff1f835695d834daa00c504c06db52f2c0e24816a1ab85fc4ee512379dee4a837c17dc89422a73c7d5926bc71c03ad8d5463a3', 'Administrador', 1);