import os
import json
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    """Sets background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding in dxa (1 pt = 20 dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_code_block(doc, text):
    """Adds a formatted monospace code block with background shading and border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F3F4F6")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border only (accent teal)
    tcPr = cell._element.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="0284C7"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(31, 41, 55)

def add_callout(doc, title, text, bg_color="EFF6FF", border_color="1D4ED8"):
    """Adds a stylized alert/callout box."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    tcPr = cell._element.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="28" w:space="0" w:color="{border_color}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run_t = p.add_run(f"{title}: ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(9.5)
    run_t.font.color.rgb = RGBColor(30, 58, 138)
    
    run_b = p.add_run(text)
    run_b.font.name = "Calibri"
    run_b.font.size = Pt(9.5)
    run_b.font.color.rgb = RGBColor(31, 41, 55)

def format_api_entry(doc, api_num, name, category, method, url, desc, req_body, res_body, internal_logic, abdm_hits, abdm_calls):
    """Formats one complete API entry in senior-ready pen-paper style."""
    h = doc.add_heading(f"API {api_num}: {name}", level=2)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(4)
    for r in h.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(14)
        r.font.color.rgb = RGBColor(15, 76, 129)

    # Metadata table
    tbl = doc.add_table(rows=4, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    meta = [
        ("Category & Milestone", category),
        ("Method & URL", f"{method} {url}"),
        ("ABDM APIs Hit by Python", f"{abdm_hits} Call(s) to ABDM Sandbox"),
        ("Description / Role", desc)
    ]
    
    col_widths = [Inches(1.8), Inches(4.7)]
    for i, (k, v) in enumerate(meta):
        row = tbl.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = col_widths[0], col_widths[1]
        set_cell_background(c0, "F8FAFC")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, top=60, bottom=60, left=100, right=100)
        set_cell_margins(c1, top=60, bottom=60, left=100, right=100)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(1)
        p0.paragraph_format.space_after = Pt(1)
        r0 = p0.add_run(k)
        r0.bold = True
        r0.font.name = "Calibri"
        r0.font.size = Pt(9)
        r0.font.color.rgb = RGBColor(71, 85, 105)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(1)
        p1.paragraph_format.space_after = Pt(1)
        r1 = p1.add_run(v)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9)
        if k == "Method & URL":
            r1.bold = True
            r1.font.color.rgb = RGBColor(14, 116, 144)
        elif k == "ABDM APIs Hit by Python":
            r1.bold = True
            r1.font.color.rgb = RGBColor(180, 83, 9) if abdm_hits > 0 else RGBColor(22, 101, 52)
        else:
            r1.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 1. ProDoc Request Body
    p_req = doc.add_paragraph()
    p_req.paragraph_format.space_before = Pt(4)
    p_req.paragraph_format.space_after = Pt(2)
    r = p_req.add_run("1. Request Body (ProDoc sends to Python):")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(15, 76, 129)
    add_code_block(doc, req_body)

    # 2. Python Response
    p_res = doc.add_paragraph()
    p_res.paragraph_format.space_before = Pt(6)
    p_res.paragraph_format.space_after = Pt(2)
    r = p_res.add_run("2. Response Body (Python returns to ProDoc):")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(15, 76, 129)
    add_code_block(doc, res_body)

    # 3. What happens in Python server
    p_srv = doc.add_paragraph()
    p_srv.paragraph_format.space_before = Pt(6)
    p_srv.paragraph_format.space_after = Pt(2)
    r = p_srv.add_run("3. What happens inside the Python Server (Internal Logic):")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(15, 76, 129)
    
    for step in internal_logic:
        p_step = doc.add_paragraph(style='List Bullet')
        p_step.paragraph_format.space_before = Pt(1)
        p_step.paragraph_format.space_after = Pt(1)
        r_step = p_step.add_run(step)
        r_step.font.name = "Calibri"
        r_step.font.size = Pt(9.5)
        r_step.font.color.rgb = RGBColor(51, 65, 85)

    # 4. ABDM Sandbox Calls
    p_abdm = doc.add_paragraph()
    p_abdm.paragraph_format.space_before = Pt(6)
    p_abdm.paragraph_format.space_after = Pt(2)
    r = p_abdm.add_run(f"4. ABDM External Calls ({abdm_hits} API call(s) executed to Govt Gateway):")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(180, 83, 9) if abdm_hits > 0 else RGBColor(22, 101, 52)
    
    if abdm_calls:
        for call in abdm_calls:
            p_call = doc.add_paragraph(style='List Bullet')
            p_call.paragraph_format.space_before = Pt(1)
            p_call.paragraph_format.space_after = Pt(1)
            r_call = p_call.add_run(call)
            r_call.font.name = "Consolas"
            r_call.font.size = Pt(8.5)
            r_call.font.color.rgb = RGBColor(30, 41, 59)
    else:
        p_call = doc.add_paragraph(style='List Bullet')
        p_call.paragraph_format.space_before = Pt(1)
        p_call.paragraph_format.space_after = Pt(1)
        r_call = p_call.add_run("0 external ABDM calls. Handled locally within Python Middleware cache and ProDoc data persistence.")
        r_call.font.name = "Calibri"
        r_call.font.size = Pt(9)
        r_call.font.color.rgb = RGBColor(22, 101, 52)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

print("Helper functions defined successfully!")
