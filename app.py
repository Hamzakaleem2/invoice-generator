import streamlit as st
import pandas as pd
import io
import json
import os
import base64
import zipfile
import re
import cv2
import numpy as np
import shutil
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML, CSS
from num2words import num2words
import pytesseract

# --- 0. CLOUD & OCR CONFIGURATION ---
# This block automatically detects if we are on the Cloud or Local Windows
if os.name == 'nt':  # Windows
    # Update this path if your local installation is different
    possible_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(possible_path):
        pytesseract.pytesseract.tesseract_cmd = possible_path
else:  # Linux (Streamlit Cloud)
    # On Cloud, Tesseract is installed in the system path, so we don't need to specify it
    pass

# --- 1. CONFIGURATION & DATABASE ---
SERIAL_FILE = 'serial_tracker.json'

COMPANIES = {
    "M/S National Traders": {
        "template_type": "logo",
        "address": "NEAR CIVIL HOSPITAL, BHURGRI ROAD,<br>HIRABAD, HYDERABAD SINDH.",
        "phone": "022-2613454",
        "ntn": "1417156-2",
        "strn": "01-01-9018-006-64",
        "header_title": "NATIONAL TRADERS",
        "header_sub": "Total Scientific Solution",
        "challan_sub": "DEALERS: DIAGNOSTIC REAGENT CHEMICALS, SURGICAL & SCIENTIFIC INSTRUMENTS...",
        "footer_title": "NATIONAL TRADERS"
    },
    "M/S Nouman Traders": {
        "template_type": "simple",
        "address": "Plot No; 14, Flate No: 20, 2nd Floor,<br>Shams Residency, Qasimabad Hyderabad Sindh.",
        "phone": "0334-3348650",
        "ntn": "", "strn": "",
        "header_title": "M/S NOUMAN TRADERS",
        "footer_title": "M/S NOUMAN TRADERS"
    },
    "M/S SK Marketing Services": {
        "template_type": "simple",
        "address": "P-13 Phase-I, Qasimabad Hyderabad",
        "phone": "3473490651",
        "ntn": "4359033-7", "strn": "3277876132385",
        "header_title": "M/S SK MARKETING SERVICES",
        "footer_title": "M/S SK MARKETING SERVICES"
    },
    "M/S Science Enterprises": {
        "template_type": "simple",
        "address": "House No. A-5, Meer Fazal Town,<br>Unit No. 9, Latifabad Hyderabad, Sindh.",
        "phone": "", "ntn": "8714104-8", "strn": "4130482831421",
        "header_title": "M/S SCIENCE ENTERPRISES",
        "footer_title": "M/S SCIENCE ENTERPRISES"
    },
    "M/S AK Traders": {
        "template_type": "simple",
        "address": "Suite No. 13, Pak Peoples colony, Masjid-e-Quba<br>Block-21, Federal B Area, Karachi-Pakistan.",
        "phone": "3312636505",
        "ntn": "5016205-1", "strn": "",
        "header_title": "M/S AK TRADERS",
        "footer_title": "M/S AK TRADERS"
    },
    "M/S Panjtan Enterprises": {
        "template_type": "simple",
        "address": "Bungalow No. A/7, Phase I, Anwar Villase,<br>Qasimabad, Hyderabad.",
        "phone": "3453544419",
        "ntn": "", "strn": "",
        "header_title": "Panjtan Enterprises",
        "footer_title": "Panjtan Enterprises"
    },
    "M/S Uraiz Pharma": {
        "template_type": "simple",
        "address": "", "phone": "", "ntn": "", "strn": "",
        "header_title": "M/S Uraiz Pharma",
        "footer_title": "M/S Uraiz Pharma"
    }
}

DEPARTMENTS = [
    "Vaccine Production Unit Sindh TandoJam (VPU)",
    "CVDL SINDH TANDO JAM",
    "Animal Breeding Sindh Hyderabad",
    "Animal Husbandry"
]

