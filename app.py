import streamlit as st
import pandas as pd
import io
import json
import base64
import zipfile
import re
import os
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML, CSS
from num2words import num2words
from mistralai import Mistral

# --- 1. CONFIGURATION & KEYS ---
# Paste your API key here
MISTRAL_API_KEY = "HvCqGQtSLzkxu2C3gmPyWm8Xg5wNktly" 

SERIAL_FILE = 'serial_tracker.json'
# Name your logo file EXACTLY this and upload it to GitHub alongside app.py
PERMANENT_LOGO_FILE = "nt_logo.png"

# --- 2. COMPANY DATABASE ---
COMPANIES = {
    "M/S National Traders": {
        "template_type": "logo",
        "address": "NEAR CIVIL HOSPITAL, BHURGRI ROAD,<br>HIRABAD, HYDERABAD SINDH.",
        "phone": "022-2613454",
        "ntn": "1417156-2",
        "strn": "01-01-9018-006-64",
        "header_title": "NATIONAL TRADERS",
        "header_sub": "",
        "challan_sub": "DEALERS: DIAGNOSTIC REAGENT CHEMICALS, SURGICAL & SCIENTIFIC INSTRUMENTS, LABORATORY EQUIPMENTS, GLASSWARE, ELECTRO MEDICAL EQUIPMENTS, HOSPITAL EQUIPMENTS & GENERAL ORDER SUPPLIER",
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

# --- 3. LOGIC HELPERS ---
def clean_buyer_name(text):
    """Aggressive cleaner: If it sees a Title, it deletes the Name."""
    if not text: return "The Project Director"
    upper_text = text.upper()
    
    if "PROJECT DIRECTOR" in upper_text:
        return "The Project Director"
    if "DIRECTOR" in upper_text and "VETERINARY" in upper_text:
        return "Director of Veterinary Research and Diagnosis"
    if "DIRECTOR" in upper_text:
        return "The Director"
    
    # Fallback
    return "The Project Director"

def get_last_serial(company, department):
    try:
        with open(SERIAL_FILE, 'r') as f: return json.load(f).get(f"{company}_{department}", 0)
    except: return 0

def update_serial(company, department, specific_val=None):
    try:
        with open(SERIAL_FILE, 'r') as f: data = json.load(f)
    except: data = {}
    key = f"{company}_{department}"
    if specific_val:
        try: data[key] = int(specific_val)
        except: pass
    else:
        data[key] = data.get(key, 0) + 1
    with open(SERIAL_FILE, 'w') as f: json.dump(data, f)

def img_to_base64(img_bytes):
    if img_bytes is None: return None
    img_bytes.seek(0)
    return base64.b64encode(img_bytes.read()).decode()

def clean_float(value):
    if value is None: return 0.0
    try:
        if isinstance(value, str): return float(re.sub(r'[^\d.]', '', value))
        return float(value)
    except: return 0.0

# --- 4. AI ENGINE ---
def analyze_with_mistral(image_file):
    api_key = MISTRAL_API_KEY
    if "YOUR_MISTRAL_API_KEY" in api_key:
        return None, "Please set MISTRAL_API_KEY in code."
    
    try:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        image_file.seek(0)
        client = Mistral(api_key=api_key)
        
        prompt = """
        Extract from this Purchase Order image:
        {
            "po_no": "Order No string",
            "date": "DD.MM.YYYY",
            "buyer": "Identify the Designation (e.g. Project Director). IGNORE specific names like Dr. Shah Murad.",
            "items": [
                {"Qty": number, "Description": "string", "Rate": number}
            ]
        }
        Return ONLY JSON.
        """
        
        resp = client.chat.complete(
            model="pixtral-12b-2409",
            messages=[{"role":"user", "content":[{"type":"text","text":prompt},{"type":"image_url","image_url":f"data:image/jpeg;base64,{base64_image}"}]}]
        )
        content = resp.choices[0].message.content
        if "```" in content: content = content.split("```json")[-1].split("```")[0]
        return json.loads(content.strip()), None
    except Exception as e:
        return None, str(e)

# --- 5. VISUAL STYLING (CSS) ---
def get_css(template_mode="standard"):
    # Using 0.5pt Border-Bottom instead of underline to prevent double-line look
    css = """
    @page { size: A4; margin: 0.25in 0.5in; }
    body { font-family: Arial, sans-serif; font-size: 10pt; line-height: 1.1; }
    .bold { font-weight: bold; }
    .right { text-align: right; }
    .center { text-align: center; }
    .v-top { vertical-align: top; }
    
    .title-box { text-align: center; margin-bottom: 5px; }
    
    /* THE FIX: No text-decoration, just a thin border */
    .main-title { 
        font-family: "Times New Roman", serif; 
        font-weight: bold; 
        display: inline-block; 
        text-decoration: none !important;
        border-bottom: 0.5pt solid black;
        padding-bottom: 1px;
    }
    .gst-title { font-size: 22pt; }
    .bill-title { font-size: 20pt; }
    
    .grid-table { width: 100%; border-collapse: collapse; margin-top: 5px; table-layout: fixed; }
    .grid-table th { background-color: white; color: black; font-weight: bold; text-align: center; border: 1px solid black; padding: 3px; font-size: 9pt; }
    .grid-table td { border: 1px solid black; padding: 3px; font-size: 9pt; word-wrap: break-word; }
    
    .gst-info-table { width: 100%; border-collapse: collapse; margin-bottom: 5px; border: 2px solid black; }
    .gst-info-table td { border: none !important; padding: 3px; vertical-align: top; }
    .gst-info-label { font-weight: bold; width: 15%; }
    
    .nt-header { border: 2px solid #74c69d; border-radius: 10px; padding: 5px; margin-bottom: 5px; }
    .nt-logo { width: 130px; height: auto; display: block; }
    .simple-header { text-align: center; margin-bottom: 10px; }
    
    .info-row { margin-bottom: 2px; display: flex; }
    .info-label { font-weight: bold; min-width: 90px; }
    .info-val { border-bottom: 1px solid black; flex-grow: 1; padding-left: 5px; min-height: 14px; }
    
    .footer-row { margin-top: 20px; display: flex; justify-content: space-between; }
    .sig-line { border-top: 1px solid black; width: 30%; text-align: center; padding-top: 5px; }
    .signature-spacing { margin-top: 2cm; } 
    .total-row td { border: 1px solid black; font-weight: bold; }
    .black-header th { background-color: black !important; color: white !important; }
    """
    
    if template_mode == "letterhead":
        css += "@page { size: A4; margin-top: 2.5in; margin-bottom: 1in; margin-left: 1cm; margin-right: 1cm; }"
    return css

# --- 6. TEMPLATES ---

TEMPLATE_GST = """
<html><head><style>{{ css }}</style></head><body>
    <div class="title-box"><div class="main-title gst-title">SALES TAX INVOICE</div></div>
    <div class="center" style="font-size: 10pt; margin-bottom: 10px;">(Under Section 23 of S.Tax Act 1990)</div>
    
    <table style="width: 100%; margin-bottom: 5px;">
        <tr><td class="bold" style="width: 20%; border-bottom: 0.5pt solid black; display:inline-block;">ORIGINAL</td><td style="width: 50%;"></td><td class="right bold" style="width: 15%;">Serial No.</td><td class="center" style="border: 1px solid black; width: 15%;">{{ serial }}</td></tr>
        <tr><td>Time of Supply:</td><td></td><td class="right bold">Date:</td><td class="center" style="border: 1px solid black;">{{ date }}</td></tr>
    </table>
    
    <table class="gst-info-table">
        <tr>
            <td class="gst-info-label">Supplier's Name:</td><td width="35%" style="border-right: 2px solid black !important;">{{ comp.header_title }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Buyer's Name:</td><td width="35%">{{ buyer_name }}</td>
        </tr>
        <tr>
            <td class="gst-info-label">Address:</td><td style="border-right: 2px solid black !important;">{{ comp.address|safe }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Address:</td><td>{{ dept }}</td>
        </tr>
        <tr>
            <td class="gst-info-label">Telephone:</td><td style="border-right: 2px solid black !important;">{{ comp.phone }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">N.T.N No.</td><td></td>
        </tr>
        <tr>
            <td class="gst-info-label">N.T.N No.</td><td style="border-right: 2px solid black !important;">{{ comp.ntn }}</td>
            <td class="gst-info-label" style="padding-left: 10px;">Terms of Sales:</td><td></td>
        </tr>
        <tr>
            <td class="gst-info-label">S.T.Reg No:</td><td style="border-right: 2px solid black !important;">{{ comp.strn }}</td>
            <td></td><td></td>
        </tr>
    </table>
    
    <table class="grid-table">
        <thead>
            <tr><th width="8%">Quantity</th><th width="50%">Description of Goods</th><th width="12%">Value<br>Excl.S.Tax</th><th width="8%">Rate of<br>Sales Tax</th><th width="10%">Total Sales Tax<br>Payable</th><th width="12%">Value Including<br>Sales.Tax</th></tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td>
                <td class="v-top">{{ item.Description }}</td>
                <td class="center v-top">{{ "{:,.0f}".format(item.val_excl) }}</td><td class="center v-top">18%</td><td class="center v-top">{{ "{:,.0f}".format(item.tax_val) }}</td><td class="center v-top">{{ "{:,.0f}".format(item.val_incl) }}</td>
            </tr>
            {% endfor %}
            {% set target_rows = 12 %}
            {% set filler_count = target_rows - items|length %}
            {% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
        <tfoot>
            <tr class="total-row"><td colspan="2" class="right">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.excl) }}</td><td class="center">18%</td><td class="center">{{ "{:,.0f}".format(totals.tax) }}</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr>
        </tfoot>
    </table>
    <br><br><div style="width: 30%; border-top: 1px solid black; margin-left: auto; text-align: center;">SIGNATURE</div>
</body></html>
"""

TEMPLATE_BILL = """
<html><head><style>{{ css }}</style></head><body>
    {% if comp.template_type == 'logo' %}
        <div class="title-box"><div class="main-title bill-title">BILL/CASH MEMO</div></div>
        <div class="nt-header">
            <table style="width: 100%; border: none;">
                <tr>
                    <td style="width: 70%; text-align: left; border: none; vertical-align: middle;">
                        <div class="main-title" style="font-size: 26pt; border: none; text-decoration: none;">{{ comp.header_title }}</div>
                        <div style="font-size: 9pt;">{{ comp.address|safe }}</div>
                    </td>
                    <td style="width: 30%; text-align: right; border: none; vertical-align: middle;">
                        {% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}
                    </td>
                </tr>
            </table>
        </div>
    {% else %}
        <div class="simple-header"><div class="main-title bill-title">BILL</div></div>
    {% endif %}
    
    <table style="width: 100%; margin-bottom: 5px;">
        <tr>
            <td width="65%" class="v-top" style="border: none;">
                <div class="info-row"><span class="info-label">Messers:</span><span class="info-val">{{ buyer_name }}</span></div>
                <div class="info-row"><span class="info-label">Address:</span><span class="info-val">{{ dept }}</span></div>
                <div class="info-row"><span class="info-label">Order No:</span><span class="info-val">{{ po_no }}</span></div>
            </td>
            <td width="5%" style="border: none;"></td>
            <td width="30%" class="v-top" style="border: none;">
                <div class="info-row"><span class="info-label" style="min-width: 60px;">No.</span><span class="info-val center bold">{{ serial }}</span></div>
                <div class="info-row"><span class="info-label" style="min-width: 60px;">Dated:</span><span class="info-val center bold">{{ date }}</span></div>
            </td>
        </tr>
    </table>
    
    <table class="grid-table {% if comp.template_type == 'logo' %}black-header{% endif %}">
        <thead><tr><th width="4%">S.No.</th><th width="10%">QTY.</th><th width="58%">PARTICULARS</th><th width="14%">RATE</th><th width="14%">AMOUNT</th></tr></thead>
        <tbody>
            {% for item in items %}
            <tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td><td class="v-top">{{ item.Description }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Rate) }}</td><td class="center v-top bold">{{ "{:,.0f}".format(item.val_incl) }}</td></tr>
            {% endfor %}
            {% set target_rows = 15 %}
            {% set filler_count = target_rows - items|length %}
            {% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
        <tfoot><tr class="total-row"><td colspan="4" class="right" style="{% if comp.template_type == 'logo' %}background:black; color:white;{% endif %}">TOTAL</td><td class="center">{{ "{:,.0f}".format(totals.incl) }}</td></tr></tfoot>
    </table>
    <div style="margin-top: 10px;"><span class="bold">Rupees = </span><span class="italic">{{ amount_words }}</span></div>
    <div class="footer-row"><div></div><div class="bold right" style="margin-top: 20px;">For, {{ comp.footer_title }}</div></div>
</body></html>
"""

TEMPLATE_CHALLAN = """
<html><head><style>{{ css }}</style></head><body>
    {% if comp.template_type == 'logo' %}
        <div class="nt-header" style="border: none;">
            <table style="width: 100%; border: none;">
                <tr>
                    <td style="width: 25%; text-align: left; border: none; vertical-align: middle;">
                         {% if logo_b64 %}<img src="data:image/png;base64,{{ logo_b64 }}" class="nt-logo">{% endif %}
                    </td>
                    <td style="width: 75%; text-align: center; border: none; vertical-align: middle;">
                        <div class="main-title" style="font-size: 26pt; border: none; text-decoration: none;">{{ comp.header_title }}</div>
                        <div style="font-size: 8pt; font-weight: bold;">{{ comp.challan_sub }}</div>
                    </td>
                </tr>
            </table>
        </div>
        <div class="title-box" style="margin-bottom: 5px;"><div class="main-title" style="font-size: 14pt;">Delivery Challan</div></div>
    {% else %}
        <div class="simple-header"><div class="main-title bill-title">Delivery Challan</div></div>
    {% endif %}
    
    <table style="width: 100%; margin-bottom: 5px;">
        <tr>
            <td width="65%" class="v-top" style="border: none;">
                <div class="info-row"><span class="info-label" style="min-width: 130px;">Your Supply Order No:</span><span class="info-val">{{ po_no }}</span></div>
                <div class="info-row"><span class="info-label" style="min-width: 130px;">Messers:</span><span class="info-val">{{ buyer_name }}</span></div>
                <div class="info-row"><span class="info-label" style="min-width: 130px;">Address:</span><span class="info-val">{{ dept }}</span></div>
            </td>
            <td width="5%" style="border: none;"></td>
            <td width="30%" class="v-top" style="border: none;">
                <div class="info-row"><span class="info-label">D.C. NO.</span><span class="info-val center bold">{{ serial }}</span></div>
                <div class="info-row"><span class="info-label">Date:</span><span class="info-val center bold">{{ date }}</span></div>
            </td>
        </tr>
    </table>
    
    <table class="grid-table">
        <thead><tr><th width="4%">S.No.</th><th width="10%">QUANTITY</th><th width="86%">PARTICULARS</th></tr></thead>
        <tbody>
            {% for item in items %}
            <tr><td class="center v-top">{{ loop.index }}</td><td class="center v-top">{{ "{:,.0f}".format(item.Qty) }} Pkts.</td><td class="v-top">{{ item.Description }}</td></tr>
            {% endfor %}
            {% set target_rows = 15 %}
            {% set filler_count = target_rows - items|length %}
            {% if filler_count > 0 %}{% for i in range(filler_count) %}<tr><td>&nbsp;</td><td></td><td></td></tr>{% endfor %}{% endif %}
        </tbody>
    </table>
    <div class="center italic bold" style="margin-top: 15px; border: 1px solid black; padding: 5px;">Received above mentioned Goods checked and found to be good condition</div>
    <br><br>
    <div class="footer-row signature-spacing"><div class="sig-line">Receiver's Signature</div><div class="sig-line">Checked by:</div><div class="sig-line">For {{ comp.footer_title }}</div></div>
</body></html>
"""

# --- 7. GENERATION ---
def generate_docs(comp_key, dept_name, buyer_name, items_data, po_no, po_date, logo_b64, manual_serial):
    if manual_serial and manual_serial.strip():
        final_serial = manual_serial.zfill(4)
        update_serial(comp_key, dept_name, final_serial)
    else:
        update_serial(comp_key, dept_name)
        final_serial = f"{get_last_serial(comp_key, dept_name):04d}"
        
    comp_data = COMPANIES[comp_key]
    processed_items = []
    t_excl = 0; t_tax = 0; t_incl = 0
    
    for item in items_data:
        qty = clean_float(item.get('Qty', 0))
        rate = clean_float(item.get('Rate', 0))
        desc = item.get('Description', '')
        
        val_incl = qty * rate
        val_excl = val_incl / 1.18
        tax = val_incl - val_excl
        t_excl += val_excl; t_tax += tax; t_incl += val_incl
        
        processed_items.append({'Qty': qty, 'Description': desc, 'Rate': rate, 'val_excl': val_excl, 'tax_val': tax, 'val_incl': val_incl})

    totals = {'excl': t_excl, 'tax': t_tax, 'incl': t_incl}
    try: amount_words = f"Rupees {num2words(int(round(t_incl))).title().replace('-', ' ')} Only"
    except: amount_words = "Rupees .............................................."
    
    is_simple = (comp_data['template_type'] == 'simple')
    gst_css = get_css("standard") 
    doc_css = get_css("letterhead" if is_simple else "standard")
    
    context = {'comp': comp_data, 'dept': dept_name, 'buyer_name': buyer_name, 'items': processed_items, 'po_no': po_no, 'date': po_date, 'serial': final_serial, 'totals': totals, 'amount_words': amount_words, 'logo_b64': logo_b64}
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
        zf.writestr(f"1_GST_{final_serial}.pdf", HTML(string=Template(TEMPLATE_GST).render(**context, css=gst_css)).write_pdf())
        zf.writestr(f"2_Bill_{final_serial}.pdf", HTML(string=Template(TEMPLATE_BILL).render(**context, css=doc_css)).write_pdf())
        zf.writestr(f"3_Challan_{final_serial}.pdf", HTML(string=Template(TEMPLATE_CHALLAN).render(**context, css=doc_css)).write_pdf())
    return zip_buffer.getvalue(), final_serial

# --- 8. UI ---
st.set_page_config(page_title="Invoice Master", layout="wide")
if 'gen_zip' not in st.session_state: st.session_state.gen_zip = None
if 'gen_serial' not in st.session_state: st.session_state.gen_serial = ""

st.title("Auto-Document Generator")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("1. Setup")
    comp_key = st.selectbox("Company", list(COMPANIES.keys()))
    dept_key = st.selectbox("Department", DEPARTMENTS)
    manual_serial = st.text_input("Manual Serial No.", placeholder="Override Auto-Serial")
    logo = st.file_uploader("Upload Logo (Optional for NT)", type=['png', 'jpg'])

with col2:
    st.subheader("2. Order")
    uploaded_img = st.file_uploader("Scan Image (Auto-AI)", type=['png', 'jpg', 'jpeg'])
    
    extracted_po = ""
    extracted_date = datetime.now().strftime("%d.%m.%Y")
    extracted_buyer = "The Project Director"
    current_items = [{"Qty": 0, "Description": "", "Rate": 0}]

    if uploaded_img:
        if 'last_img' not in st.session_state or st.session_state.last_img != uploaded_img.name:
            with st.spinner("Processing Image..."):
                ai_data, error = analyze_with_mistral(uploaded_img)
                if error: st.warning(f"AI Warning: {error}")
                elif ai_data:
                    st.success("Extracted!")
                    extracted_po = ai_data.get('po_no', "")
                    extracted_date = ai_data.get('date', "") or extracted_date
                    raw_buyer = ai_data.get('buyer', "")
                    extracted_buyer = clean_buyer_name(raw_buyer)
                    if ai_data.get('items'): current_items = ai_data['items']
                    st.session_state.editor_df = pd.DataFrame(current_items)
                    st.session_state.extracted_data = {'po': extracted_po, 'date': extracted_date, 'buyer': extracted_buyer}
                    st.session_state.last_img = uploaded_img.name

    defaults = st.session_state.get('extracted_data', {})
    po_no = st.text_input("Order No", value=defaults.get('po', extracted_po))
    col_a, col_b = st.columns(2)
    po_dt = col_a.text_input("Date", value=defaults.get('date', extracted_date))
    buyer_name = col_b.text_input("Messers", value=defaults.get('buyer', extracted_buyer))
    
    if 'editor_df' not in st.session_state: st.session_state.editor_df = pd.DataFrame(current_items)
    df_items = st.data_editor(st.session_state.editor_df, num_rows="dynamic", use_container_width=True)
    
    st.write("---")
    if st.button("Generate Documents", type="primary"):
        # --- PERMANENT LOGO LOGIC ---
        logo_b64 = None
        if logo:
            logo_b64 = img_to_base64(logo)
        elif comp_key == "M/S National Traders":
            # Check for local file if no user upload
            if os.path.exists(PERMANENT_LOGO_FILE):
                try:
                    with open(PERMANENT_LOGO_FILE, "rb") as f:
                        logo_b64 = base64.b64encode(f.read()).decode()
                except Exception as e:
                     st.error(f"Error reading local logo file: {e}")
            else:
                 st.error(f"Permanent logo not found: Make sure '{PERMANENT_LOGO_FILE}' is in the project folder.")
        
        # Validation
        if COMPANIES[comp_key]['template_type'] == 'logo' and not logo_b64:
            st.error(f"Error: Logo required! Upload one or ensure '{PERMANENT_LOGO_FILE}' exists in the folder.")
        else:
            try: items_list = df_items.to_dict('records')
            except: items_list = []
            zip_data, new_serial = generate_docs(comp_key, dept_key, buyer_name, items_list, po_no, po_dt, logo_b64, manual_serial)
            st.session_state.gen_zip = zip_data
            st.session_state.gen_serial = new_serial
            st.rerun()

if st.session_state.gen_zip:
    st.success(f"Generated Serial: {st.session_state.gen_serial}")
    st.download_button(label="Download ZIP", data=st.session_state.gen_zip, file_name=f"Docs_{st.session_state.gen_serial}.zip", mime="application/zip")
