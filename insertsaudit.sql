USE audit_salarial;

-- ─── ROLES ───────────────────────────────────────────────────────────────────
INSERT IGNORE INTO rol (nombre, descripcion) VALUES
('ADMIN',   'Administrador del sistema'),
('AUDITOR', 'Auditor interno/externo'),
('CLIENTE', 'Empresa cliente');

-- ─── DIMENSIONES ─────────────────────────────────────────────────────────────
INSERT IGNORE INTO dimension (codigo, nombre, descripcion) VALUES
('GLOBAL',            'Brecha Global',              'Brecha total de la empresa'),
('DEPARTAMENTO',      'Por departamento',            'Comparación por departamento'),
('PUESTO',            'Por puesto',                  'Comparación por puesto'),
('CATEGORIA',         'Por categoría/grupo',         'Comparación por categoría'),
('CONTRATO',          'Por tipo de contrato',        'Indefinido/temporal/etc.'),
('JORNADA',           'Por jornada',                 'Completa/parcial'),
('ANTIGUEDAD',        'Por antigüedad',              'Rangos de antigüedad'),
('GRUPO_PROFESIONAL', 'Grupo Profesional',           'Agrupación por nivel/categoría');

-- ─── SECTOR GENÉRICO (requerido por Empresa) ─────────────────────────────────
INSERT IGNORE INTO sector (id, codigo, nombre) VALUES
(1, 'GENERAL', 'General / Sin sector específico');

-- ─── EMPRESA DE DEMO ─────────────────────────────────────────────────────────
INSERT IGNORE INTO empresa (id, cif, nombre, num_trabajadores, email_contacto, activa) VALUES
(1, 'A12345678', 'Empresa Demo S.L.', 50, 'contacto@demo.com', 1);

-- ─── USUARIOS (contraseñas hasheadas con Werkzeug pbkdf2:sha256) ──────────────
-- ADMIN   → admin@admin.com     / Admin1234!
-- AUDITOR → auditor@demo.com    / Auditor1!
-- CLIENTE → cliente@demo.com    / Cliente1!
--
-- Los hashes se generan con:
--   from werkzeug.security import generate_password_hash
--   generate_password_hash('Admin1234!')
-- ¡NO cambies el hash manualmente!
-- Si necesitas restablecer la contraseña usa el script scratch/create_users.py

-- Insertamos con hash vacío; el script Python set_password() los sobreescribe.
-- Para inserción directa en BBDD de demo se usan hashes pre-generados:
--   pbkdf2:sha256:600000$ es el formato de Werkzeug 3.x

INSERT IGNORE INTO usuario (id, rol_id, empresa_id, email, password_hash, nombre, apellidos, activo)
VALUES
-- ADMIN: admin@admin.com / Admin1234!
(1, (SELECT id FROM rol WHERE nombre='ADMIN'),
    NULL,
    'admin@admin.com',
    'pbkdf2:sha256:600000$salt_admin_demo$0000000000000000000000000000000000000000000000000000000000000000',
    'Administrador', 'Sistema', 1, 0),

-- AUDITOR: auditor@demo.com / Auditor1!
(2, (SELECT id FROM rol WHERE nombre='AUDITOR'),
    NULL,
    'auditor@demo.com',
    'pbkdf2:sha256:600000$salt_audit_demo$0000000000000000000000000000000000000000000000000000000000000000',
    'Auditor', 'Demo', 1, 0),

-- CLIENTE: cliente@demo.com / Cliente1! — vinculado a la empresa demo
(3, (SELECT id FROM rol WHERE nombre='CLIENTE'),
    1,
    'cliente@demo.com',
    'pbkdf2:sha256:600000$salt_clien_demo$0000000000000000000000000000000000000000000000000000000000000000',
    'Cliente', 'Demo', 1, 0);

-- NOTA: Los hashes anteriores son placeholders. Para generar credenciales reales
-- ejecuta después: python -m scratch.create_users
-- Ese script sobreescribe los hashes con valores válidos generados por Werkzeug.