# --- 2. OCR ENGINE ---
def perform_ocr_extraction(image_file):
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        text = pytesseract.image_to_string(gray)
        
        extracted_data = {"po_no": "", "date": "", "dept": "", "items": []}
        
        # Regex Extraction Logic
        order_match = re.search(r'(?:No\.|NO\.|Order No)\s?[:\.]?\s?([A-Za-z0-9\/\-\(\)\s]+)', text)
        if order_match:
            raw_no = order_match.group(1).split("dated")[0].split("Tando")[0]
            extracted_data['po_no'] = raw_no.strip()

        date_match = re.search(r'(\d{2}[\/\-]\d{2}[\/\-]\d{4})', text)
        if date_match:
            extracted_data['date'] = date_match.group(1)
            
        if "VETERINARY" in text.upper() or "CVDL" in text.upper():
            extracted_data['dept'] = "CVDL SINDH TANDO JAM"
        elif "VACCINE" in text.upper() or "VPU" in text.upper():
            extracted_data['dept'] = "Vaccine Production Unit Sindh TandoJam (VPU)"
        elif "BREEDING" in text.upper():
             extracted_data['dept'] = "Animal Breeding Sindh Hyderabad"
        
        # Simple Item detection heuristic
        lines = text.split('\n')
        for line in lines:
            if re.search(r'\d{1,5}\s+[\d,]{3,}', line): 
                 extracted_data['items'].append({"Qty": 0, "Description": line, "Rate": 0})
        
        image_file.seek(0)
        return extracted_data, None

    except Exception as e:
        image_file.seek(0)
        return None, str(e)

# --- 3. HELPER FUNCTIONS ---
def get_last_serial(company, department):
    if os.path.exists(SERIAL_FILE):
        try:
            with open(SERIAL_FILE, 'r') as f: data = json.load(f)
        except: data = {}
    else: data = {}
    return data.get(f"{company}_{department}", 0)

def update_serial(company, department, specific_val=None):
    if os.path.exists(SERIAL_FILE):
        try:
            with open(SERIAL_FILE, 'r') as f: data = json.load(f)
        except: data = {}
    else: data = {}
    key = f"{company}_{department}"
    if specific_val:
        try: data[key] = int(specific_val)
        except: pass
    else:
        data[key] = data.get(key, 0) + 1
    with open(SERIAL_FILE, 'w') as f: json.dump(data, f)

def img_to_base64(img_bytes):
    if img_bytes is None: return None
    return base64.b64encode(img_bytes.getvalue()).decode()

# --- 4. CSS STYLING ---
GLOBAL_CSS = """
@page { size: A4; margin: 0.5cm 1cm; }
.simple-margins { @page { margin-top: 2.5in; margin-bottom: 1.5in; } }
body { font-family: Arial, sans-serif; font-size: 10pt; line-height: 1.2; display: flex; flex-direction: column; justify-content: center; height: 100%; }
.bold { font-weight: bold; }
.right { text-align: right; }
.center { text-align: center; }
.v-top { vertical-align: top; }
.title-box { text-align: center; margin-bottom: 10px; }
.main-title { font-family: "Times New Roman", serif; font-weight: bold; display: inline-block; border-bottom: 2px solid black; }
.gst-title { font-size: 24pt; }
.bill-title { font-size: 22pt; }
.grid-table { width: 100%; border-collapse: collapse; margin-top: 5px; table-layout: fixed; }
.grid-table th { background-color: white; color: black; font-weight: bold; text-align: center; border: 1px solid black; padding: 4px; font-size: 9pt; }
.grid-table td { border: 1px solid black; padding: 4px; font-size: 9pt; word-wrap: break-word; }
.gst-info-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; border: 3px solid black; }
.gst-info-table td { border: none !important; padding: 5px; vertical-align: top; }
.gst-info-label { font-weight: bold; width: 15%; }
.nt-header { border: 2px solid #74c69d; border-radius: 10px; padding: 10px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.nt-logo { width: 100px; height: auto; }
.simple-header { text-align: center; margin-bottom: 20px; }
.info-row { margin-bottom: 5px; display: flex; }
.info-label { font-weight: bold; min-width: 90px; }
.info-val { border-bottom: 1px solid black; flex-grow: 1; padding-left: 5px; min-height: 14px; }
.footer-row { margin-top: 30px; display: flex; justify-content: space-between; }
.sig-line { border-top: 1px solid black; width: 30%; text-align: center; padding-top: 5px; }
.signature-spacing { margin-top: 3cm; } 
.total-row td { border: 1px solid black; font-weight: bold; }
.black-header th { background-color: black !important; color: white !important; }
"""

