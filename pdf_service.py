import io
import re
import zipfile
from jinja2 import Template
from weasyprint import HTML
from num2words import num2words
from config import COMPANIES, get_last_serial, update_serial, BASE_CSS

# --- TEMPLATES ---
TEMPLATE_GST = """
<html><head><style>{{ css }}</style></head><body>
    <div class="title-box"><div class="main-title gst-title">SALES TAX INVOICE</div></div>
    <div class="center" style="font-size: 10pt; margin-bottom: 15px;">(Under Section 23 of S.Tax Act 1990)</div>
    <table style="width: 100%; margin-bottom: 5px;">
        <tr><td class="bold" style="width: 20%; text-decoration: underline; display:inline-block;">ORIGINAL</td><td style="width: 50%;"></td><td class="right bold" style="width: 15%;">Serial No.</td><td class="center" style="border: 1px solid black; width: 15%;">{{ serial }}</td></tr>
        <tr><td>Time of Supply:</td><td></td><td class="right bold">Date:</td><td class="center" style="border: 1px solid black;">{{ date }}</td></tr>
    </table>
    <table class="gst-info-table">
        <tr>
            <td class="gst-info-label">Supplier's Name:</td><td width="35%" class="gst-partition">{{ comp.header_title }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Buyer's Name:</td><td width="35%">{{ buyer_name }}</td>
        </tr>
        <tr>
            <td class="gst-info-label">Address:</td><td class="gst-partition">{{ comp.address|safe }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Address:</td><td>{{ dept }}</td>
        </tr>
        <tr>
            <td class="gst-info-label">Telephone:</td><td class="gst-partition">{{ comp.phone }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">N.T.N No.</td><td></td>
        </tr>
        <tr>
            <td class="gst-info-label">N.T.N No.</td><td class="gst-partition">{{ comp.ntn }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Terms of Sales:</td><td></td>
        </tr>
        <tr>
            <td class="gst-info-label">S.T.Reg No:</td><td class="gst-partition">{{ comp.strn }}</td>
            <td></td><td></td>
        </tr>
    </table>
    <table class="grid-table">
        <thead><tr><th width="8%">Quantity</th><th width="48%">Description of Goods</th><th width="12%">Value<br>Excl.S.Tax</th><th width="8%">Rate of<br>Sales Tax</th><th width="10%">Total Sales Tax<br>Payable</th><th width="14%">Value Including<br>Sales.Tax</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td><td class="v-top">{{ item.Description }}</td><td class="center v-top">{{ "{:,.0f}".format(item.val_excl) }}</td><td class="center v-top">18%</td><td class="center v-top">{{ "{:,.0f}".format(item.tax_val) }}</td><td class="center v-top">{{ "{:,.0f}".format(item.val_incl) }}</td></tr>{% endfor %}
            {% set filler_count = 20 - items|length %}
            {% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
        <tfoot><tr class="total-row"><td colspan="2" class="right">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.excl) }}</td><td class="center">18%</td><td class="center">{{ "{:,.0f}".format(totals.tax) }}</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr></tfoot>
    </table>
    <br><br><br><div style="width: 30%; border-top: 1px solid black; margin-left: auto; text-align: center;">SIGNATURE</div>
</body></html>
"""

TEMPLATE_BILL = """
<html><head><style>{{ css }}</style></head><body>
    {% if comp.template_type == 'logo' %}<div class="title-box"><div class="main-title bill-title">BILL/CASH MEMO</div></div><div class="nt-header"><div style="width: 70%;"><div class="main-title" style="font-size: 26pt; border: none;">{{ comp.header_title }}</div><div style="font-size: 9pt;">{{ comp.address|safe }}</div></div><div class="center" style="width: 30%;">{% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}<div style="font-size: 7pt; font-weight: bold; margin-top: 2px;">{{ comp.header_sub }}</div></div></div>{% else %}<div class="simple-header"><div class="main-title bill-title">BILL</div></div>{% endif %}
    <table style="width: 100%; margin-bottom: 10px;"><tr><td width="65%" class="v-top"><div class="info-row"><span class="info-label">Messers:</span><span class="info-val">{{ buyer_name }}</span></div><div class="info-row"><span class="info-label">Address:</span><span class="info-val">{{ dept }}</span></div><div class="info-row"><span class="info-label">Order No:</span><span class="info-val">{{ po_no }}</span></div></td><td width="5%"></td><td width="30%" class="v-top"><div class="info-row"><span class="info-label" style="min-width: 60px;">No.</span><span class="info-val center bold">{{ serial }}</span></div><div class="info-row"><span class="info-label" style="min-width: 60px;">Dated:</span><span class="info-val center bold">{{ date }}</span></div></td></tr></table>
    <table class="grid-table {% if comp.template_type == 'logo' %}black-header{% endif %}">
        <thead><tr><th width="6%">S.No.</th><th width="12%">QTY.</th><th width="52%">PARTICULARS</th><th width="15%">RATE</th><th width="15%">AMOUNT</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td><td class="v-top">{{ item.Description }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Rate) }}</td><td class="center v-top bold">{{ "{:,.0f}".format(item.val_incl) }}</td></tr>{% endfor %}
            {% set filler_count = 18 - items|length %}{% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
        <tfoot><tr class="total-row"><td colspan="4" class="right" style="{% if comp.template_type == 'logo' %}background:black; color:white;{% endif %}">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr></tfoot>
    </table>
    <div style="margin-top: 15px;"><span class="bold">Rupees = </span><span class="italic">{{ amount_words }}</span></div><div class="footer-row"><div></div><div class="bold right" style="margin-top: 30px;">For, {{ comp.footer_title }}</div></div>
</body></html>
"""

