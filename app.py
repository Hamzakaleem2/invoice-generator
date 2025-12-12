import streamlit as st
import pandas as pd
from datetime import datetime
from config import COMPANIES, DEPARTMENTS, img_to_base64
from ocr_service import analyze_with_mistral
from pdf_service import generate_pdf_package

# --- UI SETUP ---
st.set_page_config(page_title="Invoice Master (Microservices)", layout="wide")
if 'gen_zip' not in st.session_state: st.session_state.gen_zip = None
if 'gen_serial' not in st.session_state: st.session_state.gen_serial = ""

st.title("Auto-Document Generator")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Service Config")
    mistral_key = st.text_input("AI Key", type="password")

# --- MAIN COLUMNS ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Settings")
    comp_key = st.selectbox("Company", list(COMPANIES.keys()))
    manual_serial = st.text_input("Manual Serial No.", placeholder="Override Auto-Serial")
    logo = st.file_uploader("Upload Logo", type=['png', 'jpg'])

with col2:
    st.subheader("2. Order Processing")
    uploaded_img = st.file_uploader("Scan Image", type=['png', 'jpg', 'jpeg'])
    
    # Defaults
    extracted_po = ""
    extracted_date = datetime.now().strftime("%d.%m.%Y")
    extracted_dept = "CVDL SINDH TANDO JAM"
    extracted_buyer = "The Project Director"
    current_items = [{"Qty": 0, "Description": "", "Rate": 0}]

    # Call OCR Service
    if uploaded_img and st.button("Analyze with AI Service"):
        with st.spinner("Calling OCR Service..."):
            ai_data, error = analyze_with_mistral(uploaded_img, mistral_key)
            if error: st.error(error)
            elif ai_data:
                st.success("Analysis Complete")
                extracted_po = ai_data.get('po_no', "")
                extracted_date = ai_data.get('date', "") or extracted_date
                extracted_dept = ai_data.get('dept', "") or extracted_dept
                extracted_buyer = ai_data.get('buyer', "") or extracted_buyer
                if ai_data.get('items'): current_items = ai_data['items']
                
                st.session_state.editor_df = pd.DataFrame(current_items)
                st.session_state.extracted_data = {
                    'po': extracted_po, 'date': extracted_date, 
                    'dept': extracted_dept, 'buyer': extracted_buyer
                }

    # Data Binding
    defaults = st.session_state.get('extracted_data', {})
    po_no = st.text_input("Order No", value=defaults.get('po', extracted_po))
    col_a, col_b = st.columns(2)
    po_dt = col_a.text_input("Date", value=defaults.get('date', extracted_date))
    buyer_name = col_b.text_input("Messers", value=defaults.get('buyer', extracted_buyer))
    dept_key = st.text_input("Department/Address", value=defaults.get('dept', extracted_dept))
    
    if 'editor_df' not in st.session_state: st.session_state.editor_df = pd.DataFrame(current_items)
    df_items = st.data_editor(st.session_state.editor_df, num_rows="dynamic", use_container_width=True)
    
    st.write("---")
    
    # Call PDF Service
    if st.button("Generate Documents", type="primary"):
        logo_b64 = None
        if logo:
            logo_b64 = img_to_base64(logo)
            
        if COMPANIES[comp_key]['template_type'] == 'logo' and not logo:
            st.error("Logo required for National Traders!")
        else:
            try: items_list = df_items.to_dict('records')
            except: items_list = []
            
            # Call the PDF Service Function
            zip_data, new_serial = generate_pdf_package(
                comp_key, dept_key, buyer_name, items_list, 
                po_no, po_dt, logo_b64, manual_serial
            )
            st.session_state.gen_zip = zip_data
            st.session_state.gen_serial = new_serial
            st.rerun()

if st.session_state.gen_zip:
    st.success(f"Generated Serial: {st.session_state.gen_serial}")
    st.download_button(label="Download ZIP", data=st.session_state.gen_zip, file_name=f"Docs_{st.session_state.gen_serial}.zip", mime="application/zip")
