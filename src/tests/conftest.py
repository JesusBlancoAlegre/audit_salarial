import pytest
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import BigInteger, SmallInteger

@compiles(BigInteger, 'sqlite')
def compile_bigint_sqlite(type_, compiler, **kw):
    return "INTEGER"

@compiles(SmallInteger, 'sqlite')
def compile_smallint_sqlite(type_, compiler, **kw):
    return "INTEGER"

from audit_salarial_app import create_app
from audit_salarial_app.extensions import db

@pytest.fixture
def app():
    # Creamos la app con configuración de test
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
