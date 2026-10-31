"""Carga ampliada y aditiva de Pura Cocos. No elimina ni sustituye registros existentes."""
import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import text
from app.core.config import BASE_DIR
from app.db.database import init_db, SessionLocal, engine
from app.models.erp_models import (
    Product, Supplier, Client, Employee, WorkCenter, Warehouse, Location,
    BillOfMaterial, BOMItem, Routing, RoutingOperation, Lot, StockLocation,
    InventoryMovement, InitialDataBatch, AuditLog,
)


def read_inputs():
    catalog = json.loads((BASE_DIR / 'data/catalogo.json').read_text(encoding='utf-8'))
    business = json.loads((BASE_DIR / 'data/negocio_inicial.json').read_text(encoding='utf-8'))
    return catalog, business


def unique(db, model, **criteria):
    rows = db.query(model).filter_by(**criteria).all()
    if len(rows) > 1:
        raise ValueError(f'Hay registros duplicados en {model.__tablename__}: {criteria}. Resuélvelos antes de cargar.')
    return rows[0] if rows else None


def get_or_add(db, model, criteria, values, counts):
    existing = unique(db, model, **criteria)
    if existing is not None:
        return existing
    row = model(**values)
    db.add(row)
    db.flush()
    counts[model.__tablename__] += 1
    return row


def validate(catalog, business):
    names = [r[1] for r in catalog['insumos']] + [p['nombre'] for p in catalog['productos']]
    skus = [r[0] for r in catalog['insumos']] + [p['sku'] for p in catalog['productos']]
    if len(set(names)) != len(names) or len(set(skus)) != len(skus):
        raise ValueError('El catálogo contiene nombres o códigos repetidos.')
    known = set(skus)
    for product in catalog['productos']:
        if 'ingredientes' not in product:
            continue
        if product['lote_base'] <= 0 or not product['ingredientes']:
            raise ValueError('Receta sin rendimiento o componentes válidos.')
        for component, qty in product['ingredientes']:
            if component not in known or component == product['sku'] or not math.isfinite(float(qty)) or qty <= 0:
                raise ValueError(f'Componente inválido en {product["sku"]}.')
    warehouse_codes = {'MP', 'PT'}
    locations = {(p['almacen'], p['code']) for p in business['ubicaciones']}
    seen = set()
    for item in business['inventario']:
        qty = item['cantidad']
        if item['sku'] in seen or item['sku'] not in known:
            raise ValueError('Código de inventario repetido o inexistente.')
        seen.add(item['sku'])
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 0:
            raise ValueError('Las existencias iniciales deben ser enteras no negativas.')
        if item['almacen'] not in warehouse_codes or (item['almacen'], item['ubicacion']) not in locations:
            raise ValueError('Almacén o ubicación inicial inválidos.')
        if item['estado'] not in ('released', 'quarantine'):
            raise ValueError('El lote inicial debe estar liberado o en cuarentena.')
        if item.get('vencimiento') and date.fromisoformat(item['vencimiento']) < date.today():
            raise ValueError('No se carga inventario inicial vencido.')


