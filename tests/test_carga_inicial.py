"""La apertura es aditiva, transaccional y no se vuelve a sumar al reiniciar."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class InitialDataTests(unittest.TestCase):
    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base
        import cargar_datos_iniciales as loader
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.temp.name) / 'initial.sqlite'))
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        self.loader = loader
        self.catalog, self.business = loader.read_inputs()
        self.patches = [patch.object(loader, 'SessionLocal', self.sessions), patch.object(loader, 'init_db', lambda: Base.metadata.create_all(self.engine))]
        for p in self.patches:
            p.start()
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.engine.dispose()
        self.temp.cleanup()

    def load(self, include_inventory=True, **kwargs):
        return self.loader.load_initial_data(include_inventory=include_inventory, catalog=self.catalog, business=kwargs.get('business', self.business))

    def test_full_load_reconciles_and_repeated_load_preserves_sales(self):
        from app.models.erp_models import Product, Client, Supplier, Employee, WorkCenter, Location, Warehouse, Lot, StockLocation, BillOfMaterial, Routing, InitialDataBatch
        from app.services.soap_operations import consume
        first = self.load()
        self.assertEqual(first['creados']['lots'], 34)
        with self.sessions() as db:
            for model, count in [(Product,34),(Client,24),(Supplier,8),(Employee,8),(WorkCenter,5),(Warehouse,2),(Location,6),(BillOfMaterial,14),(Routing,14),(Lot,34),(InitialDataBatch,1)]:
                self.assertEqual(db.query(model).count(), count, model.__name__)
            for p in db.query(Product).all():
                self.assertNotIn('DEMO', p.name)
                self.assertEqual(p.stock,sum(l.current_quantity for l in db.query(Lot).filter_by(product_id=p.id)))
                self.assertEqual(p.stock,sum(l.quantity for l in db.query(StockLocation).filter_by(product_id=p.id)))
            soap = db.query(Product).filter_by(name='Jabón de lavanda 100 g [u]').one()
            allocations = consume(db,soap.id,3,'PED-APERTURA-TEST')
            self.assertTrue(allocations)
            db.commit()
            self.assertEqual(db.get(Product,soap.id).stock,57)
        second = self.load()
        self.assertEqual(second['creados'], {})
        with self.sessions() as db:
            self.assertEqual(db.query(Product).filter_by(name='Jabón de lavanda 100 g [u]').one().stock,57)
            self.assertEqual(db.query(Lot).count(),34)
        modified = copy.deepcopy(self.business)
        modified['inventario'][0]['cantidad'] += 1
        with self.assertRaisesRegex(ValueError,'ya fue aplicada'):
            self.load(business=modified)

    def test_existing_catalog_stock_prices_and_accounts_are_preserved(self):
        from app.models.erp_models import Product, Lot, User
        with self.sessions() as db:
            db.add(Product(id=40,name='Jabón de lavanda 100 g [u]',category='Jabones',stock=123,price=79))
            db.add(User(username='personal',email='staff@example.test',hashed_password='stored-hash',role='administrador'))
            db.flush()
            db.add(Lot(lot_number='ANTERIOR-001',product_id=40,initial_quantity=123,current_quantity=123,status='released'))
            db.commit()
        result = self.load()
        self.assertIn('JAB-LAV',result['existencias_preservadas'])
        self.assertEqual(result['creados']['lots'],33)
        with self.sessions() as db:
            p = db.get(Product,40)
            self.assertEqual((p.stock,p.price),(123,79))
            self.assertEqual(db.query(User).one().username,'personal')
            self.assertEqual(db.query(Lot).filter_by(product_id=40).count(),1)

    def test_catalog_only_can_receive_inventory_once_later(self):
        from app.models.erp_models import Product, Lot, InitialDataBatch
        self.load(include_inventory=False)
        with self.sessions() as db:
            self.assertEqual(sum(p.stock for p in db.query(Product)),0)
            self.assertEqual(db.query(InitialDataBatch).count(),0)
        self.load()
        self.load()
        with self.sessions() as db:
            self.assertEqual(db.query(Lot).count(),34)
            self.assertEqual(db.query(InitialDataBatch).count(),1)

    def test_invalid_inventory_leaves_no_partial_catalog(self):
        from app.models.erp_models import Product, Client, Lot
        modified = copy.deepcopy(self.business)
        modified['inventario'][-1]['cantidad'] = -1
        with self.assertRaises(ValueError):
            self.load(business=modified)
        with self.sessions() as db:
            self.assertEqual(db.query(Product).count(),0)
            self.assertEqual(db.query(Client).count(),0)
            self.assertEqual(db.query(Lot).count(),0)

    def test_all_manufactured_products_have_usable_recipes(self):
        from app.models.erp_models import Product, BillOfMaterial
        from app.services.enterprise_service import EnterpriseService
        self.load()
        with self.sessions() as db:
            for recipe in db.query(BillOfMaterial).order_by(BillOfMaterial.id):
                self.assertTrue(recipe.items)
                service = EnterpriseService(db)
                order = service.create_production_order({'product_id':recipe.finished_product_id,'planned_quantity':int(recipe.quantity)}, 'carga-test')
                for state in ['planned','materials_reserved','in_production','quality_control']:
                    service.advance_production_order(order.id,state,'carga-test')
                service.create_quality_inspection({'product_id':recipe.finished_product_id,'production_order_id':order.id,'result':'passed','measured_value':'Registro de prueba automatizada'},'carga-test')
                service.advance_production_order(order.id,'completed','carga-test')
                self.assertEqual(order.produced_quantity,recipe.quantity)

if __name__ == '__main__':
    unittest.main()
