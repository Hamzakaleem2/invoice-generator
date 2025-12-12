import json
import os

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

# GLOBAL STYLES (Used by PDF Service)
BASE_CSS = """
body { font-family: Arial, sans-serif; font-size: 10pt; line-height: 1.2; }
.bold { font-weight: bold; }
.right { text-align: right; }
.center { text-align: center; }
.v-top { vertical-align: top; }
.title-box { text-align: center; margin-bottom: 10px; }
.main-title { font-family: "Times New Roman", serif; font-weight: bold; display: inline-block; text-decoration: underline; }
.gst-title { font-size: 24pt; }
.bill-title { font-size: 22pt; }
.grid-table { width: 100%; border-collapse: collapse; margin-top: 5px; table-layout: fixed; }
.grid-table th { background-color: white; color: black; font-weight: bold; text-align: center; border: 1px solid black; padding: 4px; font-size: 9pt; }
.grid-table td { border: 1px solid black; padding: 4px; font-size: 9pt; word-wrap: break-word; }
.gst-info-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; border: 3px solid black; }
.gst-info-table td { border: none !important; padding: 5px; vertical-align: top; }
.gst-partition { border-right: 2px solid black !important; }
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
