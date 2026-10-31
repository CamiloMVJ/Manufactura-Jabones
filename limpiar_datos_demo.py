"""Elimina datos identificados de la carga antigua, conservando operaciones y catálogo."""
import argparse
import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from sqlalchemy import MetaData, select, func, delete, text
from app.core.config import BASE_DIR
from app.db.database import engine, SessionLocal
from app.models.erp_models import Lot, StockLocation, InventoryMovement, Product, Client, Supplier, AuditLog

PLACEHOLDER_SUPPLIERS = (
    'Proveedor de bases por definir',
    'Proveedor de fragancias por definir',
    'Proveedor de empaques por definir',
)


def referencing_records(db, metadata, target_table, record_id, exclude=()):
    references = []
    for table in metadata.tables.values():
        if table.name in exclude:
            continue
        for column in table.columns:
            for fk in column.foreign_keys:
                if fk.column.table.name == target_table and fk.column.name == 'id':
                    count = db.scalar(select(func.count()).select_from(table).where(column == record_id))
                    if count:
                        references.append(f'{table.name}.{column.name}: {count}')
    return references


def clean_demo(apply=True):
    report = {'aplicado': apply, 'lotes_eliminados': [], 'movimientos_eliminados': 0,
              'ubicaciones_eliminadas': 0, 'clientes_eliminados': [],
              'proveedores_eliminados': [], 'conservados': []}
    with SessionLocal() as db:
        try:
            if db.bind.dialect.name == 'sqlite':
                db.execute(text('BEGIN IMMEDIATE' if apply else 'BEGIN'))
            metadata = MetaData()
            metadata.reflect(bind=db.connection())
            lots = db.query(Lot).filter(Lot.lot_number.startswith('DEMO-')).order_by(Lot.id).all()
            for lot in lots:
                reason = None
                links = referencing_records(db, metadata, 'lots', lot.id, exclude=('stock_locations', 'inventory_movements'))
                movements = db.query(InventoryMovement).filter_by(lot_id=lot.id).all()
                locations = db.query(StockLocation).filter_by(lot_id=lot.id).all()
                product = db.get(Product, lot.product_id)
                if not (lot.notes or '').startswith('Existencia ficticia para practicar'):
                    reason = 'No coincide con el origen de la carga antigua conocida.'
                elif links:
                    reason = 'Tiene operaciones asociadas: ' + '; '.join(links)
                elif not math.isfinite(lot.current_quantity) or lot.current_quantity < 0 or not float(lot.current_quantity).is_integer():
                    reason = 'La cantidad no coincide con las unidades enteras de la carga original.'
                elif len(movements) != 1 or any(m.movement_type != 'adjustment' or m.notes != 'Carga ficticia de demostración' or m.product_id != lot.product_id or not math.isclose(m.quantity, lot.initial_quantity, abs_tol=1e-8) for m in movements):
                    reason = 'Tiene movimientos distintos de la entrada inicial o un origen no verificable.'
                elif not math.isclose(lot.initial_quantity, lot.current_quantity, abs_tol=1e-8):
                    reason = 'Su cantidad cambió después de la carga inicial.'
                elif any((s.reserved_quantity or 0) > 0 or s.product_id != lot.product_id for s in locations):
                    reason = 'Tiene reservas o ubicaciones que requieren revisión.'
                else:
                    all_lots = db.scalar(select(func.coalesce(func.sum(Lot.current_quantity), 0)).where(Lot.product_id == lot.product_id))
                    located = sum(s.quantity for s in locations)
                    if not product or not math.isclose(product.stock, all_lots, abs_tol=1e-8) or not math.isclose(located, lot.current_quantity, abs_tol=1e-8):
                        reason = 'El stock agregado, los lotes y las ubicaciones no coinciden.'
                if reason:
                    report['conservados'].append({'tipo': 'lote', 'registro': lot.lot_number, 'motivo': reason})
                    continue
                report['lotes_eliminados'].append(lot.lot_number)
                report['movimientos_eliminados'] += len(movements)
                report['ubicaciones_eliminadas'] += len(locations)
                # Se aplican también en la vista previa, dentro de una transacción que siempre se revierte.
                product.stock -= int(lot.current_quantity)
                db.execute(delete(StockLocation).where(StockLocation.lot_id == lot.id))
                db.execute(delete(InventoryMovement).where(InventoryMovement.lot_id == lot.id))
                db.delete(lot)
                db.flush()
            for client in db.query(Client).filter_by(name='Cliente de prueba', email='cliente@example.test').all():
                links = referencing_records(db, metadata, 'clients', client.id)
                if links or any((client.contact, client.address)):
                    report['conservados'].append({'tipo': 'cliente', 'registro': client.name, 'motivo': 'Tiene operaciones asociadas: ' + '; '.join(links) if links else 'El contacto original fue completado; se conserva.'})
                else:
                    report['clientes_eliminados'].append(client.name)
                    db.delete(client)
            for supplier in db.query(Supplier).filter(Supplier.name.in_(PLACEHOLDER_SUPPLIERS)).all():
                links = referencing_records(db, metadata, 'suppliers', supplier.id)
                if links or any((supplier.tax_id, supplier.contact_name, supplier.email, supplier.phone, supplier.address)):
                    report['conservados'].append({'tipo': 'proveedor', 'registro': supplier.name, 'motivo': 'Tiene registros asociados: ' + '; '.join(links) if links else 'El proveedor original fue completado; se conserva.'})
                else:
                    report['proveedores_eliminados'].append(supplier.name)
                    db.delete(supplier)
            if apply:
                removed = len(report['lotes_eliminados']) + len(report['clientes_eliminados']) + len(report['proveedores_eliminados'])
                if removed:
                    db.add(AuditLog(username='limpieza_local', action='DELETE_LEGACY_DEMO', module='configuracion', record_reference='limpiar_datos_demo.py', after_state=json.dumps(report, ensure_ascii=False)))
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise
    return report


def existing_database_path():
    if engine.url.get_backend_name() != 'sqlite':
        raise ValueError('Este comando de limpieza está preparado para SQLite.')
    if engine.url.database in (None, ':memory:'):
        raise ValueError('Se necesita una base SQLite persistente existente.')
    database = Path(engine.url.database)
    if not database.is_file():
        raise ValueError('No existe la base configurada. Ejecuta el script dentro del proyecto instalado.')
    return database


def backup_database():
    database = existing_database_path()
    directory = BASE_DIR / 'backups'
    directory.mkdir(exist_ok=True)
    backup = directory / ('antes-limpiar-demo-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite')
    with sqlite3.connect(str(database)) as source, sqlite3.connect(str(backup)) as target:
        source.backup(target)
        result = target.execute('PRAGMA integrity_check').fetchone()[0]
        if result != 'ok':
            raise ValueError('El respaldo no superó la comprobación de integridad; no se elimina ningún dato.')
    return backup


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Elimina lotes DEMO sin uso y contactos iniciales sin operaciones.')
    parser.add_argument('--ver', action='store_true', help='Mostrar qué se eliminaría sin guardar cambios.')
    args = parser.parse_args()
    try:
        existing_database_path()
        if not args.ver:
            backup = backup_database()
            print(f'Respaldo creado: {backup}')
        result = clean_demo(apply=not args.ver)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
