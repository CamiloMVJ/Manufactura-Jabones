import io
from typing import List, Dict, Any
from datetime import datetime

try:
    import pandas as pd
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
except ImportError:
    pd = None
    print("AVISO: Pandas o ReportLab no están instalados.")

class DataExporter:
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> io.BytesIO:
        if not data or pd is None: return io.BytesIO(b"")
        df = pd.DataFrame(data)
        output = io.BytesIO()
        # Index=False para no incluir el número de fila
        df.to_csv(output, index=False)
        output.seek(0)
        return output

    @staticmethod
    def to_pdf(data: List[Dict[str, Any]], title: str) -> io.BytesIO:
        if pd is None: return io.BytesIO(b"")
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
        
        if data:
            headers = list(data[0].keys())
            # Convertir datos a strings para evitar errores
            table_data = [headers] + [[str(row.get(h, "")) for h in headers] for row in data]
            
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No hay datos para mostrar.", styles['Normal']))
        
        doc.build(elements)
        output.seek(0)
        return output