def load_initial_data(include_inventory=True, catalog=None, business=None):
    if catalog is None or business is None:
        catalog, business = read_inputs()
    validate(catalog, business)
    payload_hash = hashlib.sha256(json.dumps(business['inventario'], sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    init_db()
    counts = Counter()
    skipped = []
    inventory_state = 'omitido por opción'
    with SessionLocal() as db:
        try:
            if db.bind.dialect.name == 'sqlite':
                db.execute(text('BEGIN IMMEDIATE'))
            warehouses = {}
            for code, name in [('MP', 'Insumos y empaques'), ('PT', 'Productos terminados')]:
                warehouses[code] = get_or_add(db, Warehouse, {'code': code}, {'code': code, 'name': name, 'address': 'Managua'}, counts)
            locations = {}
            for data in business['ubicaciones']:
                values = {k: v for k, v in data.items() if k != 'almacen'}
                values['warehouse_id'] = warehouses[data['almacen']].id
                locations[data['code']] = get_or_add(db, Location, {'warehouse_id': values['warehouse_id'], 'code': values['code']}, values, counts)
            centers = {}
            for data in business['centros']:
                centers[data['code']] = get_or_add(db, WorkCenter, {'code': data['code']}, data, counts)
            for data in business['proveedores']:
                get_or_add(db, Supplier, {'name': data['name']}, data, counts)
            for data in business['clientes']:
                get_or_add(db, Client, {'email': data['email']}, data, counts)
            for data in business['empleados']:
                get_or_add(db, Employee, {'code': data['code']}, data, counts)
            products = {}
            for sku, name, category, price, _ in catalog['insumos']:
                products[sku] = get_or_add(db, Product, {'name': name}, {'name': name, 'category': category, 'price': price, 'stock': 0}, counts)
            for data in catalog['productos']:
                products[data['sku']] = get_or_add(db, Product, {'name': data['nombre']}, {'name': data['nombre'], 'category': data['categoria'], 'price': data['precio'], 'stock': 0}, counts)
            for data in catalog['productos']:
                if 'ingredientes' not in data:
                    continue
                product = products[data['sku']]
                bom_code, route_code = 'REC-' + data['sku'], 'RUTA-' + data['sku']
                bom = unique(db, BillOfMaterial, code=bom_code)
                if bom and bom.finished_product_id != product.id:
                    raise ValueError(f'El código {bom_code} ya corresponde a otro producto.')
                if not bom:
                    bom = BillOfMaterial(code=bom_code, finished_product_id=product.id, quantity=data['lote_base'], version='1.0', notes='Fórmula de catálogo propuesta; validar fichas técnicas, peso neto y rendimiento.')
                    db.add(bom)
                    db.flush()
                    counts['bills_of_material'] += 1
                    for sku, qty in data['ingredientes']:
                        db.add(BOMItem(bom_id=bom.id, component_product_id=products[sku].id, quantity=qty, scrap_percentage=0))
                        counts['bom_items'] += 1
                route = unique(db, Routing, code=route_code)
                if route and route.finished_product_id != product.id:
                    raise ValueError(f'El código {route_code} ya corresponde a otro producto.')
                if not route:
                    route = Routing(code=route_code, name=data['nombre'], finished_product_id=product.id, description='Procedimiento de Pura Cocos; consultar Recetas y costos.')
                    db.add(route)
                    db.flush()
                    counts['routings'] += 1
                    for index, step in enumerate(data['pasos'], 1):
                        center = 'ENS-01' if data['categoria'] == 'Kits' else 'ENV-01' if index == len(data['pasos']) else 'PESA-01' if index == 1 else 'FUND-01' if data['categoria'] == 'Jabones' else 'MESA-01'
                        db.add(RoutingOperation(routing_id=route.id, sequence=index * 10, work_center_id=centers[center].id, operation_name=step[:200], standard_duration_minutes=15))
                        counts['routing_operations'] += 1
            if include_inventory:
                previous = unique(db, InitialDataBatch, code=business['version'])
                if previous:
                    if previous.payload_hash != payload_hash:
                        raise ValueError('La apertura ya fue aplicada con otras cantidades. Registra las nuevas entradas en Compras; no recargues el inventario.')
                    inventory_state = 'ya aplicado; no se repitió'
                else:
                    inventory_state = 'aplicado'
                    for data in business['inventario']:
                        product = products[data['sku']]
                        # No sumar apertura sobre existencias ni historial de lotes de una instalación anterior.
                        has_lots = db.query(Lot.id).filter_by(product_id=product.id).first() is not None
                        has_locations = db.query(StockLocation.id).filter_by(product_id=product.id).first() is not None
                        has_moves = db.query(InventoryMovement.id).filter_by(product_id=product.id).first() is not None
                        if product.stock or has_lots or has_locations or has_moves:
                            skipped.append(data['sku'])
                            continue
                        qty = data['cantidad']
                        if not qty:
                            continue
                        lot_number = f'AP-{date.today():%Y%m%d}-{data["sku"]}'
                        lot = Lot(lot_number=lot_number, product_id=product.id, initial_quantity=qty, current_quantity=qty, status=data['estado'], expiry_date=date.fromisoformat(data['vencimiento']) if data.get('vencimiento') else None, notes='Apertura desde data/negocio_inicial.json; cantidades propuestas, pendientes de contrastar con conteo físico.')
                        db.add(lot)
                        db.flush()
                        product.stock = qty
                        db.add(StockLocation(product_id=product.id, warehouse_id=warehouses[data['almacen']].id, location_id=locations[data['ubicacion']].id, lot_id=lot.id, quantity=qty, reserved_quantity=0))
                        db.add(InventoryMovement(code=f'INI-{date.today():%Y%m%d}-{data["sku"]}', product_id=product.id, lot_id=lot.id, movement_type='adjustment', dest_warehouse_id=warehouses[data['almacen']].id, dest_location_id=locations[data['ubicacion']].id, quantity=qty, reference_doc_type='initial_inventory', reference_doc_id=business['version'], notes='Apertura; no representa una factura de compra ni una producción registrada.'))
                        counts['lots'] += 1
                    db.add(InitialDataBatch(code=business['version'], payload_hash=payload_hash, origin=business['origen'], summary=json.dumps({'created_lots': counts['lots'], 'preserved_skus': skipped}, ensure_ascii=False)))
            if counts or inventory_state == 'aplicado':
                db.add(AuditLog(username='carga_inicial', action='INITIAL_DATA_LOAD', module='configuracion', record_reference=business['version'], after_state=json.dumps(dict(counts)), before_state=None))
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {'creados': dict(counts), 'inventario': inventory_state, 'existencias_preservadas': skipped}


def backup_database():
    if engine.url.get_backend_name() != 'sqlite' or engine.url.database in (None, ':memory:'):
        return None
    database = Path(engine.url.database)
    if not database.exists():
        return None
    directory = BASE_DIR / 'backups'
    directory.mkdir(exist_ok=True)
    destination = directory / f'apertura-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite'
    with sqlite3.connect(str(database)) as source, sqlite3.connect(str(destination)) as target:
        source.backup(target)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carga ampliada de datos iniciales de Pura Cocos.')
    parser.add_argument('--sin-stock', action='store_true', help='Cargar únicamente catálogos; no crear lotes ni existencias.')
    args = parser.parse_args()
    try:
        catalog, business = read_inputs()
        validate(catalog, business)
        backup = backup_database()
        if backup:
            print(f'Respaldo creado: {backup}')
        print(business['origen'])
        result = load_initial_data(include_inventory=not args.sin_stock, catalog=catalog, business=business)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
