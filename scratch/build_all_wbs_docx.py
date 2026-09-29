#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FocusFlow — Complete Generator for 7 WBS DOCX Documents
"""

import os
import zipfile
import xml.etree.ElementTree as ET

TEMPLATE_PATH = "docs_ute/(1) PROJECT CHARTER & STATEMENT OF WORK (SOW).docx"
OUTPUT_DIR = "docs_ute"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml"
}

def qn(tag):
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"

def create_element(tag, attrs=None):
    el = ET.Element(qn(tag))
    if attrs:
        for k, v in attrs.items():
            if ":" in k:
                el.set(qn(k), str(v))
            else:
                el.set(k, str(v))
    return el

def add_run(p, text, bold=False, italic=False, color="1f1f1f", size=20, style=None):
    r = create_element("w:r")
    rPr = create_element("w:rPr")
    
    font_name = "Google Sans" if (style and ("Heading" in style or "Title" in style)) else "Google Sans Text"
    rPr.append(create_element("w:rFonts", {
        "w:ascii": font_name,
        "w:hAnsi": font_name,
        "w:cs": font_name
    }))
    
    if bold:
        rPr.append(create_element("w:b"))
        rPr.append(create_element("w:bCs"))
    if italic:
        rPr.append(create_element("w:i"))
        rPr.append(create_element("w:iCs"))
    if color:
        rPr.append(create_element("w:color", {"w:val": color}))
    if size:
        rPr.append(create_element("w:sz", {"w:val": str(size)}))
        rPr.append(create_element("w:szCs", {"w:val": str(size)}))
        
    r.append(rPr)
    t = create_element("w:t", {"xml:space": "preserve"})
    t.text = text
    r.append(t)
    p.append(r)
    return r

def make_para(text="", style=None, bold=False, italic=False, color="1f1f1f", size=20, align=None, space_after=120, space_before=0):
    p = create_element("w:p")
    pPr = create_element("w:pPr")
    
    if style:
        pPr.append(create_element("w:pStyle", {"w:val": style}))
    if align:
        pPr.append(create_element("w:jc", {"w:val": align}))
        
    spacing_attrs = {"w:line": "276", "w:lineRule": "auto"}
    if space_after is not None:
        spacing_attrs["w:after"] = str(space_after)
    if space_before is not None:
        spacing_attrs["w:before"] = str(space_before)
    pPr.append(create_element("w:spacing", spacing_attrs))
    p.append(pPr)
    
    if text:
        add_run(p, text, bold=bold, italic=italic, color=color, size=size, style=style)
        
    return p

def make_heading(text, level=1):
    sizes = {1: 26, 2: 22, 3: 20}
    befores = {1: 240, 2: 180, 3: 120}
    afters = {1: 100, 2: 80, 3: 60}
    return make_para(text, style=f"Heading{level}", bold=True, color="1f1f1f", size=sizes.get(level, 20), space_before=befores.get(level, 120), space_after=afters.get(level, 80))

def make_bullet(text, bold_prefix=None, level=0):
    p = create_element("w:p")
    pPr = create_element("w:pPr")
    pPr.append(create_element("w:spacing", {"w:line": "276", "w:lineRule": "auto", "w:after": "80", "w:before": "0"}))
    pPr.append(create_element("w:ind", {"w:left": str(360 * (level + 1)), "w:hanging": "240"}))
    p.append(pPr)
    
    bullet_symbol = "•  " if level == 0 else "–  "
    add_run(p, bullet_symbol, bold=True, color="1f1f1f", size=20)
    
    if bold_prefix:
        add_run(p, bold_prefix, bold=True, color="1f1f1f", size=20)
    if text:
        add_run(p, text, bold=False, color="1f1f1f", size=20)
        
    return p

def make_cell(text, is_header=False, width_dxa=1872, bold=False, italic=False, align="left"):
    tc = create_element("w:tc")
    tcPr = create_element("w:tcPr")
    tcPr.append(create_element("w:tcW", {"w:w": str(width_dxa), "w:type": "dxa"}))
    
    tcBorders = create_element("w:tcBorders")
    for b_name in ["top", "left", "bottom", "right"]:
        tcBorders.append(create_element(f"w:{b_name}", {
            "w:val": "single", "w:sz": "4", "w:space": "0", "w:color": "000000"
        }))
    tcPr.append(tcBorders)
    
    shd_color = "e9eef6" if is_header else "f8fafd"
    tcPr.append(create_element("w:shd", {"w:val": "clear", "w:color": "auto", "w:fill": shd_color}))
    
    tcMar = create_element("w:tcMar")
    tcMar.append(create_element("w:top", {"w:w": "100", "w:type": "dxa"}))
    tcMar.append(create_element("w:bottom", {"w:w": "100", "w:type": "dxa"}))
    tcMar.append(create_element("w:left", {"w:w": "140", "w:type": "dxa"}))
    tcMar.append(create_element("w:right", {"w:w": "140", "w:type": "dxa"}))
    tcPr.append(tcMar)
    
    tcPr.append(create_element("w:vAlign", {"w:val": "center" if is_header else "top"}))
    tc.append(tcPr)
    
    p = create_element("w:p")
    pPr = create_element("w:pPr")
    pPr.append(create_element("w:spacing", {"w:after": "40", "w:before": "40", "w:line": "240", "w:lineRule": "auto"}))
    if align:
        pPr.append(create_element("w:jc", {"w:val": align}))
    p.append(pPr)
    
    add_run(p, text, bold=(True if is_header else bold), italic=italic, color="1f1f1f", size=18)
    tc.append(p)
    return tc

def make_table(col_widths, headers, data_rows):
    tbl = create_element("w:tbl")
    tblPr = create_element("w:tblPr")
    tblPr.append(create_element("w:tblStyle", {"w:val": "TableNormal"}))
    total_w = sum(col_widths)
    tblPr.append(create_element("w:tblW", {"w:w": str(total_w), "w:type": "dxa"}))
    tblPr.append(create_element("w:jc", {"w:val": "center"}))
    
    tblBorders = create_element("w:tblBorders")
    for b_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        tblBorders.append(create_element(f"w:{b_name}", {
            "w:val": "single", "w:sz": "4", "w:space": "0", "w:color": "000000"
        }))
    tblPr.append(tblBorders)
    tblPr.append(create_element("w:tblLayout", {"w:type": "fixed"}))
    tbl.append(tblPr)
    
    tblGrid = create_element("w:tblGrid")
    for w in col_widths:
        tblGrid.append(create_element("w:gridCol", {"w:w": str(w)}))
    tbl.append(tblGrid)
    
    if headers:
        tr_h = create_element("w:tr")
        trPr_h = create_element("w:trPr")
        trPr_h.append(create_element("w:tblHeader"))
        tr_h.append(trPr_h)
        for i, h_text in enumerate(headers):
            tr_h.append(make_cell(h_text, is_header=True, width_dxa=col_widths[i], align="center"))
        tbl.append(tr_h)
        
    for row in data_rows:
        tr = create_element("w:tr")
        for i, val in enumerate(row):
            tr.append(make_cell(str(val), is_header=False, width_dxa=col_widths[i]))
        tbl.append(tr)
        
    return tbl

def make_metadata_table(items):
    col_widths = [2600, 6760] # Total 9360 dxa
    return make_table(col_widths, None, items)

def make_callout(title, text):
    p = create_element("w:p")
    pPr = create_element("w:pPr")
    pPr.append(create_element("w:pBdr"))
    left_bdr = create_element("w:left", {"w:val": "single", "w:sz": "18", "w:space": "8", "w:color": "1a73e8"})
    pPr.find(qn("w:pBdr")).append(left_bdr)
    pPr.append(create_element("w:shd", {"w:val": "clear", "w:color": "auto", "w:fill": "f1f3f4"}))
    pPr.append(create_element("w:ind", {"w:left": "240", "w:right": "240"}))
    pPr.append(create_element("w:spacing", {"w:before": "120", "w:after": "120", "w:line": "276", "w:lineRule": "auto"}))
    p.append(pPr)
    
    if title:
        add_run(p, title + "\n", bold=True, color="1a73e8", size=20)
    add_run(p, text, bold=False, italic=True, color="3c4043", size=19)
    return p

def save_docx(body_elements, filename):
    out_path = os.path.join(OUTPUT_DIR, filename)
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as zin:
        xml_content = zin.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        body = tree.find(qn("w:body"))
        
        sectPr = body.find(qn("w:sectPr"))
        body.clear()
        
        for el in body_elements:
            body.append(el)
            
        if sectPr is not None:
            body.append(sectPr)
            
        new_doc_xml = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
        
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_doc_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))
                    
    print(f"-> Generated: {out_path}")

print("Docx generator core ready.")
