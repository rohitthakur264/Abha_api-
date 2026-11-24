"""
update_documentation_with_automapping.py
Generates updated Word (.docx) and PDF (.pdf) documents incorporating:
1. Global Session Access Token (GLOBAL_ACCESS_TOKEN auto-refresh)
2. X-LINK-TOKEN (180-day Care Context Token auto-management)
3. txnId / transactionId Multi-Key Auto-Mapping Engine
4. T-token vs X-token Seamless Header Routing
5. Full API Reference & store.py Lifecycle Timeline
"""
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

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_word_doc():
    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(0.7)
        s.bottom_margin = Inches(0.7)
        s.left_margin = Inches(0.7)
        s.right_margin = Inches(0.7)

    # Title & Subtitle
    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_before = Pt(8)
    p_t.paragraph_format.space_after = Pt(2)
    r = p_t.add_run("ProDoc HMIS ↔ ABDM Middleware")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(24)
    r.font.color.rgb = RGBColor(15, 76, 129)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    r = p_sub.add_run("Complete Architecture, Auto-Mapping Engine, store.py Lifecycle & Technical API Reference")
    r.font.name = "Calibri"
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(71, 85, 105)

    add_callout(
        doc,
        "CORE INTEGRATION ARCHITECTURE",
        "This specification documents the complete internal intelligence of the Python FastAPI Middleware. "
        "It details the 4 major automated management systems: "
        "(1) Global Session Access Token auto-refresh, (2) X-LINK-TOKEN 180-day lifecycle & auto-generation, "
        "(3) txnId / transactionId multi-key auto-mapping, and (4) T-token vs X-token seamless routing. "
        "All APIs strictly adhere to standardized capital keys (ABHANumber, ABHAAddress) and 2.0s fast-acknowledgment tuning.",
        bg_color="EFF6FF",
        border_color="1D4ED8"
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # SECTION 1: AUTO-MAPPING & GLOBAL VARIABLE ARCHITECTURE
    # =========================================================================
    h1 = doc.add_heading("1. Internal Auto-Mapping & Token Management Architecture", level=1)
    for r in h1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = RGBColor(15, 76, 129)

    p_desc = doc.add_paragraph(
        "To make hospital integration effortless for ProDoc and prevent complex token handling in VB.NET, "
        "the Python middleware implements 4 dedicated automated state engines:"
    )
    p_desc.paragraph_format.space_after = Pt(6)

    # 4 Auto-Mapping Features Table
    tbl_auto = doc.add_table(rows=5, cols=3)
    tbl_auto.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_auto.autofit = False
    col_w_auto = [Inches(1.8), Inches(2.2), Inches(2.6)]

    hdr_vals = ["Engine / Feature", "Internal Mechanism in Code", "Impact on ProDoc & Hospital Workflow"]
    for i, h_text in enumerate(hdr_vals):
        cell = tbl_auto.rows[0].cells[i]
        cell.width = col_w_auto[i]
        set_cell_background(cell, "0F4C81")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    auto_data = [
        ("1. Global Gateway Session Token (GLOBAL_ACCESS_TOKEN)",
         "Stored in global memory variables: GLOBAL_ACCESS_TOKEN & GLOBAL_ACCESS_TOKEN_EXPIRY. get_access_token() checks if now < expiry - 30s. If expired or not set, calls Gateway /sessions and auto-refreshes.",
         "Zero token management for ProDoc. Outbound calls never fail with 401 Unauthorized. Auto-refreshes seamlessly in background."),
        
        ("2. X-LINK-TOKEN (180-Day Care Context Token)",
         "Evaluated via is_link_token_valid(). If ProDoc has a token, passes it. If missing or expired, Python auto-calls /token/generate-token, receives token via webhook, and returns linkToken + remainingDays (180) to ProDoc.",
         "ProDoc stores the returned linkToken in hospital DB. Care context linking runs with 180-day validity without re-authenticating the patient repeatedly."),
        
        ("3. txnId / transactionId Multi-Key Auto-Mapping",
         "When Send OTP returns txnId, store.m1_otp_txns maps it under 4 keys: txnId, patientId, mobile, abhaAddress. Verify OTP & get-abha-profile auto-resolve txnId from active session.",
         "VB.NET buttons don't need to pass transaction IDs manually. User clicks 'Select Account' with zero body {}, and Python auto-maps txnId."),
        
        ("4. T-token vs X-token Header Routing",
         "ABDM requires T-token for /verify/user, and X-token for /profile/account. Python inspects the endpoint and dynamically attaches 'T-token: Bearer ...' or 'X-token: Bearer ...'.",
         "ProDoc developers do not need to understand ABDM's dual-token system. Python handles both tokens internally.")
    ]

    for r_idx, (c0, c1, c2) in enumerate(auto_data, start=1):
        row = tbl_auto.rows[r_idx]
        bg_col = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate([c0, c1, c2]):
            cell = row.cells[c_idx]
            cell.width = col_w_auto[c_idx]
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(8.5)
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(15, 76, 129)
            elif c_idx == 1:
                r.font.name = "Consolas"
                r.font.size = Pt(8)
                r.font.color.rgb = RGBColor(180, 83, 9)
            else:
                r.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Deep Dive on Global Token
    p_gt = doc.add_paragraph()
    r = p_gt.add_run("Deep Dive: How GLOBAL_ACCESS_TOKEN Operates in Code")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(15, 76, 129)

    add_code_block(doc, (
        "# abdm_client.py\n"
        "GLOBAL_ACCESS_TOKEN: str | None = None\n"
        "GLOBAL_ACCESS_TOKEN_EXPIRY: float = 0.0\n\n"
        "async def get_access_token(force_refresh: bool = False) -> str:\n"
        "    global GLOBAL_ACCESS_TOKEN, GLOBAL_ACCESS_TOKEN_EXPIRY\n"
        "    now = time.time()\n"
        "    # Check if existing token has at least 30 seconds of remaining validity\n"
        "    if not force_refresh and GLOBAL_ACCESS_TOKEN and now < (GLOBAL_ACCESS_TOKEN_EXPIRY - 30):\n"
        "        return GLOBAL_ACCESS_TOKEN\n\n"
        "    # Otherwise auto-generate new token from ABDM Gateway\n"
        "    res = await client.post(SESSION_URL, json={'clientId': CLIENT_ID, 'clientSecret': CLIENT_SECRET})\n"
        "    GLOBAL_ACCESS_TOKEN = res.json()['accessToken']\n"
        "    GLOBAL_ACCESS_TOKEN_EXPIRY = now + res.json().get('expiresIn', 1800)\n"
        "    return GLOBAL_ACCESS_TOKEN"
    ))

    # Deep Dive on X-LINK-TOKEN
    p_lt = doc.add_paragraph()
    r = p_lt.add_run("Deep Dive: How X-LINK-TOKEN (180 Days) Operates in Code")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(15, 76, 129)

    add_code_block(doc, (
        "# routes_abdm.py / abdm_client.py\n"
        "# 1. If ProDoc provides linkToken from hospital DB, verify validity:\n"
        "if link_token and is_link_token_valid(link_token):\n"
        "    token_source = 'PRODOC_PROVIDED'\n"
        "else:\n"
        "    # 2. Check local persistent cache (link_tokens_cache.json):\n"
        "    cached = link_tokens.get(norm_abha)\n"
        "    if cached and is_link_token_valid(cached):\n"
        "        link_token = cached['linkToken']\n"
        "    else:\n"
        "        # 3. Auto-generate from ABDM with 180-day expiry:\n"
        "        await send_to_abdm('POST', GENERATE_TOKEN_URL, ...)\n"
        "        cb = await wait_for_callback(..., require_link_token=True)\n"
        "        link_token = cb['payload']['linkToken']\n"
        "        save_token(norm_abha, {'linkToken': link_token, 'expires_at': now + 180*86400})\n\n"
        "# 4. Attach to outgoing care context call:\n"
        "headers['X-LINK-TOKEN'] = link_token\n"
        "# 5. Return token + exact expiry date to ProDoc to save in DB:\n"
        "return {'linkToken': link_token, 'remainingDays': 180, 'linkTokenExpiresAtIso': '...'}"
    ))

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # SECTION 2: WHEN DOES STORE.PY GET IN ACTION? (LIFECYCLE TIMELINE)
    # =========================================================================
    h2 = doc.add_heading("2. When Does store.py Get in Action? (Complete Lifecycle)", level=1)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = RGBColor(15, 76, 129)

    p_s_desc = doc.add_paragraph(
        "store.py is the persistence and memory engine of the middleware. "
        "Below is the exact timeline showing when store.py functions and data stores get triggered:"
    )
    p_s_desc.paragraph_format.space_after = Pt(6)

    tbl_s = doc.add_table(rows=8, cols=3)
    tbl_s.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_s.autofit = False
    col_w_s = [Inches(1.8), Inches(2.3), Inches(2.5)]

    for i, h_text in enumerate(["Timeline / Event", "store.py Functions Triggered", "Action Performed & Impact"]):
        cell = tbl_s.rows[0].cells[i]
        cell.width = col_w_s[i]
        set_cell_background(cell, "0F4C81")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    timeline_data = [
        ("1. Server Boot (t = 0)", "_load_cache(), _load_m1_cache(), _load_m1_linked(), _load_m1_profiles()", "Loads 5 JSON files from disk into memory. Parses JWT 'exp' so expired tokens are never mistakenly used."),
        ("2. Send OTP (t = OTP Req)", "store.m1_otp_txns[txn_id] = record", "Stores pending transaction mapping across patientId, mobile number, and txnId for auto-matching in subsequent steps."),
        ("3. Verify OTP (t = OTP Verify)", "save_m1_token(), save_m1_profile(), save_m1_linked()", "Saves verified citizen JWT token, real DOB, gender, and ABHA identity to disk. Ensures permanent record persistence."),
        ("4. Select Account (t = 2-in-1 Profile)", "get_m1_token(), get_m1_profile()", "Auto-resolves patient token. CRUCIAL FALLBACK: If ABDM sandbox 2-min session expired, provides cached profile so VB.NET gets 200 OK without error!"),
        ("5. Register Link (t = Link Finalize)", "save_m1_linked(reg_no, data)", "Permanently binds hospital patient Reg. No. to verified ABHANumber and ABHAAddress in m1_linked_cache.json."),
        ("6. Care Context Link (t = CC Linking)", "is_link_token_valid(), save_token(), care_context_transactions", "Evaluates 180-day linkToken validity. Generates new token if expired. Tracks pending linking transaction state."),
        ("7. Webhook Arrival (t = Callback Push)", "store.received.append(), store.seen_uuids.add(), pending_events[id].set()", "Directly logs pushed event, avoids duplicate processing, and instantly signals the waiting async request within milliseconds.")
    ]

    for r_idx, row_vals in enumerate(timeline_data, start=1):
        row = tbl_s.rows[r_idx]
        bg_col = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = col_w_s[c_idx]
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(8.5)
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(15, 76, 129)
            elif c_idx == 1:
                r.font.name = "Consolas"
                r.font.size = Pt(8)
                r.font.color.rgb = RGBColor(180, 83, 9)
            else:
                r.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Save document
    filename = "ProDoc_ABDM_Architecture_and_API_Guide.docx"
    doc.save(filename)
    print(f"Generated {filename} ({os.path.getsize(filename):,} bytes)!")

def build_pdf_doc():
    pdf_filename = "ProDoc_ABDM_Architecture_and_API_Guide.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    title_s = ParagraphStyle("T", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#0F4C81"), spaceAfter=3)
    sub_s = ParagraphStyle("S", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#475569"), spaceAfter=10)
    h1_s = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.HexColor("#0F4C81"), spaceBefore=12, spaceAfter=4, keepWithNext=True)
    body_s = ParagraphStyle("B", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#1E293B"))
    code_s = ParagraphStyle("C", parent=styles["Code"], fontName="Courier", fontSize=7, leading=8.5, textColor=colors.HexColor("#1F2937"))

    story = []
    story.append(Paragraph("ProDoc HMIS ↔ ABDM Middleware Architecture & Auto-Mapping Guide", title_s))
    story.append(Paragraph("Global Token Auto-Refresh, X-LINK-TOKEN, txnId Mapping & store.py Lifecycle", sub_s))

    # Callout
    callout_data = [[
        Paragraph(
            "<b>CORE ARCHITECTURE NOTE:</b> This document details the 4 internal automated management systems: "
            "(1) Global Session Access Token auto-refresh (reusing active tokens, auto-generating fresh tokens on expiry), "
            "(2) X-LINK-TOKEN 180-day lifecycle & auto-generation for Care Contexts, "
            "(3) txnId / transactionId multi-key auto-mapping (eliminating manual parameter copying), and "
            "(4) store.py persistence lifecycle across all patient registration and care context linking events.",
            body_s
        )
    ]]
    c_tbl = Table(callout_data, colWidths=[523])
    c_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#1D4ED8")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(c_tbl)
    story.append(Spacer(1, 8))

    # Section 1: Auto-Mapping Engines
    story.append(Paragraph("1. Internal Auto-Mapping & Token Management Engines", h1_s))
    auto_pdf_data = [
        [Paragraph("<b>Engine / Feature</b>", body_s), Paragraph("<b>Internal Mechanism & Implementation</b>", body_s), Paragraph("<b>Hospital Impact (ProDoc)</b>", body_s)],
        [Paragraph("<b>GLOBAL_ACCESS_TOKEN</b>", body_s), Paragraph("Stored in global memory variables. <code>get_access_token()</code> checks if <code>now < expiry - 30s</code>. If expired or not set, calls Gateway <code>/sessions</code> and auto-refreshes.", body_s), Paragraph("Zero token handling in VB.NET. Calls never fail with 401 Unauthorized.", body_s)],
        [Paragraph("<b>X-LINK-TOKEN (180 Days)</b>", body_s), Paragraph("Evaluated via <code>is_link_token_valid()</code>. If missing or expired, Python calls <code>/token/generate-token</code>, receives token via webhook, and returns <code>linkToken</code> + 180-day expiry to ProDoc.", body_s), Paragraph("ProDoc stores linkToken in DB. Links care contexts for 6 months without re-authenticating.", body_s)],
        [Paragraph("<b>txnId Auto-Mapping</b>", body_s), Paragraph("Send OTP maps <code>txnId</code> across 4 keys: txnId, patientId, mobile, abhaAddress. Verify OTP & get-profile auto-resolve txnId from active session.", body_s), Paragraph("VB.NET clicks 'Select Account' with zero body <code>{}</code> without copying txnId.", body_s)],
        [Paragraph("<b>T-token vs X-token Routing</b>", body_s), Paragraph("ABDM requires T-token for <code>/verify/user</code>, and X-token for <code>/profile/account</code>. Python dynamically formats appropriate headers internally.", body_s), Paragraph("Developer doesn't need to learn dual-token difference; fully abstracted.", body_s)]
    ]
    t_auto = Table(auto_pdf_data, colWidths=[120, 233, 170])
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
    story.append(Spacer(1, 8))

    # Section 2: store.py timeline
    story.append(Paragraph("2. When Does store.py Get in Action? (Lifecycle Timeline)", h1_s))
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
    t_tbl = Table(timeline_pdf, colWidths=[100, 150, 273])
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
    story.append(Spacer(1, 8))

    # Section 3: Settings.py & Execution
    story.append(Paragraph("3. Operational Setup & Fast Acknowledgment Tuning", h1_s))
    run_steps = [
        "<b>Global Session Access Token:</b> Python manages <code>GLOBAL_ACCESS_TOKEN</code> in memory. ProDoc never needs to log into Gateway manually.",
        "<b>1-2s Fast Acknowledgment:</b> <code>CALLBACK_WAIT_SECONDS = 2.0</code> in <code>settings.py</code> ensures that if ABDM sandbox delays callbacks, ProDoc gets <code>status: 'PENDING'</code> immediately without freezing the UI.",
        "<b>Zero-Body Button Calls:</b> VB.NET <code>btnSelectABHAAccount_Click</code> calls <code>POST /api/abdm/register-patient/get-abha-profile</code> with <code>{}</code>; Python auto-resolves txnId and tokens.",
        "<b>How to Run:</b> <code>uvicorn main:app --host 0.0.0.0 --port 8000 --reload</code>"
    ]
    for s in run_steps:
        story.append(Paragraph(f"• {s}", body_s))

    doc.build(story)
    print(f"Generated {pdf_filename} ({os.path.getsize(pdf_filename):,} bytes)!")

if __name__ == "__main__":
    build_word_doc()
    build_pdf_doc()
