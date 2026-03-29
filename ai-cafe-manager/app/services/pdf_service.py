from fpdf import FPDF
from datetime import datetime
import os

class POService(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 18)
        self.cell(0, 10, 'AIBO Cafe Manager', align='C', 
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'I', 11)
        self.cell(0, 8, 'Automated Purchase Order (System Generated)', align='C', 
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Dispatched by AIBO Agentic Intelligence', align='C')

def generate_po_pdf(vendor: dict, items: list, order_id: str) -> str:
    """Generates a professional PDF for a Purchase Order and returns the filepath."""
    pdf = POService()
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 12)
    v_name = vendor.get('name', 'Wholesale Partner')
    pdf.cell(0, 8, f"Supplier: {v_name}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 6, f"Contact: {vendor.get('contact_name', 'Sales/Distribution')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Issue Date: {datetime.utcnow().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Order Ref: #{order_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(90, 10, "Ingredient / Material", border=1, fill=True)
    pdf.cell(40, 10, "Auth. Quantity", border=1, fill=True)
    pdf.cell(60, 10, "Urgency", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    
    # Table Body
    pdf.set_font("helvetica", '', 11)
    for item in items:
        pdf.cell(90, 10, str(item['name']), border=1)
        qty_str = f"{item['qty']:.1f} {item.get('unit', '')}"
        pdf.cell(40, 10, qty_str, border=1)
        pdf.cell(60, 10, "CRITICAL (<= 2 Days Runway)", border=1, new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(15)
    pdf.set_font("helvetica", 'I', 11)
    pdf.multi_cell(0, 10, "This order was mathematically optimized and authorized by the AIBO prediction engine based on real-time burn rates. Please process immediately. Do not exceed authorized quantities without admin override.")
    
    os.makedirs("data/sync/orders", exist_ok=True)
    filepath = f"data/sync/orders/AIBO_PO_{order_id}.pdf"
    pdf.output(filepath)
    return filepath