# --- 5. TEMPLATES ---
TEMPLATE_GST = """
<html><head><style>""" + GLOBAL_CSS + """</style></head><body>
    <div class="title-box"><div class="main-title gst-title">SALES TAX INVOICE</div></div>
    <div class="center" style="font-size: 10pt; margin-bottom: 15px;">(Under Section 23 of S.Tax Act 1990)</div>
    <table style="width: 100%; margin-bottom: 5px;">
        <tr><td class="bold" style="width: 20%; border-bottom: 2px solid black; display:inline-block;">ORIGINAL</td><td style="width: 50%;"></td><td class="right bold" style="width: 15%;">Serial No.</td><td class="center" style="border: 1px solid black; width: 15%;">{{ serial }}</td></tr>
        <tr><td>Time of Supply:</td><td></td><td class="right bold">Date:</td><td class="center" style="border: 1px solid black;">{{ date }}</td></tr>
    </table>
    <table class="gst-info-table">
        <tr><td class="gst-info-label">Supplier's Name:</td><td width="35%">{{ comp.header_title }}</td><td class="gst-info-label">Buyer's Name:</td><td width="35%">{{ buyer_name }}</td></tr>
        <tr><td class="gst-info-label">Address:</td><td>{{ comp.address|safe }}</td><td class="gst-info-label">Address:</td><td>{{ dept }}</td></tr>
        <tr><td class="gst-info-label">Telephone:</td><td>{{ comp.phone }}</td><td class="gst-info-label">N.T.N No.</td><td></td></tr>
        <tr><td class="gst-info-label">N.T.N No.</td><td>{{ comp.ntn }}</td><td class="gst-info-label">Terms of Sales:</td><td></td></tr>
        <tr><td class="gst-info-label">S.T.Reg No:</td><td>{{ comp.strn }}</td><td></td><td></td></tr>
    </table>
    <table class="grid-table">
        <thead><tr><th width="10%">Quantity</th><th width="40%">Description of Goods</th><th width="13%">Value<br>Excl.S.Tax</th><th width="10%">Rate of<br>Sales Tax</th><th width="12%">Total Sales Tax<br>Payable</th><th width="15%">Value Including<br>Sales.Tax</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ item.Qty }} Pkts.</td><td class="v-top">{{ item.Description }}</td><td class="center v-top">{{ "{:,.0f}".format(item.val_excl) }}</td><td class="center v-top">18%</td><td class="center v-top">{{ "{:,.0f}".format(item.tax_val) }}</td><td class="center v-top">{{ "{:,.0f}".format(item.val_incl) }}</td></tr>{% endfor %}
            {% if items|length < 12 %}{% for i in range(12 - items|length) %} <tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr> {% endfor %}{% endif %}
        </tbody>
        <tfoot><tr class="total-row"><td colspan="2" class="right">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.excl) }}</td><td class="center">18%</td><td class="center">{{ "{:,.0f}".format(totals.tax) }}</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr></tfoot>
    </table>
    <br><br><br><div style="width: 30%; border-top: 1px solid black; margin-left: auto; text-align: center;">SIGNATURE</div>
</body></html>
"""

TEMPLATE_BILL = """
<html><head><style>""" + GLOBAL_CSS + """</style></head><body class="{% if comp.template_type == 'simple' %}simple-margins{% endif %}">
    {% if comp.template_type == 'logo' %}<div class="title-box"><div class="main-title bill-title">BILL/CASH MEMO</div></div><div class="nt-header"><div style="width: 70%;"><div class="nt-title main-title">{{ comp.header_title }}</div><div style="font-size: 9pt;">{{ comp.address|safe }}</div></div><div class="center" style="width: 30%;">{% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}<div style="font-size: 7pt; font-weight: bold; margin-top: 2px;">{{ comp.header_sub }}</div></div></div>{% else %}<div class="simple-header"><div class="main-title bill-title">BILL</div></div>{% endif %}
    <table style="width: 100%; margin-bottom: 10px;"><tr><td width="65%" class="v-top"><div class="info-row"><span class="info-label">Messers:</span><span class="info-val">{{ buyer_name }}</span></div><div class="info-row"><span class="info-label">Address:</span><span class="info-val">{{ dept }}</span></div><div class="info-row"><span class="info-label">Order No:</span><span class="info-val">{{ po_no }}</span></div></td><td width="5%"></td><td width="30%" class="v-top"><div class="info-row"><span class="info-label" style="min-width: 60px;">No.</span><span class="info-val center bold">{{ serial }}</span></div><div class="info-row"><span class="info-label" style="min-width: 60px;">Dated:</span><span class="info-val center bold">{{ date }}</span></div></td></tr></table>
    <table class="grid-table {% if comp.template_type == 'logo' %}black-header{% endif %}">
        <thead><tr><th width="8%">S.No.</th><th width="15%">QTY.</th><th width="47%">PARTICULARS</th><th width="15%">RATE</th><th width="15%">AMOUNT</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ item.Qty }} Pkts.</td><td class="v-top">{{ item.Description }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Rate) }}</td><td class="center v-top bold">{{ "{:,.0f}".format(item.val_incl) }}</td></tr>{% endfor %}
            {% if items|length < 12 %}{% for i in range(12 - items|length) %} <tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr> {% endfor %}{% endif %}
        </tbody>
        <tfoot><tr class="total-row"><td colspan="4" class="right" style="{% if comp.template_type == 'logo' %}background:black; color:white;{% endif %}">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr></tfoot>
    </table>
    <div style="margin-top: 15px;"><span class="bold">Rupees = </span><span class="italic">{{ amount_words }}</span></div><div class="footer-row"><div></div><div class="bold right" style="margin-top: 30px;">For, {{ comp.footer_title }}</div></div>
</body></html>
"""

