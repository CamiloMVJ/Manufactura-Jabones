import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class CleanupTests(unittest.TestCase):
    def setUp(self):
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base
        import configurar_jaboneria as original
        import cargar_datos_iniciales as initial
        import limpiar_datos_demo as cleanup
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.tmp.name)/'cleanup.sqlite'))
        @event.listens_for(self.engine,'connect')
        def foreign_keys(connection,_): connection.execute('PRAGMA foreign_keys=ON')
        self.sessions = sessionmaker(bind=self.engine,autoflush=False)
        self.cleanup = cleanup
        self.initial = initial
        self.patches = []
        for module in (original, initial):
            self.patches.extend([patch.object(module,'SessionLocal',self.sessions),patch.object(module,'init_db',lambda:Base.metadata.create_all(self.engine))])
        self.patches.append(patch.object(cleanup,'SessionLocal',self.sessions))
        for p in self.patches:p.start()
        original.configure(demo=True)

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.engine.dispose()
        self.tmp.cleanup()

    def test_removes_only_unused_legacy_records_and_reconciles_stock(self):
        from app.models.erp_models import Lot, Product, StockLocation, Client, Supplier, User
        self.initial.load_initial_data()
        with self.sessions() as db:
            expected = db.query(Lot).filter(Lot.lot_number.startswith('DEMO-')).count()
            normal_ids = [r.id for r in db.query(Lot).filter(Lot.lot_number.startswith('AP-'))]
            db.add(User(username='admin-preservado',email='admin@example.test',role='administrador',hashed_password='stored'))
            db.commit()
        report = self.cleanup.clean_demo()
        self.assertEqual(len(report['lotes_eliminados']),expected)
        self.assertEqual(len(report['clientes_eliminados']),1)
        self.assertEqual(len(report['proveedores_eliminados']),3)
        with self.sessions() as db:
            self.assertEqual(db.query(Product).count(),34)
            self.assertEqual(db.query(Client).count(),24)
            self.assertEqual(db.query(Supplier).count(),8)
            self.assertEqual(db.query(User).count(),1)
            self.assertEqual([r.id for r in db.query(Lot).order_by(Lot.id)],normal_ids)
            for p in db.query(Product):
                self.assertEqual(p.stock,sum(l.current_quantity for l in db.query(Lot).filter_by(product_id=p.id)))
                self.assertEqual(p.stock,sum(s.quantity for s in db.query(StockLocation).filter_by(product_id=p.id)))
        second = self.cleanup.clean_demo()
        self.assertEqual(second['lotes_eliminados'],[])
        self.assertEqual(second['clientes_eliminados'],[])

    def test_preview_does_not_write(self):
        from app.models.erp_models import Lot, AuditLog
        with self.sessions() as db:count=db.query(Lot).count()
        preview = self.cleanup.clean_demo(apply=False)
        self.assertEqual(len(preview['lotes_eliminados']),count)
        with self.sessions() as db:
            self.assertEqual(db.query(Lot).count(),count)
            self.assertEqual(db.query(AuditLog).count(),0)

    def test_used_lot_and_client_with_orders_are_preserved(self):
        from app.models.erp_models import Lot, Product, Order, OrderItem, Client
        from app.services.soap_operations import consume
        with self.sessions() as db:
            lot=db.query(Lot).filter_by(lot_number='DEMO-JABONERA').one()
            product=lot.product_id
            client=db.query(Client).filter_by(email='cliente@example.test').one()
            order=Order(client_id=client.id,status='pendiente',total_amount=90)
            db.add(order);db.flush()
            allocations=consume(db,product,1,'PED-'+str(order.id))
            db.add(OrderItem(order_id=order.id,product_id=product,lot_id=allocations[0][0],quantity=1,subtotal=90))
            db.commit()
        report=self.cleanup.clean_demo()
        with self.sessions() as db:
            self.assertEqual(db.query(Lot).filter_by(lot_number='DEMO-JABONERA').count(),1)
            self.assertEqual(db.get(Product,product).stock,19)
            self.assertEqual(db.query(OrderItem).count(),1)
            self.assertEqual(db.query(Client).filter_by(email='cliente@example.test').count(),1)
        self.assertTrue(any(r['registro']=='DEMO-JABONERA' for r in report['conservados']))

    def test_unknown_demo_prefix_is_not_enough_to_delete(self):
        from app.models.erp_models import Lot, Product
        with self.sessions() as db:
            product=db.query(Product).first()
            db.add(Lot(lot_number='DEMO-MANUAL',product_id=product.id,initial_quantity=0,current_quantity=0,notes='Registro manual que debe conservarse'))
            db.commit()
        report=self.cleanup.clean_demo()
        self.assertTrue(any(r['registro']=='DEMO-MANUAL' for r in report['conservados']))
        with self.sessions() as db:self.assertEqual(db.query(Lot).filter_by(lot_number='DEMO-MANUAL').count(),1)

    def test_completed_placeholder_contacts_are_preserved(self):
        from app.models.erp_models import Client, Supplier
        with self.sessions() as db:
            db.query(Client).filter_by(email='cliente@example.test').one().contact='Contacto añadido por el usuario'
            db.query(Supplier).filter_by(name='Proveedor de bases por definir').one().email='compras@example.test'
            db.commit()
        report=self.cleanup.clean_demo()
        self.assertEqual(report['clientes_eliminados'],[])
        self.assertEqual(len(report['proveedores_eliminados']),2)
        with self.sessions() as db:
            self.assertEqual(db.query(Client).count(),1)
            self.assertEqual(db.query(Supplier).count(),1)

    def test_exception_rolls_back_lots_and_stock(self):
        from app.models.erp_models import Lot, Product, AuditLog
        with self.sessions() as db:
            before_lots=db.query(Lot).count()
            before_stock={p.id:p.stock for p in db.query(Product)}
        original=self.cleanup.referencing_records
        def fail_later(db,metadata,target,record_id,exclude=()):
            if target=='suppliers':raise RuntimeError('Fallo simulado después de procesar lotes')
            return original(db,metadata,target,record_id,exclude)
        with patch.object(self.cleanup,'referencing_records',side_effect=fail_later):
            with self.assertRaises(RuntimeError):self.cleanup.clean_demo()
        with self.sessions() as db:
            self.assertEqual(db.query(Lot).count(),before_lots)
            self.assertEqual({p.id:p.stock for p in db.query(Product)},before_stock)
            self.assertEqual(db.query(AuditLog).count(),0)

    def test_backup_is_readable_and_preserves_original(self):
        import sqlite3
        with patch.object(self.cleanup,'engine',self.engine),patch.object(self.cleanup,'BASE_DIR',Path(self.tmp.name)):
            backup=self.cleanup.backup_database()
        with sqlite3.connect(str(backup)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertGreater(db.execute('SELECT COUNT(*) FROM lots').fetchone()[0],0)

if __name__=='__main__': unittest.main()
