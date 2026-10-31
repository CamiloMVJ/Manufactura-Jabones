import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class EncodingTests(unittest.TestCase):
    def test_repair_text(self):
        from reparar_textos import repair_text
        for original in ['Jabón cítrico 100 g [u]', 'Sales de baño', 'Jabonera de bambú [u]']:
            for encoding in ['cp1252', 'latin1']:
                wrong = original.encode('utf-8').decode(encoding)
                self.assertEqual(repair_text(wrong), original)
            self.assertEqual(repair_text(original), original)
        self.assertEqual(repair_text(None), None)

    def test_database_preserves_identity_and_stock(self):
        from app.db.database import Base
        from app.models.erp_models import Product
        from reparar_textos import repair
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'encoding.sqlite'
            engine = create_engine('sqlite:///' + str(path))
            Base.metadata.create_all(engine)
            sessions = sessionmaker(bind=engine)
            correct = 'Jabón cítrico 100 g [u]'
            with sessions() as db:
                db.add(Product(id=1,name=correct.encode('utf-8').decode('cp1252'),category='Jabones',stock=42,price=85))
                db.commit()
            with patch('reparar_textos.engine',engine), patch('reparar_textos.SessionLocal',sessions):
                repair()
                repair()
            with sessions() as db:
                row = db.get(Product,1)
                self.assertEqual(row.name,correct)
                self.assertEqual(row.stock,42)
                self.assertEqual(row.price,85)
                self.assertEqual(db.query(Product).count(),1)
            self.assertEqual(len(list(Path(tmp).glob('*.backup-textos-*'))),2)
            engine.dispose()
