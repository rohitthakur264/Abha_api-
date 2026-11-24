import os
import json
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from make_docx_helpers import (
    set_cell_background,
    set_cell_margins,
    add_code_block,
    add_callout,
    format_api_entry,
)

def build_word_document():
    doc = docx.Document()

    # Set page margins (0.75 in / 54 pt)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    # =========================================================================
    # COVER / HEADER
    # =========================================================================
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(10)
    p_title.paragraph_format.space_after = Pt(2)
    run_title = p_title.add_run("ProDoc HMIS ↔ ABDM Middleware")
    run_title.bold = True
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(24)
    run_title.font.color.rgb = RGBColor(15, 76, 129)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    run_sub = p_sub.add_run("Complete Technical API Integration Manual & Architecture Specification")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = RGBColor(71, 85, 105)

    add_callout(
        doc,
        "EXECUTIVE SUMMARY & API AUDIT",
        "This document details all APIs created for the ProDoc HMIS integration with the Ayushman Bharat Digital Mission (ABDM). "
        "It covers the 10 Base Specification APIs (100% of Milestone 1 and Milestone 2) from the XML/Excel specification sheet, "
        "plus the 5 Dedicated Extra APIs built for the live ProDoc OPD form (frmRegisterABHAPatient) and internal orchestration. "
        "All JSON keys strictly adhere to standardized naming conventions (ABHANumber, ABHAAddress).",
        bg_color="EFF6FF",
        border_color="1D4ED8"
    )

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # =========================================================================
    # SUMMARY TABLE: BASE VS EXTRA APIS
    # =========================================================================
    h_sum = doc.add_heading("1. API Architecture & Inventory Summary", level=1)
    h_sum.paragraph_format.space_before = Pt(14)
    h_sum.paragraph_format.space_after = Pt(6)
    for r in h_sum.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(15, 76, 129)

    p_table_desc = doc.add_paragraph(
        "Below is the exact audit comparing the 16 APIs from the original specification sheet "
        "against the actual endpoints implemented in the Python FastAPI middleware:"
    )
    p_table_desc.paragraph_format.space_after = Pt(6)

    tbl = doc.add_table(rows=5, cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    headers = ["Milestone / Category", "Total in Doc", "Created & Ready", "Status", "Description"]
    col_widths = [Inches(1.8), Inches(0.9), Inches(1.1), Inches(1.2), Inches(2.0)]

    hdr_row = tbl.rows[0]
    for c_idx, h_text in enumerate(headers):
        cell = hdr_row.cells[c_idx]
        cell.width = col_widths[c_idx]
        set_cell_background(cell, "0F4C81")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h_text)
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    summary_rows = [
        ("Milestone 1 (M1): Patient Enrolment & Discovery", "7", "7", "100% Created", "APIs 1 to 7 fully operational"),
        ("Milestone 2 (M2): HIP Care Context Linking", "3", "3", "100% Created", "APIs 8 to 10 fully operational"),
        ("Milestone 3 (M3): HIU Consent & Data Transfer", "6", "0", "Roadmap", "Scheduled for HIU records retrieval phase"),
        ("EXTRA APIS: ProDoc OPD Dedicated Flow", "-", "5", "100% Created", "Specialized endpoints for frmRegisterABHAPatient"),
    ]

    for r_idx, row_data in enumerate(summary_rows, start=1):
        row = tbl.rows[r_idx]
        bg_col = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = col_widths[c_idx]
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(9)
            if c_idx == 2:
                r.bold = True
                r.font.color.rgb = RGBColor(22, 101, 52)
            elif c_idx == 3:
                r.bold = True
                r.font.color.rgb = RGBColor(14, 116, 144) if "100%" in val else RGBColor(180, 83, 9)
            else:
                r.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # PART 1: BASE SPECIFICATION APIS (APIS 1 TO 10)
    # =========================================================================
    h_p1 = doc.add_heading("2. Base Specification APIs (From Excel/XML Contract)", level=1)
    h_p1.paragraph_format.space_before = Pt(18)
    h_p1.paragraph_format.space_after = Pt(8)
    for r in h_p1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(15, 76, 129)

    # API 1
    format_api_entry(
        doc,
        api_num="1",
        name="Register Patient / Generate ABHA OTP (Aadhaar Enrolment)",
        category="Milestone 1 (Base Contract)",
        method="POST",
        url="/api/abdm/patients/register",
        desc="Initiates citizen ABHA registration via Aadhaar OTP. Python RSA-encrypts Aadhaar number and returns a transactionId.",
        req_body=json.dumps({
            "patientId": "145",
            "name": "Rohan Thakur",
            "dob": "2008-10-08",
            "gender": "M",
            "mobile": "8779441274",
            "aadhaarNumber": "987654321012",
            "consent": True
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "transactionId": "TXN-ABHA-5fc4645d-dd56-4c52-a5b6",
            "patientId": "145",
            "status": "OTP_PENDING",
            "message": "Aadhaar OTP sent successfully to mobile linked with Aadhaar"
        }, indent=2),
        internal_logic=[
            "Validates the 12-digit Aadhaar number and patient mandatory fields.",
            "Retrieves active ABDM Gateway Bearer session token (auto-refreshed if expired).",
            "Encrypts Aadhaar number using ABDM official RSA public certificate.",
            "Calls ABDM v3 enrollment OTP endpoint and tracks transactionId against patientId in memory/disk store."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions (Gateway Auth)",
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/request/otp (Request Aadhaar OTP)"
        ]
    )

    # API 2
    format_api_entry(
        doc,
        api_num="2",
        name="Verify ABHA OTP (Enrolment Verification)",
        category="Milestone 1 (Base Contract)",
        method="POST",
        url="/api/abdm/patients/verify-otp",
        desc="Submits citizen OTP to ABDM, verifies Aadhaar identity, generates ABHANumber and ABHAAddress, and links to ProDoc record.",
        req_body=json.dumps({
            "patientId": "145",
            "transactionId": "TXN-ABHA-5fc4645d-dd56-4c52-a5b6",
            "otp": "123456"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "name": "Rohan Kumar Thakur",
            "gender": "M",
            "dob": "2008-10-08",
            "status": "VERIFIED",
            "message": "ABHA Enrolment verified successfully"
        }, indent=2),
        internal_logic=[
            "Retrieves active transactionId mapped to patientId.",
            "RSA-encrypts the 6-digit OTP using ABDM public certificate.",
            "Calls ABDM enrol by Aadhaar verification endpoint.",
            "Receives authenticated citizen JWT token and new ABHA credentials.",
            "Persists verified identity to disk cache (m1_linked_cache.json & m1_tokens_cache.json)."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions (Gateway Auth)",
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/enrol/byAadhaar (Verify OTP & Enrol)"
        ]
    )

    # API 3
    format_api_entry(
        doc,
        api_num="3",
        name="Search Existing ABHA",
        category="Milestone 1 (Base Contract)",
        method="POST",
        url="/api/abdm/abha/search",
        desc="Searches ABDM database for existing citizen ABHA profile using Mobile number, ABHA Number, or ABHA Address.",
        req_body=json.dumps({
            "patientId": "145",
            "searchType": "MOBILE",
            "searchValue": "8779441274"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "transactionId": "5fc4645d-dd56-4c52-a5b6-7bf41c8c3edc",
            "patientId": "145",
            "verificationRequired": True,
            "accounts": [
                {
                    "ABHANumber": "91372762677683",
                    "ABHAAddress": "thakurrohan2@sbx",
                    "name": "Rohan Kumar Thakur",
                    "gender": "M",
                    "dob": "2008-10-08",
                    "status": "ACTIVE"
                }
            ],
            "message": "ABHA accounts found. OTP required to verify."
        }, indent=2),
        internal_logic=[
            "Parses searchType (MOBILE, ABHA_NUMBER, ABHA_ADDRESS).",
            "Encrypts search value with ABDM public key.",
            "Calls ABDM Login Search / Request OTP endpoint.",
            "Returns found accounts and sets up authentication transaction reference."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions (Gateway Auth)",
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/profile/login/search (or /request/otp)"
        ]
    )

    # API 4
    format_api_entry(
        doc,
        api_num="4",
        name="Link Existing ABHA to ProDoc Patient",
        category="Milestone 1 (Base Contract)",
        method="POST",
        url="/api/abdm/abha/link-existing",
        desc="Links a previously verified ABHA identity to the ProDoc hospital patient record.",
        req_body=json.dumps({
            "patientId": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "regNo": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "status": "LINKED",
            "message": "ABHA linked to ProDoc patient record successfully"
        }, indent=2),
        internal_logic=[
            "Validates that citizen ABHA credentials exist and match verified session.",
            "Stores permanent linkage record in m1_linked_cache.json.",
            "Returns confirmation to ProDoc to save in hospital database."
        ],
        abdm_hits=0,
        abdm_calls=[]
    )

    # API 5
    format_api_entry(
        doc,
        api_num="5",
        name="Get Patient ABHA Profile",
        category="Milestone 1 (Base Contract)",
        method="GET",
        url="/api/abdm/patients/145/abha-profile",
        desc="Fetches full demographic profile for a linked patient from ABDM or persistent cache.",
        req_body="None (Path parameter patientId in URL). Also accepts POST with {'patientId': '145'}",
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "firstName": "Rohan",
            "middleName": "Kumar",
            "lastName": "Thakur",
            "name": "Rohan Kumar Thakur",
            "dob": "2008-10-08",
            "gender": "M",
            "mobile": "8779441274",
            "status": "ACTIVE",
            "message": "ABHA profile retrieved successfully"
        }, indent=2),
        internal_logic=[
            "Retrieves cached citizen token (X-token) for the patientId.",
            "Attempts live fetch from ABDM profile/account endpoint with X-token header.",
            "Falls back gracefully to cached profile if sandbox session is expired or offline."
        ],
        abdm_hits=1,
        abdm_calls=[
            "GET https://abhasbx.abdm.gov.in/abha/api/v3/profile/account"
        ]
    )

    # API 6
    format_api_entry(
        doc,
        api_num="6",
        name="Get ABHA Card (PDF / Base64)",
        category="Milestone 1 (Base Contract)",
        method="GET",
        url="/api/abdm/patients/145/abha-card",
        desc="Downloads the official graphical ABHA card (PDF or PNG) for the patient.",
        req_body="None (Path parameter patientId). Also accepts POST with {'patientId': '145', 'format': 'PDF'}",
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "format": "PDF",
            "cardData": "JVBERi0xLjQKJ...",
            "message": "ABHA card retrieved successfully"
        }, indent=2),
        internal_logic=[
            "Resolves user token for patientId.",
            "Sends request to ABDM ABHA Card endpoint with X-token.",
            "Encodes binary stream into base64 string for ProDoc."
        ],
        abdm_hits=1,
        abdm_calls=[
            "GET https://abhasbx.abdm.gov.in/abha/api/v3/profile/account/abha-card"
        ]
    )

    # API 7
    format_api_entry(
        doc,
        api_num="7",
        name="Get ABHA QR Code",
        category="Milestone 1 (Base Contract)",
        method="GET",
        url="/api/abdm/patients/145/abha-qr",
        desc="Retrieves the official ABDM QR code image for fast scan & share registration.",
        req_body="None (Path parameter patientId). Also accepts POST with {'patientId': '145'}",
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "qrCode": "data:image/png;base64,iVBORw0KGgoAAAANSUh...",
            "message": "ABHA QR code retrieved successfully"
        }, indent=2),
        internal_logic=[
            "Retrieves patient session token.",
            "Calls ABDM qrCode endpoint.",
            "Returns base64 data URI to render directly in ProDoc picture box."
        ],
        abdm_hits=1,
        abdm_calls=[
            "GET https://abhasbx.abdm.gov.in/abha/api/v3/profile/account/qrCode"
        ]
    )

    # API 8
    format_api_entry(
        doc,
        api_num="8",
        name="Register HIP Care Contexts",
        category="Milestone 2 (Base Contract)",
        method="POST",
        url="/api/abdm/hip/care-context/register",
        desc="Links hospital care encounters (OPD visits, lab tests, prescriptions) to the patient's ABHA address using 180-day linkToken.",
        req_body=json.dumps({
            "patientId": "145",
            "abhaAddress": "thakurrohan2@sbx",
            "patientReferenceNumber": "PRODOC-145",
            "name": "Rohan Kumar Thakur",
            "gender": "M",
            "yearOfBirth": 2008,
            "careContexts": [
                {
                    "referenceNumber": "OPD-2026-00145",
                    "display": "OPD Consultation - 2026-11-24"
                }
            ]
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "status": "SUCCESS",
            "patientId": "145",
            "transactionId": "TXN-CC-48DF1A0E",
            "linkedCareContexts": ["OPD-2026-00145"],
            "linkToken": "eyJhbGciOi...",
            "linkTokenExpiresAt": 1805495000,
            "linkTokenExpiresAtIso": "2027-05-23T05:24:14.000Z",
            "remainingDays": 180,
            "tokenSource": "PRODOC_DB_OR_CACHE",
            "message": "Care context linking completed successfully"
        }, indent=2),
        internal_logic=[
            "Validates or auto-generates 180-day patient linkToken with ABDM.",
            "Builds careContexts payload matching ABDM v3 HIP specification.",
            "Calls POST /v3/hip/link/carecontext.",
            "Direct webhook receiver catches asynchronous ABDM confirmation callback.",
            "Returns linkToken and exact expiration date so ProDoc can store it in DB."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/hip/v3/token/generate-token (If token expired)",
            "POST https://dev.abdm.gov.in/api/hiecm/hip/v3/link/carecontext"
        ]
    )

    # API 9
    format_api_entry(
        doc,
        api_num="9",
        name="Get Care Context Linking Status",
        category="Milestone 2 (Base Contract)",
        method="GET",
        url="/api/abdm/hip/care-context/status/TXN-CC-48DF1A0E",
        desc="Queries live status of an asynchronous care-context linking transaction.",
        req_body="None (Path parameter transactionId or abdm_request_id)",
        res_body=json.dumps({
            "success": True,
            "transactionId": "TXN-CC-48DF1A0E",
            "status": "SUCCESS",
            "patientId": "145",
            "abhaAddress": "thakurrohan2@sbx",
            "message": "Care context linking completed successfully"
        }, indent=2),
        internal_logic=[
            "Looks up transactionId in care_context_transactions store.",
            "Returns status updated by ABDM webhook callback (SUCCESS, PENDING, or FAILED)."
        ],
        abdm_hits=0,
        abdm_calls=[]
    )

    # API 10
    format_api_entry(
        doc,
        api_num="10",
        name="List Patient Care Contexts",
        category="Milestone 2 (Base Contract)",
        method="GET",
        url="/api/abdm/patients/145/care-contexts",
        desc="Lists all care contexts linked to a patient record in ProDoc.",
        req_body="None (Path parameter patientId)",
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "careContexts": [
                {
                    "referenceNumber": "OPD-145-001",
                    "display": "OPD Consultation - Patient 145",
                    "status": "LINKED"
                }
            ]
        }, indent=2),
        internal_logic=[
            "Queries all historical care-context records linked to patientId.",
            "Returns array of encounter reference numbers and display titles."
        ],
        abdm_hits=0,
        abdm_calls=[]
    )

    # =========================================================================
    # PART 2: EXTRA APIS (DEDICATED PRODOC OPD WORKFLOW)
    # =========================================================================
    h_p2 = doc.add_heading("3. EXTRA APIS (Dedicated ProDoc OPD Workflow & System Utilities)", level=1)
    h_p2.paragraph_format.space_before = Pt(18)
    h_p2.paragraph_format.space_after = Pt(8)
    for r in h_p2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(180, 83, 9)

    add_callout(
        doc,
        "PURPOSE OF EXTRA APIS",
        "These endpoints were specifically created to power the live ProDoc OPD UI screen (frmRegisterABHAPatient) "
        "and senior architectural requirements (internal 2-in-1 orchestration, zero-body button clicks, "
        "global auto-refreshing session, and zero-polling push webhook callbacks).",
        bg_color="FEF3C7",
        border_color="D97706"
    )

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Extra API 1
    format_api_entry(
        doc,
        api_num="EXTRA 1",
        name="Send OTP (Mobile / ABHA Address / ABHA Number)",
        category="Extra API: ProDoc OPD Flow",
        method="POST",
        url="/api/abdm/register-patient/send-otp",
        desc="Called by btnSendOTP_Click. Accepts 10-digit mobile number, ABHA number, or ABHA address, resolves the citizen identifier, encrypts it, and triggers an OTP from ABDM.",
        req_body=json.dumps({
            "mobile": "8779441274",
            "patientId": "145"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "transactionId": "5fc4645d-dd56-4c52-a5b6-7bf41c8c3edc",
            "patientId": "145",
            "message": "OTP sent successfully to registered mobile number"
        }, indent=2),
        internal_logic=[
            "Auto-resolves input identifier: supports mobile, 14-digit ABHA number, or username@sbx.",
            "Fetches Gateway Bearer token.",
            "RSA-encrypts the target loginId using ABDM public key.",
            "Calls ABDM profile login request OTP endpoint.",
            "Stores transaction mapping across patientId, mobile, and transactionId."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions (Gateway Auth)",
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/profile/login/request/otp (Request OTP)"
        ]
    )

    # Extra API 2
    format_api_entry(
        doc,
        api_num="EXTRA 2",
        name="Verify OTP & Return Accounts & Real Citizen DOB",
        category="Extra API: ProDoc OPD Flow",
        method="POST",
        url="/api/abdm/register-patient/verify-otp",
        desc="Called by btnVerifyOTP_Click. Submits entered OTP, extracts all linked citizen accounts, parses real DOB from JWT claims, and standardizes keys to ABHANumber & ABHAAddress.",
        req_body=json.dumps({
            "otp": "123456",
            "patientId": "145",
            "transactionId": "5fc4645d-dd56-4c52-a5b6-7bf41c8c3edc"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "message": "OTP Verified Successfully",
            "transactionId": "5fc4645d-dd56-4c52-a5b6-7bf41c8c3edc",
            "patientId": "145",
            "regNo": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "patientName": "Rohan Kumar Thakur",
            "gender": "M",
            "dob": "2008-10-08",
            "status": "ACTIVE",
            "accounts": [
                {
                    "ABHANumber": "91372762677683",
                    "ABHAAddress": "thakurrohan2@sbx",
                    "name": "Rohan Kumar Thakur",
                    "gender": "M",
                    "dob": "2008-10-08",
                    "status": "ACTIVE"
                }
            ]
        }, indent=2),
        internal_logic=[
            "RSA-encrypts the entered 6-digit OTP.",
            "Calls ABDM profile login verify endpoint.",
            "Extracts JWT claims and accounts list from response.",
            "Resolves citizen DOB from ABDM profile / claims.",
            "Normalizes keys strictly to ABHANumber and ABHAAddress.",
            "Caches user token for immediate subsequent profile lookup."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/profile/login/verify (Verify OTP)",
            "GET https://abhasbx.abdm.gov.in/abha/api/v3/profile/account (Profile snapshot)"
        ]
    )

    # Extra API 3
    format_api_entry(
        doc,
        api_num="EXTRA 3",
        name="Select Account & Get ABHA Profile (2-in-1 Internal Orchestration)",
        category="Extra API: ProDoc OPD Flow",
        method="POST",
        url="/api/abdm/register-patient/get-abha-profile",
        desc="Combined 2-in-1 endpoint called by btnSelectABHAAccount_Click. Requires ZERO BODY ({}) from VB.NET. Python internally calls ABDM Verify User followed by Get Profile Details.",
        req_body=json.dumps({}, indent=2) + "  // Empty body or {'patientId': '145'}",
        res_body=json.dumps({
            "success": True,
            "message": "Patient profile details retrieved successfully",
            "patientId": "145",
            "regNo": "145",
            "firstName": "Rohan",
            "middleName": "Kumar",
            "lastName": "Thakur",
            "name": "Rohan Kumar Thakur",
            "dob": "2008-10-08",
            "yearOfBirth": "2008",
            "monthOfBirth": "10",
            "dayOfBirth": "08",
            "gender": "M",
            "mobile": "8779441274",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "address": "plot no 14/b/3, road no 2, hari masjid, Mumbai",
            "pincode": "400043",
            "districtName": "MUMBAI SUBURBAN",
            "stateName": "MAHARASHTRA",
            "status": "ACTIVE"
        }, indent=2),
        internal_logic=[
            "Auto-resolves active patientId and transactionId from verified session.",
            "Internal Step 1: Calls ABDM POST /profile/login/verify/user with T-token to receive X-Token.",
            "Internal Step 2: Calls ABDM GET /profile/account with X-token to receive full profile breakdown.",
            "Splits name cleanly into firstName, middleName, lastName.",
            "Handles sandbox session expiry automatically via cache fallback so VB.NET never receives 400 error.",
            "Returns separated demographic fields ready for the ProDoc verification grid."
        ],
        abdm_hits=2,
        abdm_calls=[
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/profile/login/verify/user (Receive X-Token)",
            "GET https://abhasbx.abdm.gov.in/abha/api/v3/profile/account (Retrieve Profile Details)"
        ]
    )

    # Extra API 4
    format_api_entry(
        doc,
        api_num="EXTRA 4",
        name="Standalone Verify User Account",
        category="Extra API: ProDoc OPD Flow",
        method="POST",
        url="/api/abdm/register-patient/verify-user",
        desc="Standalone endpoint to execute the ABDM Verify User step independently if testing separate steps in Postman.",
        req_body=json.dumps({
            "patientId": "145",
            "ABHANumber": "91372762677683"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "message": "User verified successfully",
            "token": "eyJhbGciOi...",
            "patientId": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx"
        }, indent=2),
        internal_logic=[
            "Sends ABHANumber and transactionId with T-token header to ABDM.",
            "Saves returned X-Token to patient token cache.",
            "Includes session fallback to prevent 'Invalid T-token' error if sandbox OTP expired."
        ],
        abdm_hits=1,
        abdm_calls=[
            "POST https://abhasbx.abdm.gov.in/abha/api/v3/profile/login/verify/user"
        ]
    )

    # Extra API 5
    format_api_entry(
        doc,
        api_num="EXTRA 5",
        name="Register Patient ABHA Link",
        category="Extra API: ProDoc OPD Flow",
        method="POST",
        url="/api/abdm/register-patient/link",
        desc="Called by btnRegisterABHA_Click. Finalizes the registration and permanently binds citizen ABHA to hospital RegNo/PatientId.",
        req_body=json.dumps({
            "regNo": "145",
            "patientId": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "firstName": "Rohan",
            "middleName": "Kumar",
            "lastName": "Thakur",
            "dob": "2008-10-08",
            "gender": "M"
        }, indent=2),
        res_body=json.dumps({
            "success": True,
            "patientId": "145",
            "regNo": "145",
            "ABHANumber": "91372762677683",
            "ABHAAddress": "thakurrohan2@sbx",
            "status": "LINKED",
            "message": "Patient ABHA registration linked successfully"
        }, indent=2),
        internal_logic=[
            "Validates patient RegNo and ABHA credentials.",
            "Updates permanent local cache and disk file m1_linked_cache.json.",
            "Prepares patient for subsequent Milestone 2 Care Context linking."
        ],
        abdm_hits=0,
        abdm_calls=[]
    )

    # Extra API 6
    format_api_entry(
        doc,
        api_num="EXTRA 6",
        name="Global ABDM Session Token & Auto-Refresh Monitor",
        category="Extra API: System Utility",
        method="GET",
        url="/api/abdm/session/token",
        desc="Senior Requirement 1: Monitors the global ABDM Gateway Bearer token, auto-refreshing 5 minutes prior to expiry.",
        req_body="None",
        res_body=json.dumps({
            "success": True,
            "status": "ACTIVE",
            "session": {
                "is_valid": True,
                "expires_at": 1805495000,
                "expires_at_iso": "2026-11-24T12:00:00.000Z",
                "remaining_seconds": 1250
            },
            "message": "Global session accessToken is active and auto-refreshes on expiry"
        }, indent=2),
        internal_logic=[
            "Checks cached Gateway Bearer session.",
            "Triggers automatic background refresh if remaining duration < 300 seconds."
        ],
        abdm_hits=1,
        abdm_calls=[
            "POST https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions (Only on refresh)"
        ]
    )

    # Extra API 7
    format_api_entry(
        doc,
        api_num="EXTRA 7",
        name="Direct Webhook Push Callback Receiver",
        category="Extra API: System Utility",
        method="POST",
        url="/api/abdm/webhook/callback",
        desc="Senior Requirement 3: Dedicated webhook receiver that immediately accepts ABDM asynchronous push callbacks without polling.",
        req_body=json.dumps({
            "requestId": "uuid",
            "resp": {"requestId": "uuid"},
            "acknowledgement": {"status": "SUCCESS"}
        }, indent=2),
        res_body=json.dumps({
            "status": "acknowledged",
            "action": "push-received",
            "message": "I have received this message",
            "abdm_request_id": "uuid"
        }, indent=2),
        internal_logic=[
            "Zero polling. ABDM pushes event directly to Python endpoint.",
            "Immediately replies with acknowledgment: 'I have received this message'.",
            "Updates matching pending transaction in memory/disk."
        ],
        abdm_hits=0,
        abdm_calls=[]
    )

    # Save document
    filename = "ProDoc_ABDM_API_Documentation.docx"
    doc.save(filename)
    print(f"Successfully generated {filename} ({os.path.getsize(filename):,} bytes)!")

if __name__ == "__main__":
    build_word_document()