TEMPLATE_CHALLAN = """
<html><head><style>""" + GLOBAL_CSS + """</style></head><body class="{% if comp.template_type == 'simple' %}simple-margins{% endif %}">
    {% if comp.template_type == 'logo' %}<div class="nt-header" style="border: none;"><div style="width: 70%;"><div class="nt-title main-title">{{ comp.header_title }}</div><div style="font-size: 8pt; font-weight: bold;">{{ comp.challan_sub }}</div></div><div class="center" style="width: 30%;">{% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}</div></div><div class="title-box" style="margin-bottom: 10px;"><div class="main-title" style="font-size: 14pt;">Delivery Challan</div></div>{% else %}<div class="simple-header"><div class="main-title bill-title">Delivery Challan</div></div>{% endif %}
    <table style="width: 100%; margin-bottom: 15px;"><tr><td width="65%" class="v-top"><div class="info-row"><span class="info-label" style="min-width: 130px;">Your Supply Order No:</span><span class="info-val">{{ po_no }}</span></div><div class="info-row"><span class="info-label" style="min-width: 130px;">Messers:</span><span class="info-val">{{ buyer_name }}</span></div><div class="info-row"><span class="info-label" style="min-width: 130px;">Address:</span><span class="info-val">{{ dept }}</span></div></td><td width="5%"></td><td width="30%" class="v-top"><div class="info-row"><span class="info-label">D.C. NO.</span><span class="info-val center bold">{{ serial }}</span></div>{% if comp.template_type == 'simple' %}<div class="info-row"><span class="info-label">Date:</span><span class="info-val center bold">{{ date }}</span></div>{% endif %}</td></tr></table>
    <table class="grid-table">
        <thead><tr><th width="8%">S.No.</th><th width="15%">QUANTITY</th><th width="77%">PARTICULARS</th></tr></thead>
        <tbody>
            {% for item in items %}<tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ item.Qty }} Pkts.</td><td class="v-top">{{ item.Description }}</td></tr>{% endfor %}
            {% if items|length < 14 %}{% for i in range(14 - items|length) %} <tr><td>&nbsp;</td><td></td><td></td></tr> {% endfor %}{% endif %}
        </tbody>
    </table>
    <div class="center italic bold" style="margin-top: 20px; border: 1px solid black; padding: 5px;">Received above mentioned Goods checked and found to be good condition</div>
    <div class="footer-row signature-spacing"><div class="sig-line">Receiver's Signature</div><div class="sig-line">Checked by:</div><div class="sig-line">For {{ comp.footer_title }}</div></div>
</body></html>
"""