TEMPLATE_CHALLAN = """
<html><head><style>{{ css }}</style></head><body>
    {% if comp.template_type == 'logo' %}<div class="nt-header" style="border: none;"><div style="width: 70%;"><div class="main-title" style="font-size: 26pt; border: none;">{{ comp.header_title }}</div><div style="font-size: 8pt; font-weight: bold;">{{ comp.challan_sub }}</div></div><div class="center" style="width: 30%;">{% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}</div></div><div class="title-box" style="margin-bottom: 10px;"><div class="main-title" style="font-size: 14pt;">Delivery Challan</div></div>{% else %}<div class="simple-header"><div class="main-title bill-title">Delivery Challan</div></div>{% endif %}
    <table style="width: 100%; margin-bottom: 15px;"><tr><td width="65%" class="v-top"><div class="info-row"><span class="info-label" style="min-width: 130px;">Your Supply Order No:</span><span class="info-val">{{ po_no }}</span></div><div class="info-row"><span class="info-label" style="min-width: 130px;">Messers:</span><span class="info-val">{{ buyer_name }}</span></div><div class="info-row"><span class="info-label" style="min-width: 130px;">Address:</span><span class="info-val">{{ dept }}</span></div></td><td width="5%"></td><td width="30%" class="v-top"><div class="info-row"><span class="info-label">D.C. NO.</span><span class="info-val center bold">{{ serial }}</span></div>{% if comp.template_type == 'simple' %}<div class="info-row"><span class="info-label">Date:</span><span class="info-val center bold">{{ date }}</span></div>{% endif %}</td></tr></table>
    <table class="grid-table">
        <thead><tr><th width="6%">S.No.</th><th width="14%">QUANTITY</th><th width="80%">PARTICULARS</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td><td class="v-top">{{ item.Description }}</td></tr>{% endfor %}
            {% set filler_count = 18 - items|length %}{% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
    </table>
    <div class="center italic bold" style="margin-top: 20px; border: 1px solid black; padding: 5px;">Received above mentioned Goods checked and found to be good condition</div>
    <br><br><br><div class="footer-row signature-spacing"><div class="sig-line">Receiver's Signature</div><div class="sig-line">Checked by:</div><div class="sig-line">For {{ comp.footer_title }}</div></div>
</body></html>
"""

def clean_float(value):
    if value is None: return 0.0
    try:
        if isinstance(value, str): return float(re.sub(r'[^\d.]', '', value))
        return float(value)
    except: return 0.0

def get_css(template_mode="standard"):
    # Builds CSS based on template mode
    css = BASE_CSS
    if template_mode == "letterhead":
        css += "@page { size: A4; margin-top: 2.5in; margin-bottom: 1.5in; margin-left: 1cm; margin-right: 1cm; }"
    else:
        css += "@page { size: A4; margin: 0.5cm 1cm; }"
    return css

def generate_pdf_package(comp_key, dept_name, buyer_name, items_data, po_no, po_date, logo_b64, manual_serial):
    # 1. Handle Serial Number
    if manual_serial and manual_serial.strip():
        final_serial = manual_serial.zfill(4)
        update_serial(comp_key, dept_name, final_serial)
    else:
        update_serial(comp_key, dept_name)
        final_serial = f"{get_last_serial(comp_key, dept_name):04d}"
        
    comp_data = COMPANIES[comp_key]
    processed_items = []
    t_excl = 0; t_tax = 0; t_incl = 0
    
    # 2. Process Data & Calculate (Safely)
    for item in items_data:
        qty = clean_float(item.get('Qty', 0))
        rate = clean_float(item.get('Rate', 0))
        desc = item.get('Description', '')
        
        val_incl = qty * rate
        val_excl = val_incl / 1.18
        tax = val_incl - val_excl
        
        t_excl += val_excl; t_tax += tax; t_incl += val_incl
        
        processed_items.append({
            'Qty': qty, 'Description': desc, 'Rate': rate,
            'val_excl': val_excl, 'tax_val': tax, 'val_incl': val_incl
        })

    totals = {'excl': t_excl, 'tax': t_tax, 'incl': t_incl}
    try: amount_words = f"Rupees {num2words(int(round(t_incl))).title().replace('-', ' ')} Only"
    except: amount_words = "Rupees .............................................."
    
    # 3. Determine Styles
    is_simple = (comp_data['template_type'] == 'simple')
    gst_css = get_css("standard")
    doc_css = get_css("letterhead" if is_simple else "standard")
    
    # 4. Create Context
    context = {
        'comp': comp_data, 'dept': dept_name, 'buyer_name': buyer_name, 
        'items': processed_items, 'po_no': po_no, 'date': po_date, 
        'serial': final_serial, 'totals': totals, 'amount_words': amount_words, 
        'logo_b64': logo_b64
    }
    
    # 5. Generate Files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
        zf.writestr(f"1_GST_{final_serial}.pdf", HTML(string=Template(TEMPLATE_GST).render(**context, css=gst_css)).write_pdf())
        zf.writestr(f"2_Bill_{final_serial}.pdf", HTML(string=Template(TEMPLATE_BILL).render(**context, css=doc_css)).write_pdf())
        zf.writestr(f"3_Challan_{final_serial}.pdf", HTML(string=Template(TEMPLATE_CHALLAN).render(**context, css=doc_css)).write_pdf())
        
    return zip_buffer.getvalue(), final_serial
