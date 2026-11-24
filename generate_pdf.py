import os
import json
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    pdf_filename = "ProDoc_ABDM_API_Documentation.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F4C81"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F4C81"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )
    h1_extra_style = ParagraphStyle(
        "Heading1_Extra_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#B45309"),
        spaceBefore=16,
        spaceAfter=6,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0F4C81"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    h2_extra_style = ParagraphStyle(
        "Heading2_Extra_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#B45309"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    subhead_style = ParagraphStyle(
        "Subhead_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F4C81"),
        spaceBefore=4,
        spaceAfter=2,
        keepWithNext=True,
    )
    normal_style = ParagraphStyle(
        "Normal_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B"),
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2,
    )
    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#1F2937"),
    )
    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E3A8A"),
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("ProDoc HMIS ↔ ABDM Middleware Integration Manual", title_style))
    story.append(Paragraph("Comprehensive API Specification: Base Contract (M1/M2) & Dedicated ProDoc OPD Endpoints", subtitle_style))

    # Executive Callout
    callout_data = [[
        Paragraph(
            "<b>EXECUTIVE AUDIT SUMMARY:</b> This document details all APIs created for the ProDoc HMIS integration "
            "with ABDM. It is divided into <b>Base Specification APIs</b> (10 out of 16 created from the Excel/XML doc, "
            "covering 100% of Milestone 1 and Milestone 2) and <b>Extra APIs</b> (specialized for the live ProDoc OPD UI "
            "<code>frmRegisterABHAPatient</code> and internal senior architectural requirements). "
            "All responses strictly use standardized capital keys <b>ABHANumber</b> and <b>ABHAAddress</b>.",
            callout_style
        )
    ]]
    callout_table = Table(callout_data, colWidths=[523])
    callout_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#1D4ED8")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # Summary Table
    story.append(Paragraph("1. API Architecture & Inventory Breakdown", h1_style))
    
    summary_data = [
        ["Milestone / Category", "Total in Doc", "Created & Ready", "Status", "Description"],
        ["Milestone 1 (M1): Patient Enrolment & Discovery", "7", "7", "100% Created", "APIs 1 to 7 fully operational"],
        ["Milestone 2 (M2): HIP Care Context Linking", "3", "3", "100% Created", "APIs 8 to 10 fully operational"],
        ["Milestone 3 (M3): HIU Consent & Health Data", "6", "0", "Roadmap", "Scheduled for HIU records retrieval phase"],
        ["EXTRA APIS: ProDoc OPD Dedicated Flow", "-", "5", "100% Created", "Specialized endpoints for frmRegisterABHAPatient"],
    ]
    t_summary = Table(summary_data, colWidths=[150, 65, 80, 85, 143])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.white),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FEF3C7")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 10))

    # Section 2: Internal Auto-Mapping & Token Management Architecture
    story.append(Paragraph("2. Internal Auto-Mapping & Token Architecture", h1_style))
    auto_pdf_data = [
        [Paragraph("<b>Engine / Feature</b>", normal_style), Paragraph("<b>Internal Mechanism in Code</b>", normal_style), Paragraph("<b>Impact on ProDoc & Hospital Workflow</b>", normal_style)],
        [Paragraph("<b>GLOBAL_ACCESS_TOKEN</b>", normal_style), Paragraph("Stored in global memory variables. <code>get_access_token()</code> checks if <code>now < expiry - 30s</code>. If expired or not set, calls Gateway <code>/sessions</code> and auto-refreshes.", normal_style), Paragraph("Zero token handling in VB.NET. Calls never fail with 401 Unauthorized.", normal_style)],
        [Paragraph("<b>X-LINK-TOKEN (180 Days)</b>", normal_style), Paragraph("Evaluated via <code>is_link_token_valid()</code>. If missing or expired, Python calls <code>/token/generate-token</code>, receives token via webhook, and returns <code>linkToken</code> + 180-day expiry to ProDoc.", normal_style), Paragraph("ProDoc stores linkToken in DB. Links care contexts for 6 months without re-authenticating.", normal_style)],
        [Paragraph("<b>txnId Auto-Mapping</b>", normal_style), Paragraph("Send OTP maps <code>txnId</code> across 4 keys: txnId, patientId, mobile, abhaAddress. Verify OTP & get-profile auto-resolve txnId from active session.", normal_style), Paragraph("VB.NET clicks 'Select Account' with zero body <code>{}</code> without copying txnId.", normal_style)],
        [Paragraph("<b>T-token vs X-token Routing</b>", normal_style), Paragraph("ABDM requires T-token for <code>/verify/user</code>, and X-token for <code>/profile/account</code>. Python dynamically formats appropriate headers internally.", normal_style), Paragraph("Developer doesn't need to learn dual-token difference; fully abstracted.", normal_style)]
    ]
    t_auto = Table(auto_pdf_data, colWidths=[110, 240, 173])
    t_auto.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.white),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.white),
    ]))
    story.append(t_auto)
    story.append(Spacer(1, 10))

    # Section 3: When does store.py get into action
    story.append(Paragraph("3. When Does store.py Get in Action? (Lifecycle)", h1_style))
    timeline_pdf = [
        ["Timeline / Event", "store.py Functions Triggered", "Action & Architectural Impact"],
        ["1. Server Boot (t = 0)", "_load_cache(), _load_m1_cache()", "Loads 5 JSON files. Evaluates JWT exp timestamps to eliminate expired tokens."],
        ["2. Send OTP", "store.m1_otp_txns[txn_id]", "Tracks transaction metadata across patientId, mobile, and txnId for auto-matching."],
        ["3. Verify OTP", "save_m1_token(), save_m1_profile()", "Persists authenticated citizen token, real DOB, and accounts to disk."],
        ["4. Select Account", "get_m1_token(), get_m1_profile()", "CRUCIAL FALLBACK: If ABDM sandbox 2-min session expired, provides cached profile for 200 OK."],
        ["5. Register Link", "save_m1_linked(reg_no, data)", "Permanently links hospital patient RegNo to ABHANumber & ABHAAddress."],
        ["6. Care Context", "is_link_token_valid(), save_token()", "Verifies 180-day linkToken validity. Generates fresh token if expired. Tracks txnId."],
        ["7. Webhook Push", "seen_uuids.add(), pending_events.set()", "Dedupes callback by UUID, logs acknowledgment, and unblocks waiting async calls."]
    ]
    t_tbl = Table(timeline_pdf, colWidths=[95, 145, 283])
    t_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_tbl)
    story.append(Spacer(1, 10))

    # Helper function to add API block
    def add_api_pdf(num, name, category, method, url, desc, req_json, res_json, logic_list, abdm_hits, abdm_urls, is_extra=False):
        elements = []
        head_s = h2_extra_style if is_extra else h2_style
        badge_color = "#B45309" if is_extra else "#0F4C81"
        
        elements.append(Paragraph(f"API {num}: {name}", head_s))
        
        meta_table_data = [
            [Paragraph("<b>Category:</b> " + category, normal_style), Paragraph(f"<b>ABDM Calls:</b> <font color='{badge_color}'><b>{abdm_hits} Call(s) to Govt Gateway</b></font>", normal_style)],
            [Paragraph("<b>Route:</b> <code>" + method + " " + url + "</code>", normal_style), Paragraph("<b>Description:</b> " + desc, normal_style)]
        ]
        meta_tbl = Table(meta_table_data, colWidths=[240, 283])
        meta_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_tbl)
        elements.append(Spacer(1, 4))

        # Request & Response side by side or stacked
        req_box = Table([[Paragraph(f"<pre>{req_json}</pre>", code_style)]], colWidths=[255])
        req_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
            ("LINELEFT", (0, 0), (0, -1), 2, colors.HexColor("#0284C7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        res_box = Table([[Paragraph(f"<pre>{res_json}</pre>", code_style)]], colWidths=[260])
        res_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
            ("LINELEFT", (0, 0), (0, -1), 2, colors.HexColor("#10B981")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        boxes_table = Table([
            [Paragraph("<b>1. ProDoc Request Body:</b>", subhead_style), Paragraph("<b>2. Python Response:</b>", subhead_style)],
            [req_box, res_box]
        ], colWidths=[260, 263])
        boxes_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(boxes_table)
        elements.append(Spacer(1, 4))

        # Logic
        elements.append(Paragraph("<b>3. Internal Python Logic & Workflow:</b>", subhead_style))
        for item in logic_list:
            elements.append(Paragraph(f"• {item}", bullet_style))

        # ABDM external calls
        elements.append(Paragraph(f"<b>4. ABDM External Calls ({abdm_hits} Hits):</b>", subhead_style))
        if abdm_urls:
            for u in abdm_urls:
                elements.append(Paragraph(f"• <font color='#0F4C81'><b>{u}</b></font>", bullet_style))
        else:
            elements.append(Paragraph("• <i>0 external calls. Executed locally using ProDoc cache / data store.</i>", bullet_style))

        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=8))
        return elements

    # =========================================================================
    # PART 1: BASE CONTRACT APIS
    # =========================================================================
    story.append(Paragraph("2. Base Specification APIs (From Excel/XML Contract)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F4C81"), spaceAfter=8))

    # API 1
    story.extend(add_api_pdf(
        "1", "Register Patient / Generate ABHA OTP", "Milestone 1 (Base Contract)",
        "POST", "/api/abdm/patients/register",
        "Enrols patient by Aadhaar OTP. Python RSA-encrypts Aadhaar with ABDM certificate.",
        json.dumps({"patientId": "145", "name": "Rohan Thakur", "dob": "2008-10-08", "gender": "M", "mobile": "8779441274", "aadhaarNumber": "987654321012", "consent": True}, indent=2),
        json.dumps({"success": True, "transactionId": "TXN-ABHA-5fc4645d", "patientId": "145", "status": "OTP_PENDING", "message": "Aadhaar OTP sent successfully"}, indent=2),
        [
            "Validates 12-digit Aadhaar number and patient details.",
            "Retrieves active Bearer Gateway session token (auto-refreshed if expired).",
            "RSA-encrypts Aadhaar number using official ABDM public key.",
            "Calls ABDM v3 enrollment endpoint and maps transactionId to patientId."
        ],
        2,
        ["POST /api/hiecm/gateway/v3/sessions (Gateway Auth)", "POST /abha/api/v3/enrollment/request/otp (Request Aadhaar OTP)"]
    ))

    # API 2
    story.extend(add_api_pdf(
        "2", "Verify ABHA OTP (Enrolment Verification)", "Milestone 1 (Base Contract)",
        "POST", "/api/abdm/patients/verify-otp",
        "Verifies Aadhaar OTP, generates ABHANumber and ABHAAddress, and saves to ProDoc record.",
        json.dumps({"patientId": "145", "transactionId": "TXN-ABHA-5fc4645d", "otp": "123456"}, indent=2),
        json.dumps({"success": True, "patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "name": "Rohan Kumar Thakur", "dob": "2008-10-08", "status": "VERIFIED"}, indent=2),
        [
            "Retrieves active Aadhaar transaction reference for patientId.",
            "RSA-encrypts the 6-digit OTP using ABDM public certificate.",
            "Receives citizen JWT token and new ABHA credentials from ABDM.",
            "Persists verified identity to disk cache (m1_linked_cache.json & m1_tokens_cache.json)."
        ],
        2,
        ["POST /api/hiecm/gateway/v3/sessions (Gateway Auth)", "POST /abha/api/v3/enrollment/enrol/byAadhaar (Verify OTP & Enrol)"]
    ))

    # API 3
    story.extend(add_api_pdf(
        "3", "Search Existing ABHA", "Milestone 1 (Base Contract)",
        "POST", "/api/abdm/abha/search",
        "Searches ABDM database for existing citizen ABHA profile using Mobile, ABHA Number, or Address.",
        json.dumps({"patientId": "145", "searchType": "MOBILE", "searchValue": "8779441274"}, indent=2),
        json.dumps({"success": True, "transactionId": "5fc4645d-dd56", "patientId": "145", "verificationRequired": True, "accounts": [{"ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "name": "Rohan Kumar Thakur", "dob": "2008-10-08"}]}, indent=2),
        [
            "Parses searchType (MOBILE, ABHA_NUMBER, ABHA_ADDRESS).",
            "Encrypts search value with ABDM public key.",
            "Calls ABDM Login Search endpoint and formats account list for verification."
        ],
        2,
        ["POST /api/hiecm/gateway/v3/sessions (Gateway Auth)", "POST /abha/api/v3/profile/login/search (or /request/otp)"]
    ))

    # API 4
    story.extend(add_api_pdf(
        "4", "Link Existing ABHA to ProDoc Patient", "Milestone 1 (Base Contract)",
        "POST", "/api/abdm/abha/link-existing",
        "Links an authenticated ABHA identity to the ProDoc hospital patient record.",
        json.dumps({"patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx"}, indent=2),
        json.dumps({"success": True, "patientId": "145", "regNo": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "status": "LINKED"}, indent=2),
        [
            "Validates that citizen credentials match active verified session.",
            "Stores permanent linkage record in m1_linked_cache.json."
        ],
        0,
        []
    ))

    # API 5
    story.extend(add_api_pdf(
        "5", "Get Patient ABHA Profile", "Milestone 1 (Base Contract)",
        "GET", "/api/abdm/patients/145/abha-profile",
        "Fetches full demographic profile for a linked patient from ABDM or persistent cache.",
        "None (Path parameter patientId in URL). Also accepts POST with {'patientId': '145'}",
        json.dumps({"success": True, "patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "firstName": "Rohan", "lastName": "Thakur", "dob": "2008-10-08", "status": "ACTIVE"}, indent=2),
        [
            "Retrieves cached citizen token (X-token) for patientId.",
            "Calls ABDM profile/account endpoint with X-token header.",
            "Falls back gracefully to cached profile if sandbox session is expired."
        ],
        1,
        ["GET /abha/api/v3/profile/account"]
    ))

    # API 6
    story.extend(add_api_pdf(
        "6", "Get ABHA Card (PDF / Base64)", "Milestone 1 (Base Contract)",
        "GET", "/api/abdm/patients/145/abha-card",
        "Downloads official graphical ABHA card (PDF or PNG) for the patient.",
        "None (Path parameter patientId). Also accepts POST with {'patientId': '145', 'format': 'PDF'}",
        json.dumps({"success": True, "patientId": "145", "format": "PDF", "cardData": "JVBERi0xLjQKJ...", "message": "ABHA card retrieved successfully"}, indent=2),
        [
            "Passes citizen user token to ABDM Card endpoint.",
            "Receives binary stream and encodes into base64 string for ProDoc."
        ],
        1,
        ["GET /abha/api/v3/profile/account/abha-card"]
    ))

    # API 7
    story.extend(add_api_pdf(
        "7", "Get ABHA QR Code", "Milestone 1 (Base Contract)",
        "GET", "/api/abdm/patients/145/abha-qr",
        "Retrieves the official ABDM QR code image for fast scan & share registration.",
        "None (Path parameter patientId). Also accepts POST with {'patientId': '145'}",
        json.dumps({"success": True, "patientId": "145", "qrCode": "data:image/png;base64,iVBORw0KGgo...", "message": "ABHA QR code retrieved successfully"}, indent=2),
        [
            "Calls ABDM qrCode endpoint with patient session token.",
            "Returns base64 data URI to render directly in ProDoc picture box."
        ],
        1,
        ["GET /abha/api/v3/profile/account/qrCode"]
    ))

    # API 8
    story.extend(add_api_pdf(
        "8", "Register HIP Care Contexts", "Milestone 2 (Base Contract)",
        "POST", "/api/abdm/hip/care-context/register",
        "Links hospital care encounters (OPD visits, lab tests) to citizen ABHA address using 180-day linkToken.",
        json.dumps({"patientId": "145", "abhaAddress": "thakurrohan2@sbx", "patientReferenceNumber": "PRODOC-145", "name": "Rohan Kumar Thakur", "yearOfBirth": 2008, "careContexts": [{"referenceNumber": "OPD-2026-00145", "display": "OPD Consultation - 2026-11-24"}]}, indent=2),
        json.dumps({"success": True, "status": "SUCCESS", "patientId": "145", "transactionId": "TXN-CC-48DF1A0E", "linkToken": "eyJhbGciOi...", "remainingDays": 180, "message": "Care context linking completed"}, indent=2),
        [
            "Validates or auto-generates 180-day linkToken with ABDM.",
            "Calls POST /v3/hip/link/carecontext.",
            "Direct webhook receiver catches asynchronous ABDM confirmation callback.",
            "Returns linkToken + expiry so ProDoc can store in hospital DB."
        ],
        2,
        ["POST /api/hiecm/hip/v3/token/generate-token (If expired)", "POST /api/hiecm/hip/v3/link/carecontext"]
    ))

    # API 9
    story.extend(add_api_pdf(
        "9", "Get Care Context Linking Status", "Milestone 2 (Base Contract)",
        "GET", "/api/abdm/hip/care-context/status/TXN-CC-48DF1A0E",
        "Queries live status of an asynchronous care-context linking transaction.",
        "None (Path parameter transactionId)",
        json.dumps({"success": True, "transactionId": "TXN-CC-48DF1A0E", "status": "SUCCESS", "patientId": "145", "message": "Care context linking completed"}, indent=2),
        [
            "Looks up transactionId in care_context_transactions store.",
            "Returns status updated by ABDM webhook callback (SUCCESS, PENDING, or FAILED)."
        ],
        0,
        []
    ))

    # API 10
    story.extend(add_api_pdf(
        "10", "List Patient Care Contexts", "Milestone 2 (Base Contract)",
        "GET", "/api/abdm/patients/145/care-contexts",
        "Lists all care contexts linked to a patient record in ProDoc.",
        "None (Path parameter patientId)",
        json.dumps({"success": True, "patientId": "145", "careContexts": [{"referenceNumber": "OPD-145-001", "display": "OPD Consultation - Patient 145", "status": "LINKED"}]}, indent=2),
        [
            "Queries all historical care-context records linked to patientId.",
            "Returns array of encounter reference numbers and display titles."
        ],
        0,
        []
    ))

    # =========================================================================
    # PART 2: EXTRA APIS (DEDICATED OPD WORKFLOW)
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. EXTRA APIS (Dedicated ProDoc OPD Workflow & System Utilities)", h1_extra_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#B45309"), spaceAfter=8))

    # Extra API 1
    story.extend(add_api_pdf(
        "EXTRA 1", "Send OTP (Mobile / ABHA Address / ABHA Number)", "Extra API: ProDoc OPD Flow",
        "POST", "/api/abdm/register-patient/send-otp",
        "Called by btnSendOTP_Click. Resolves mobile, ABHA number, or ABHA address, encrypts it, and triggers OTP from ABDM.",
        json.dumps({"mobile": "8779441274", "patientId": "145"}, indent=2),
        json.dumps({"success": True, "transactionId": "5fc4645d-dd56-4c52-a5b6", "patientId": "145", "message": "OTP sent successfully to registered mobile number"}, indent=2),
        [
            "Auto-resolves input identifier: supports mobile, 14-digit ABHA number, or username@sbx.",
            "RSA-encrypts the target loginId using ABDM public key.",
            "Calls ABDM profile login request OTP endpoint.",
            "Stores transaction mapping across patientId, mobile, and transactionId."
        ],
        2,
        ["POST /api/hiecm/gateway/v3/sessions (Gateway Auth)", "POST /abha/api/v3/profile/login/request/otp (Request OTP)"],
        is_extra=True
    ))

    # Extra API 2
    story.extend(add_api_pdf(
        "EXTRA 2", "Verify OTP & Return Accounts & Real Citizen DOB", "Extra API: ProDoc OPD Flow",
        "POST", "/api/abdm/register-patient/verify-otp",
        "Called by btnVerifyOTP_Click. Submits entered OTP, extracts citizen accounts, parses real DOB from JWT claims, and standardizes keys.",
        json.dumps({"otp": "123456", "patientId": "145", "transactionId": "5fc4645d-dd56-4c52-a5b6"}, indent=2),
        json.dumps({"success": True, "message": "OTP Verified Successfully", "transactionId": "5fc4645d", "patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "dob": "2008-10-08", "accounts": [{"ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "name": "Rohan Kumar Thakur", "dob": "2008-10-08"}]}, indent=2),
        [
            "RSA-encrypts the entered 6-digit OTP.",
            "Calls ABDM profile login verify endpoint.",
            "Extracts JWT claims and accounts list from response.",
            "Resolves citizen DOB from ABDM profile / claims.",
            "Normalizes keys strictly to ABHANumber and ABHAAddress.",
            "Caches user token for immediate subsequent profile lookup."
        ],
        2,
        ["POST /abha/api/v3/profile/login/verify (Verify OTP)", "GET /abha/api/v3/profile/account (Profile snapshot)"],
        is_extra=True
    ))

    # Extra API 3
    story.extend(add_api_pdf(
        "EXTRA 3", "Select Account & Get ABHA Profile (2-in-1 Internal Orchestration)", "Extra API: ProDoc OPD Flow",
        "POST", "/api/abdm/register-patient/get-abha-profile",
        "Combined 2-in-1 endpoint called by btnSelectABHAAccount_Click. Requires ZERO BODY ({}) from VB.NET. Python internally calls Verify User + Get Profile Details.",
        json.dumps({}, indent=2) + "  // Empty body or {'patientId': '145'}",
        json.dumps({"success": True, "message": "Profile retrieved", "patientId": "145", "firstName": "Rohan", "middleName": "Kumar", "lastName": "Thakur", "name": "Rohan Kumar Thakur", "dob": "2008-10-08", "gender": "M", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "districtName": "MUMBAI SUBURBAN"}, indent=2),
        [
            "Auto-resolves active patientId and transactionId from verified session.",
            "Internal Step 1: Calls ABDM POST /profile/login/verify/user with T-token to receive X-Token.",
            "Internal Step 2: Calls ABDM GET /profile/account with X-token to receive full profile breakdown.",
            "Splits name cleanly into firstName, middleName, lastName.",
            "Handles sandbox session expiry automatically via cache fallback so VB.NET never receives 400 error.",
            "Returns separated demographic fields ready for the ProDoc verification grid."
        ],
        2,
        ["POST /abha/api/v3/profile/login/verify/user (Receive X-Token)", "GET /abha/api/v3/profile/account (Retrieve Profile Details)"],
        is_extra=True
    ))

    # Extra API 4
    story.extend(add_api_pdf(
        "EXTRA 4", "Standalone Verify User Account", "Extra API: ProDoc OPD Flow",
        "POST", "/api/abdm/register-patient/verify-user",
        "Standalone endpoint to execute ABDM Verify User step independently if testing separate steps in Postman.",
        json.dumps({"patientId": "145", "ABHANumber": "91372762677683"}, indent=2),
        json.dumps({"success": True, "message": "User verified successfully", "token": "eyJhbGciOi...", "patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx"}, indent=2),
        [
            "Sends ABHANumber and transactionId with T-token header to ABDM.",
            "Saves returned X-Token to patient token cache.",
            "Includes session fallback to prevent 'Invalid T-token' error if sandbox OTP expired."
        ],
        1,
        ["POST /abha/api/v3/profile/login/verify/user"],
        is_extra=True
    ))

    # Extra API 5
    story.extend(add_api_pdf(
        "EXTRA 5", "Register Patient ABHA Link", "Extra API: ProDoc OPD Flow",
        "POST", "/api/abdm/register-patient/link",
        "Called by btnRegisterABHA_Click. Finalizes registration and permanently binds citizen ABHA to hospital RegNo/PatientId.",
        json.dumps({"regNo": "145", "patientId": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "name": "Rohan Kumar Thakur", "dob": "2008-10-08", "gender": "M"}, indent=2),
        json.dumps({"success": True, "patientId": "145", "regNo": "145", "ABHANumber": "91372762677683", "ABHAAddress": "thakurrohan2@sbx", "status": "LINKED", "message": "Patient ABHA registration linked successfully"}, indent=2),
        [
            "Validates patient RegNo and ABHA credentials.",
            "Updates permanent local cache and disk file m1_linked_cache.json.",
            "Prepares patient for subsequent Milestone 2 Care Context linking."
        ],
        0,
        [],
        is_extra=True
    ))

    # Build PDF
    doc.build(story)
    print(f"Successfully generated {pdf_filename} ({os.path.getsize(pdf_filename):,} bytes)!")

if __name__ == "__main__":
    generate_pdf()
