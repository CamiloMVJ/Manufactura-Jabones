"""Repara la lectura UTF-8 interpretada como Windows-1252 sin recargar el catálogo."""
from datetime import datetime
from pathlib import Path
import sqlite3
from app.db.database import engine, SessionLocal
from app.models.erp_models import Product, Routing, RoutingOperation


def repair_text(value):
    if not isinstance(value, str):
        return value
    for _ in range(3):
        original = value
        for encoding in ('cp1252', 'latin1'):
            try:
                fixed = value.encode(encoding).decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if fixed != value:
                value = fixed
                break
        if value == original:
            break
    return value


def repair():
    if engine.url.get_backend_name() != 'sqlite':
        raise ValueError('Esta reparación automática está preparada para SQLite.')
    database = Path(engine.url.database)
    if not database.is_file():
        raise ValueError('No existe la base configurada. Ejecuta este archivo dentro del proyecto instalado.')
    backup = database.with_name(database.name + '.backup-textos-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    with sqlite3.connect(str(database)) as source, sqlite3.connect(str(backup)) as target:
        source.backup(target)
    fields = ((Product, ('name', 'category')), (Routing, ('name', 'description')), (RoutingOperation, ('operation_name',)))
    count = 0
    with SessionLocal() as db:
        try:
            for model, names in fields:
                for row in db.query(model).all():
                    for name in names:
                        current = getattr(row, name)
                        fixed = repair_text(current)
                        if fixed != current:
                            setattr(row, name, fixed)
                            count += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(f'Campos reparados: {count}. Se conservaron IDs, existencias, recetas y ventas.')
    print(f'Respaldo: {backup.name}')


if __name__ == '__main__':
    try:
        repair()
    except ValueError as error:
        raise SystemExit(str(error))
