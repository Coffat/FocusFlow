#!/usr/bin/env python3
import os
import zipfile
import xml.etree.ElementTree as ET

TEMPLATE_PATH = "docs_ute/PROJECT STATUS REPORT.docx"

# Namespace dictionary
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml"
}

def make_para(text, style=None, bold=False, italic=False, color="1f1f1f", size=None, align=None, space_after=120, space_before=0):
    p = ET.Element("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
    pPr = ET.SubElement(p, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
    
    if style:
        ET.SubElement(pPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": style
        })
        
    if align:
        ET.SubElement(pPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}jc", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": align
        })
        
    spacing_attrs = {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}line": "276",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lineRule": "auto"
    }
    if space_after:
        spacing_attrs["{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after"] = str(space_after)
    if space_before:
        spacing_attrs["{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before"] = str(space_before)
    ET.SubElement(pPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing", spacing_attrs)
    
    # Run properties
    r = ET.SubElement(p, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")
    rPr = ET.SubElement(r, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
    
    font_name = "Google Sans" if (style and "Heading" in style) else "Google Sans Text"
    ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii": font_name,
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi": font_name,
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cs": font_name
    })
    
    if bold:
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b")
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bCs")
    if italic:
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i")
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}iCs")
    if color:
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": color
        })
    if size:
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": str(size)
        })
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}szCs", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": str(size)
        })
        
    t = ET.SubElement(r, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t", {
        "{http://www.w3.org/XML/1998/namespace}space": "preserve"
    })
    t.text = text
    return p

def make_cell(text, is_header=False, width_dxa=1872):
    tc = ET.Element("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
    tcPr = ET.SubElement(tc, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcPr")
    
    # Borders
    tcBorders = ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcBorders")
    for b_name in ["top", "left", "bottom", "right"]:
        ET.SubElement(tcBorders, f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{b_name}", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "single",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz": "6",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space": "0",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color": "000000"
        })
        
    # Shading
    shd_color = "e9eef6" if is_header else "f8fafd"
    ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "clear",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color": "auto",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill": shd_color
    })
    
    # Margins
    tcMar = ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcMar")
    ET.SubElement(tcMar, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}top", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": "120", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "dxa"
    })
    ET.SubElement(tcMar, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bottom", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": "120", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "dxa"
    })
    ET.SubElement(tcMar, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}left", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": "180", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "dxa"
    })
    ET.SubElement(tcMar, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}right", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": "180", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "dxa"
    })
    
    ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vAlign", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "top"
    })
    
    # Content paragraph
    p = ET.SubElement(tc, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
    pPr = ET.SubElement(p, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
    ET.SubElement(pPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after": "120",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before": "120",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}line": "276",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lineRule": "auto"
    })
    
    r = ET.SubElement(p, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")
    rPr = ET.SubElement(r, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
    ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii": "Google Sans Text",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi": "Google Sans Text",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cs": "Google Sans Text"
    })
    if is_header:
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b")
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bCs")
    ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "1f1f1f"
    })
    
    t = ET.SubElement(r, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t", {
        "{http://www.w3.org/XML/1998/namespace}space": "preserve"
    })
    t.text = text
    return tc

def make_table(style_name, col_widths, headers, data_rows):
    tbl = ET.Element("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl")
    tblPr = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblPr")
    ET.SubElement(tblPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblStyle", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": style_name
    })
    total_w = sum(col_widths)
    ET.SubElement(tblPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblW", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": str(total_w),
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "dxa"
    })
    ET.SubElement(tblPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}jc", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "left"
    })
    tblBorders = ET.SubElement(tblPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblBorders")
    for b_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        ET.SubElement(tblBorders, f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{b_name}", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "single",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz": "6",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space": "0",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color": "000000"
        })
    ET.SubElement(tblPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblLayout", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type": "fixed"
    })
    
    # Grid
    tblGrid = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblGrid")
    for w in col_widths:
        ET.SubElement(tblGrid, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}gridCol", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": str(w)
        })
        
    # Header Row
    tr_h = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
    trPr_h = ET.SubElement(tr_h, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}trPr")
    ET.SubElement(trPr_h, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblHeader")
    for i, h_text in enumerate(headers):
        tr_h.append(make_cell(h_text, is_header=True, width_dxa=col_widths[i]))
        
    # Data Rows
    for row in data_rows:
        tr = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
        for i, val in enumerate(row):
            tr.append(make_cell(val, is_header=False, width_dxa=col_widths[i]))
            
    return tbl

print("Helper functions defined successfully.")