# --- 6. GENERATION ---
def generate_docs(company_name, dept_name, buyer_name, items_data, po_no, po_date, logo_b64, manual_serial):
    if manual_serial and manual_serial.strip():
        final_serial = manual_serial.zfill(4)
        update_serial(company_name, dept_name, final_serial)
    else:
        update_serial(company_name, dept_name)
        final_serial = f"{get_last_serial(company_name, dept_name):04d}"
    comp_data = COMPANIES[company_name]
    processed_items = []
    t_excl = 0; t_tax = 0; t_incl = 0
    for item in items_data:
        try: qty = float(item['Qty']); rate = float(item['Rate'])
        except: qty = 0; rate = 0
        val_incl = qty * rate; val_excl = val_incl / 1.18; tax = val_incl - val_excl
        t_excl += val_excl; t_tax += tax; t_incl += val_incl
        processed_items.append({**item, 'val_excl': val_excl, 'tax_val': tax, 'val_incl': val_incl})
    totals = {'excl': t_excl, 'tax': t_tax, 'incl': t_incl}
    try: amount_words = f"Rupees {num2words(int(round(t_incl))).title().replace('-', ' ')} Only"
    except: amount_words = "Rupees .............................................."
    context = {'comp': comp_data, 'dept': dept_name, 'buyer_name': buyer_name, 'items': processed_items, 'po_no': po_no, 'date': po_date, 'serial': final_serial, 'totals': totals, 'amount_words': amount_words, 'logo_b64': logo_b64}
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
        zf.writestr(f"1_GST_{final_serial}.pdf", HTML(string=Template(TEMPLATE_GST).render(**context)).write_pdf())
        zf.writestr(f"2_Bill_{final_serial}.pdf", HTML(string=Template(TEMPLATE_BILL).render(**context)).write_pdf())
        zf.writestr(f"3_Challan_{final_serial}.pdf", HTML(string=Template(TEMPLATE_CHALLAN).render(**context)).write_pdf())
    return zip_buffer.getvalue(), final_serial

# --- 7. UI ---
st.set_page_config(page_title="Invoice Master", layout="wide")
if 'gen_zip' not in st.session_state: st.session_state.gen_zip = None
if 'gen_serial' not in st.session_state: st.session_state.gen_serial = ""

st.title("Auto-Document Generator (Cloud Ready)")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("1. Settings")
    comp_key = st.selectbox("Company", list(COMPANIES.keys()))
    manual_serial = st.text_input("Manual Serial No.", placeholder="Override Auto-Serial")
    logo = st.file_uploader("Upload Logo", type=['png', 'jpg'])

with col2:
    st.subheader("2. Order Details")
    uploaded_img = st.file_uploader("Upload Scan for OCR (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
    
    extracted_po = ""
    extracted_date = datetime.now().strftime("%d-%m-%Y")
    extracted_dept = "CVDL SINDH TANDO JAM"
    extracted_buyer = "The Project Director"
    current_items = [{"Qty": 0, "Description": "", "Rate": 0}]

    if uploaded_img:
        with st.spinner("Analyzing image..."):
            ocr_data, error = perform_ocr_extraction(uploaded_img)
            if ocr_data:
                st.success("Extracted!")
                extracted_po = ocr_data.get('po_no', "")
                extracted_date = ocr_data.get('date', "") or extracted_date
                extracted_dept = ocr_data.get('dept', "") or extracted_dept
                if ocr_data.get('items'): current_items = ocr_data['items']
    
    col_a, col_b = st.columns(2)
    po_no = col_a.text_input("Order No", value=extracted_po)
    po_dt = col_b.text_input("Date", value=extracted_date)
    buyer_name = st.text_input("Messers", value=extracted_buyer)
    dept_key = st.text_input("Department/Address", value=extracted_dept)
    
    if 'editor_df' not in st.session_state or (uploaded_img and st.session_state.get('last_img') != uploaded_img.name):
        st.session_state.editor_df = pd.DataFrame(current_items)
        if uploaded_img: st.session_state.last_img = uploaded_img.name

    df_items = st.data_editor(st.session_state.editor_df, num_rows="dynamic", use_container_width=True)
    
    st.write("---")
    if st.button("Generate Documents", type="primary"):
        if COMPANIES[comp_key]['template_type'] == 'logo' and not logo:
            st.error("Logo required for National Traders!")
        else:
            logo_b64 = img_to_base64(logo) if logo else None
            try: items_list = df_items.to_dict('records')
            except: items_list = []
            zip_data, new_serial = generate_docs(comp_key, dept_key, buyer_name, items_list, po_no, po_dt, logo_b64, manual_serial)
            st.session_state.gen_zip = zip_data
            st.session_state.gen_serial = new_serial
            st.rerun()

if st.session_state.gen_zip:
    st.success(f"Ready: Serial {st.session_state.gen_serial}")
    st.warning("Note: On the free cloud, serial numbers may reset if the app restarts. You can manually set them above.")
    st.download_button(label="Download ZIP", data=st.session_state.gen_zip, file_name=f"Docs_{st.session_state.gen_serial}.zip", mime="application/zip")