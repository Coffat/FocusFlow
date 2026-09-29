#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FocusFlow — Full Generator for 7 WBS DOCX Documents
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
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "xml": "http://www.w3.org/XML/1998/namespace"
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

# ==============================================================================
# 1. WBS 1.1 BUILDER
# ==============================================================================
def build_wbs_1_1():
    elements = []
    # Title
    elements.append(make_para("BÁO CÁO KHẢO SÁT NHU CẦU TỰ HỌC & NGHIÊN CỨU ĐỐI SÁNH GIẢI PHÁP (BENCHMARKING)", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 1.1 — KHÁM PHÁ BÀI TOÁN & PHÂN TÍCH HIỆN TRẠNG HỌC THUẬT", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    # Metadata
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 1.1: Khảo sát nhu cầu tự học và nghiên cứu đối sánh giải pháp (Benchmarking)"),
        ("Sinh Viên Phụ Trách", "Phan Đình Duẩn (Senior BA / Requirements Engineer)"),
        ("Thời Gian Thực Hiện", "28/08/2026 – 02/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Căn Cứ Đánh Giá", "Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 Mức 5"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Hoàn thành 100% (Deliverable Approved)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    # Section 1
    elements.append(make_heading("1. TỔNG QUAN & MỤC ĐÍCH NGHIÊN CỨU", level=1))
    elements.append(make_heading("1.1. Bối cảnh tự học và suy hao tri thức kỷ nguyên số", level=2))
    elements.append(make_para("Trong kỷ nguyên trí tuệ nhân tạo và chuyển đổi số, chu kỳ suy hao tri thức công nghệ rút ngắn xuống chỉ còn 2–3 năm. Nhu cầu tự học suốt đời (Self-Directed Lifelong Learning) và tái đào tạo kỹ năng (Reskilling/Upskilling) trở thành năng lực bắt buộc. Tuy nhiên, các khóa học đóng gói (MOOCs) thường chỉ cung cấp tài nguyên tĩnh, thiếu tính thích ứng theo năng lực và thời gian thực tế, dẫn đến tỷ lệ bỏ cuộc giữa chừng trong tự học lên tới 85% – 90%."))
    elements.append(make_heading("1.2. Mục tiêu của nghiên cứu", level=2))
    elements.append(make_bullet("Thiết lập luận cứ thực chứng khách quan dựa trên khảo sát người dùng thực tế kết hợp khoa học nhận thức, chứng minh bài toán FocusFlow giải quyết là có thật và cấp bách (Rubric TC1 Mức 5).", bold_prefix="Minh chứng tính cấp thiết: "))
    elements.append(make_bullet("Phân tích đa chiều 4 nhóm giải pháp hiện hữu trên thị trường để chỉ ra các điểm nghẽn kỹ thuật và trải nghiệm chưa được giải quyết.", bold_prefix="Đối sánh giải pháp (Benchmarking): "))
    elements.append(make_bullet("Ánh xạ từ nỗi đau thực tế thành các yêu cầu kỹ thuật và 5 KPI định lượng cho hồ sơ đồ án tốt nghiệp.", bold_prefix="Định hình cơ sở yêu cầu: "))
    
    # Section 2
    elements.append(make_heading("2. CƠ SỞ LÝ THUYẾT & PHƯƠNG PHÁP LUẬN KHẢO SÁT", level=1))
    elements.append(make_para("Nghiên cứu của FocusFlow được neo vào 3 mô hình lý thuyết khoa học giáo dục và nhận thức đã được công nhận quốc tế:"))
    elements.append(make_bullet("Quá trình tự học bắt buộc phải trải qua vòng lặp 3 pha: Chuẩn bị/Kế hoạch (Forethought) -> Thực thi/Tập trung (Performance) -> Tự suy ngẫm/Đánh giá (Self-Reflection). FocusFlow thiết kế 4 module khép kín bám sát đúng chu trình này.", bold_prefix="1. Thuyết Tự điều chỉnh Học tập (SRL - Zimmerman, 2002): "))
    elements.append(make_bullet("Bộ nhớ làm việc (Working Memory) của con người có giới hạn. Việc phải chuyển đổi qua lại giữa 3-4 công cụ rời rạc làm tăng vọt Tải ngoại lai (Extraneous Load), triệt tiêu tài nguyên não bộ dành cho tiếp thu kiến thức.", bold_prefix="2. Thuyết Tải Nhận thức (Cognitive Load Theory - Sweller, 1988): "))
    elements.append(make_bullet("Ý chí và khả năng ra quyết định là nguồn năng lượng hữu hạn. Mất 30-45 phút kéo thả sắp xếp lịch thủ công làm cạn kiệt năng lượng trước khi kịp học.", bold_prefix="3. Hiện tượng Suy hao Ý chí & Mệt mỏi Kế hoạch (Baumeister et al., 1998): "))
    elements.append(make_para("Đề tài áp dụng phương pháp nghiên cứu kết hợp đa nguồn (Multi-method Triangulation): Kết hợp Nghiên cứu thứ cấp từ các báo cáo quốc tế uy tín (Science 2019, ACM CHI 2005, Stack Overflow 2023), Thực nghiệm đánh giá công thái học (Cognitive Walkthrough trên 6 công cụ hiện hữu trong 4 tuần), và Thiết kế sẵn sàng bộ công cụ khảo sát 15 tiêu chí cho pha UAT."))
    
    # Section 3
    elements.append(make_heading("3. BÁO CÁO & PHÂN TÍCH DỮ LIỆU THỰC CHỨNG", level=1))
    elements.append(make_heading("3.1. Dữ liệu Bối cảnh & Phân khúc Người tự học Công nghệ", level=2))
    elements.append(make_para("Dữ liệu thống kê ngành và các công trình khoa học quốc tế uy tín xác thực tính cấp bách của bài toán:"))
    sample_headers = ["Nguồn dữ liệu / Báo cáo", "Chỉ số thực chứng", "Ý nghĩa khoa học đối với FocusFlow"]
    sample_data = [
        ["Stack Overflow Developer Survey (2023)", "73.7% lập trình viên tự học kỹ năng mới", "Nhu cầu tự học công nghệ ngoài giảng đường là rất lớn và phổ biến"],
        ["Tạp chí Science (Reich & Ruipérez-Valiente, 2019)", "Tỷ lệ bỏ cuộc tự học online lên tới 85% – 95%", "Người tự học thiếu cấu trúc thích ứng và công cụ duy trì kỷ luật"],
        ["Nghiên cứu của TS. Gloria Mark (ACM CHI 2005)", "Mất 23 phút 15 giây để hồi phục tập trung", "Sự phân mảnh công cụ gây suy giảm nghiêm trọng hiệu suất tiếp thu"]
    ]
    elements.append(make_table([3000, 3160, 3200], sample_headers, sample_data))
    
    elements.append(make_heading("3.2. Phân tích 3 Nỗi đau Cốt tử qua Thực nghiệm Công thái học", level=2))
    elements.append(make_para("Kết quả thực nghiệm mô phỏng lộ trình tự học 4 tuần (Cognitive Walkthrough) làm sáng tỏ 3 rào cản chí mạng:"))
    elements.append(make_bullet("Mất 45–60 phút chỉ để tìm kiếm và chia nhỏ lộ trình thủ công; dễ rơi vào bẫy lên lịch quá lạc quan. Các chatbot thông thường chỉ sinh văn bản rời rạc, trôi dạt trong chatbox và không tạo thành đầu việc quản lý được.", bold_prefix="Nỗi đau 1 — Rào cản phân rã mục tiêu (Decomposition Barrier): "))
    elements.append(make_bullet("Người học phải mở đồng thời 3–4 ứng dụng (Calendar, Notion, Todoist, Timer). Mất 8–12 phút đầu buổi chỉ để chuẩn bị, gây phân tâm nhận thức và 70% không lưu lại được tóm tắt (Key Takeaways) buổi học.", bold_prefix="Nỗi đau 2 — Quá tải và phân mảnh công cụ (Tool Fragmentation): "))
    elements.append(make_bullet("Các ứng dụng lịch truyền thống là lịch sự kiện tĩnh. Khi bị trễ hạn 2–3 ngày, việc kéo thả lại từng ô lịch mất 20–30 phút, gây suy hao ý chí và khiến người học nản chí bỏ xó toàn bộ lộ trình.", bold_prefix="Nỗi đau 3 — Đứt gãy kỷ luật khi có biến cố (Rigid Planning Failure): "))
    
    elements.append(make_heading("3.3. Hạn chế của nghiên cứu & Nguy cơ sai lệch (Threats to Validity)", level=2))
    elements.append(make_bullet("Dữ liệu thứ cấp quốc tế mang tính khái quát vĩ mô. Đề tài kiểm soát bằng cách tinh chỉnh tham số thiết kế (khung giờ tối 20:00–22:30 Mode B) bám sát lịch sinh hoạt thực tế của sinh viên CNTT tại Việt Nam.", bold_prefix="Khái quát hóa dữ liệu thứ cấp: "))
    elements.append(make_bullet("Thực nghiệm mô phỏng bởi nhóm tác giả có thể chịu ảnh hưởng chủ quan. Đề tài kiểm soát bằng việc áp dụng nguyên tắc Nielsen's Usability Heuristics và đối chiếu với Thuyết Tải nhận thức.", bold_prefix="Nguy cơ thiên vị người nghiên cứu: "))
    elements.append(make_bullet("Đề tài cam kết thực hiện pha Đánh giá Chấp nhận Người dùng (UAT Testing) độc lập trên hệ thống hoàn thiện với >= 10 người dùng thật, đo tự động Task Completion >= 90% và điểm SUS >= 80/100 (TC2.7).", bold_prefix="Cam kết nghiệm thu UAT: "))
    
    # Section 4
    elements.append(make_heading("4. NGHIÊN CỨU ĐỐI SÁNH GIẢI PHÁP (BENCHMARKING - TC1 MỨC 5)", level=1))
    elements.append(make_para("Nghiên cứu đối sánh 4 nhóm công cụ đại diện thị trường với FocusFlow:"))
    bench_headers = ["Tiêu chí đối sánh", "Google Calendar", "Notion", "ChatGPT / Claude", "Reclaim / Motion", "FocusFlow (Đề xuất)"]
    bench_data = [
        ["Phân rã mục tiêu bằng AI", "Không hỗ trợ", "Không hỗ trợ", "Văn bản tự do, không cấu trúc", "Phân rã task việc, không theo học tập", "Phân rã 2 cấp (Milestones & Proposal)"],
        ["Cấu hình thời gian rảnh", "Tạo event rảnh", "Tự dựng DB", "Mù thời gian thực", "Tự đọc lịch trống", "Hybrid Mode A (quỹ giờ) / Mode B (khung giờ)"],
        ["Duyệt lịch Human-in-loop", "Không có", "Tự nhập", "Copy paste thủ công", "AI tự xếp xáo trộn", "Proposal -> Edit -> Validation Gate -> Apply"],
        ["Không gian học (Workspace)", "Không có", "Nhúng widget ngoài", "Không có", "Không có", "Tích hợp: Checklist + Pomodoro + Note"],
        ["Phát hiện quá hạn", "Không (sự kiện trôi)", "Viết Formula", "Không biết tiến độ", "Tự dời lịch", "Thuật toán tất định: date < TODAY"],
        ["Thích ứng khi có biến cố", "Kéo thả thủ công", "Sửa filter thủ công", "Gõ prompt lại từ đầu", "Hộp đen xáo trộn lịch", "Pause Roadmap & Domino Shift tất định"],
        ["Đồng bộ lịch ngoại vi", "Có sẵn", "Cần Zapier ngoài", "Không có", "OAuth 2 chiều", "1-Way WebCal Feed bảo mật token (.ics)"],
        ["Chi phí đối với sinh viên", "Miễn phí", "Free / $8+", "Free / $20", "Đắt ($10 - $34/tháng)", "Miễn phí Core MVP / Quota phân tầng"]
    ]
    elements.append(make_table([1800, 1500, 1500, 1500, 1500, 1560], bench_headers, bench_data))
    
    elements.append(make_heading("4.1. Ba Khoảng trống Chiến lược (The 3 Strategic Gaps)", level=2))
    elements.append(make_bullet("Thị trường chỉ có các công cụ giải quyết từng mẩu rời rạc (ChatGPT gợi ý ý tưởng, Calendar giữ giờ, Pomodoro canh giờ, Notion lưu trữ). Thiếu một nền tảng kết nối khép kín toàn bộ chu trình học tập.", bold_prefix="Khoảng trống 1 — Quy trình học tập khép kín (Workflow Gap): "))
    elements.append(make_bullet("Các ứng dụng hiện tại hoặc quá tĩnh (không tự dời lịch), hoặc quá phụ thuộc vào LLM hộp đen gây tốn kém và ảo giác. Cần cơ chế thích ứng lai: Dùng backend tất định để dời ngày (Domino Shift chính xác 100%), chỉ dùng AI cho gợi ý tri thức.", bold_prefix="Khoảng trống 2 — Thích ứng lai tất định (Deterministic Adaptation Gap): "))
    elements.append(make_bullet("Người học không tin tưởng hệ thống tự động ghi đè dữ liệu. Cần quy trình phê duyệt minh bạch: Đề xuất (Proposal) -> Xem xét/Sửa đổi -> Xác nhận (Apply) -> Lịch chính thức.", bold_prefix="Khoảng trống 3 — Kiểm duyệt con người (Human-in-the-Loop Approval Gap): "))
    
    # Section 5
    elements.append(make_heading("5. DANH MỤC TÀI LIỆU THAM KHẢO CHUẨN IEEE", level=1))
    elements.append(make_para("[1] B. J. Zimmerman, 'Becoming a self-regulated learner: An overview,' Theory Into Practice, vol. 41, no. 2, pp. 64–70, Spring 2002.\n[2] J. Sweller, 'Cognitive load during problem solving: Effects on learning,' Cognitive Science, vol. 12, no. 2, pp. 257–285, Apr. 1988.\n[3] R. F. Baumeister et al., 'Ego depletion: Is the active self a limited resource?,' J. Pers. Soc. Psychol., vol. 74, no. 5, pp. 1252–1265, May 1998.\n[4] J. Reich and J. A. Ruipérez-Valiente, 'The MOOC pivot,' Science, vol. 363, no. 6423, pp. 130–131, Jan. 2019.\n[5] G. Mark, V. M. Gonzalez, and J. Harris, 'No task left behind? Examining the nature of fragmented work,' in Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '05), 2005, pp. 321–330.\n[6] Stack Overflow, '2023 Developer Survey - Learning to code,' Stack Overflow Research, 2023.\n[7] A. Cooper, The Inmates Are Running the Asylum, Sams Publishing, 1999.\n[8] ISO/IEC/IEEE, 'ISO/IEC/IEEE 29148:2018 Systems and software engineering — Requirements engineering,' 2018.\n[9] J. Brooke, 'SUS: A quick and dirty usability scale,' in Usability Evaluation In Industry, Taylor & Francis, 1996.\n[10] B. Deshpande et al., 'Internet Calendaring and Scheduling Core Object Specification (iCalendar),' IETF RFC 5545, Sep. 2009."))
    
    save_docx(elements, "WBS 1.1 - Khảo sát nhu cầu tự học và nghiên cứu đối sánh giải pháp (Benchmarking).docx")

# ==============================================================================
# 2. WBS 1.2 BUILDER
# ==============================================================================
def build_wbs_1_2():
    elements = []
    elements.append(make_para("ĐẶC TẢ MỤC TIÊU NGHIỆP VỤ & 5 CHỈ SỐ KPI ĐỊNH LƯỢNG", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 1.2 — HỆ THỐNG CHỈ SỐ HIỆU SUẤT & GIAO THỨC NGHIỆM THU ĐỒ ÁN", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 1.2: Thiết lập Business Goals & 5 chỉ số KPI định lượng"),
        ("Sinh Viên Phụ Trách", "Vũ Toàn Thắng (Lead BA / System Analyst)"),
        ("Thời Gian Thực Hiện", "01/09/2026 – 05/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Căn Cứ Đánh Giá", "Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 Mức 5 & TC2.7 Mức 5"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Hoàn thành 100% (Deliverable Approved)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. NGUYÊN TẮC THIẾT LẬP MỤC TIÊU & PHƯƠNG PHÁP LUẬN ĐO LƯỜNG", level=1))
    elements.append(make_para("Theo chuẩn mực kỹ thuật phần mềm, mọi mục tiêu dự án phải được cụ thể hóa bằng các chỉ số định lượng đo lường được (SMART). Đề tài thiết lập sự phân định rạch ròi về mặt phương pháp luận:"))
    elements.append(make_bullet("Yêu cầu Phi Chức năng (NFR): Ràng buộc chất lượng nội tại mà phần mềm tự thân phải đáp ứng trong môi trường kiểm thử (ví dụ: API backend phản hồi <= 200ms, timeout AI 55s, Lighthouse Accessibility >= 90).", bold_prefix="NFR nội tại: "))
    elements.append(make_bullet("Chỉ số Hiệu suất Cốt lõi (KPI / Evaluation Metrics): Chỉ số đo lường kết quả tương tác thực tế giữa người dùng và phần mềm trong môi trường vận hành (ví dụ: Thời gian tạo lịch <= 5 phút, Tỷ lệ hoàn thành task >= 80%, Điểm SUS >= 80). Đây là căn cứ nghiệm thu đồ án trước Hội đồng.", bold_prefix="KPI nghiệp vụ & Đánh giá: "))
    
    elements.append(make_heading("2. HỆ THỐNG 5 MỤC TIÊU NGHIỆP VỤ CỐT LÕI (BUSINESS GOALS)", level=1))
    elements.append(make_bullet("Tự động hóa phân rã một mục tiêu lớn, trừu tượng thành các mốc kiến thức (Milestones) và đầu việc (Tasks) chi tiết bám sát thời gian rảnh thực tế.", bold_prefix="BG-01 (Tự động hóa phân rã lộ trình): "))
    elements.append(make_bullet("Tích hợp không gian học tập thống nhất (Study Workspace), triệt tiêu chi phí chuyển đổi ngữ cảnh giữa nhiều ứng dụng rời rạc.", bold_prefix="BG-02 (Tối ưu hóa phiên thực thi): "))
    elements.append(make_bullet("Bảo vệ tính liên tục của kế hoạch học tập trước các biến cố đời sống thông qua cơ chế thích ứng Domino Shift khi tạm dừng.", bold_prefix="BG-03 (Bảo vệ tính liên tục kế hoạch): "))
    elements.append(make_bullet("Đạt độ tin cậy trải nghiệm cao với giao diện responsive, chuẩn tiếp cận và quy trình kiểm duyệt con người minh bạch.", bold_prefix="BG-04 (Trải nghiệm tương tác chuẩn mực): "))
    elements.append(make_bullet("Quản trị chặt chẽ việc gọi API mô hình ngôn ngữ lớn qua middleware phân tầng Quota, bảo vệ ngân sách và an toàn dữ liệu.", bold_prefix="BG-05 (Kiểm soát chi phí & an toàn AI): "))
    
    elements.append(make_heading("3. ĐẶC TẢ CHI TIẾT 5 CHỈ SỐ KPI ĐỊNH LƯỢNG (RUBRIC TC1 MỨC 5)", level=1))
    kpi_headers = ["Mã KPI", "Tên chỉ số", "Mục tiêu Benchmark", "Công thức toán học giải tích", "Nguồn dữ liệu & Công cụ đo"]
    kpi_data = [
        ["KPI 1 (EVAL-01)", "Thời gian khởi tạo lộ trình (Plan Creation Time)", "<= 5 phút (300 giây)", "T_plan = t_apply_success - t_goal_submit", "Audit Log / Telemetry (GOAL_SUBMITTED -> OFFICIAL_SCHEDULE_CREATED)"],
        ["KPI 2 (EVAL-02)", "Hiệu quả thực thi buổi học (Session Task Completion)", ">= 80% hoàn thành", "CR = (Tasks_Completed / Tasks_Scheduled) * 100%", "Bảng study_sessions & session_tasks"],
        ["KPI 3 (EVAL-03)", "Tỷ lệ duy trì lộ trình (Plan Adherence Rate)", ">= 70% buổi học", "AR = [Days_Attended / (Days_Scheduled - Days_Paused)] * 100%", "Bảng official_schedules & pause_records (loại trừ ngày PAUSED)"],
        ["KPI 4 (EVAL-04)", "Tỷ lệ hoàn thành tác vụ (Task Success Rate)", ">= 90% thành công", "TSR = [Sum(Success) / (Users * Tasks)] * 100%", "Biên bản kiểm thử UAT 4 kịch bản trên >= 10 người dùng thật"],
        ["KPI 5 (EVAL-05)", "Độ hài lòng trải nghiệm (SUS Usability Score)", ">= 80/100 (Grade A)", "SUS = Sum[Item_scores] * 2.5 theo chuẩn Brooke (1996)", "Phiếu khảo sát chuẩn quốc tế 10 câu hỏi Likert"]
    ]
    elements.append(make_table([1300, 2000, 1600, 2460, 2000], kpi_headers, kpi_data))
    
    elements.append(make_heading("4. GIAO THỨC THỰC NGHIỆM NGHIỆM THU NGƯỜI DÙNG THẬT (UAT PROTOCOL)", level=1))
    elements.append(make_para("Thực hiện nghiêm túc trên người dùng thật nhằm đáp ứng tiêu chuẩn TC2.7 Mức 5:"))
    elements.append(make_bullet("Cỡ mẫu U = 10 – 15 người dùng thật, gồm >= 60% sinh viên CNTT, >= 25% người chuyển ngành và >= 15% người ôn chứng chỉ. Thời gian theo dõi thực tế: 7 đến 14 ngày liên tục.", bold_prefix="Quy mô & Tiêu chuẩn chọn mẫu: "))
    elements.append(make_bullet("Task 1: Tạo lộ trình AI và bấm Apply (<= 5 phút); Task 2: Thực thi phiên học Pomodoro, tick task và lưu Takeaway; Task 3: Tạm dừng lộ trình 2 ngày và kiểm tra Domino Shift; Task 4: Đồng bộ WebCal Feed lên điện thoại và xem báo cáo tuần.", bold_prefix="4 Kịch bản tác vụ đo lường TSR: "))
    elements.append(make_bullet("Dữ liệu KPI 1, 2, 3 được ghi nhận bằng Backend Audit Logger tự động; KPI 4 ghi nhận qua biên bản UAT; KPI 5 tính điểm tự động qua Google Form SUS Validator.", bold_prefix="Công cụ đo lường khách quan: "))
    
    elements.append(make_heading("5. MA TRẬN RỦI RO MỤC TIÊU & BIỆN PHÁP KIỂM SOÁT KỸ THUẬT", level=1))
    risk_headers = ["Chỉ số", "Nguy cơ tiềm ẩn", "Nguyên nhân kỹ thuật", "Biện pháp kiểm soát của FocusFlow"]
    risk_data = [
        ["KPI 1", "T_plan > 5 phút", "LLM API phản hồi chậm, timeout mạng", "Hard Timeout 55s, auto-retry, hỗ trợ Fallback tạo thủ công ngay"],
        ["KPI 2", "CR < 80%", "AI xếp khối lượng task quá nặng", "Backend Hard Ceiling Gate chặn Apply nếu vượt quỹ giờ khả dụng"],
        ["KPI 3", "AR < 70%", "Người dùng quên học, nản khi trễ hạn", "Đồng bộ WebCal Feed 1 chiều; Nút Pause kích hoạt Domino Shift"],
        ["KPI 4", "TSR < 90%", "Giao diện gây hiểu lầm hoặc nghẽn luồng", "Tuân thủ Lighthouse Accessibility >= 90; Thiết kế Wizard từng bước"],
        ["KPI 5", "SUS < 80", "Ứng dụng giật lag, phản hồi chậm", "Tối ưu API <= 200ms; Optimistic UI cập nhật tức thì trên client"]
    ]
    elements.append(make_table([1300, 2000, 2600, 3460], risk_headers, risk_data))
    
    save_docx(elements, "WBS 1.2 - Thiết lập Business Goals & 5 chỉ số KPI định lượng.docx")

# ==============================================================================
# 3. WBS 1.3 BUILDER
# ==============================================================================
def build_wbs_1_3():
    elements = []
    elements.append(make_para("ĐẶC TẢ TÁC NHÂN HỆ THỐNG & PHÂN TÍCH CHÂN DUNG NGƯỜI DÙNG (PERSONAS)", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 1.3 — MÔ HÌNH HÓA ĐỐI TƯỢNG TƯƠNG TÁC & THIẾT KẾ HƯỚNG NGƯỜI DÙNG (UCD)", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 1.3: Xác định tác nhân hệ thống & Phân tích chân dung người dùng (Personas)"),
        ("Sinh Viên Phụ Trách", "Phan Đình Duẩn (Senior BA / Requirements Engineer)"),
        ("Thời Gian Thực Hiện", "04/09/2026 – 08/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Căn Cứ Đánh Giá", "Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 & TC2.1"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Hoàn thành 100% (Deliverable Approved)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. PHÂN BIỆT LÝ THUYẾT GIỮA TÁC NHÂN HỆ THỐNG & CHÂN DUNG NGƯỜI DÙNG", level=1))
    elements.append(make_para("Trong công nghệ phần mềm chuyên nghiệp, cần phân định rõ ràng:"))
    elements.append(make_bullet("System Actor là vai trò logic trừu tượng tương tác qua ranh giới hệ thống (System Boundary) phục vụ thiết kế API, phân quyền bảo mật và vẽ biểu đồ Use Case.", bold_prefix="Tác nhân Hệ thống (System Actor): "))
    elements.append(make_bullet("User Persona là hình mẫu hợp thành mang tính thực chứng (Composite User Archetype theo Alan Cooper, 1999) đại diện cho một nhóm người dùng có cùng mô thức hành vi, mục tiêu và rào cản nhận thức phục vụ thiết kế công thái học.", bold_prefix="Chân dung Người dùng (User Persona): "))
    
    elements.append(make_heading("2. ĐẶC TẢ CHI TIẾT 4 TÁC NHÂN HỆ THỐNG (SYSTEM ACTORS)", level=1))
    elements.append(make_bullet("Tác nhân người dùng chính tương tác qua Web App; đăng ký, cấu hình thời gian rảnh, phê duyệt Proposal thành Official Schedule, vận hành phiên học trong Study Workspace và quản lý WebCal token.", bold_prefix="1. Learner (Người học): "))
    elements.append(make_bullet("Vai trò dịch vụ nền tảng (Service Role); quản trị hạn ngạch gọi AI (Tokens / Requests quota) tại middleware và giám sát hệ thống; không xây dựng Web Admin Portal riêng để tối ưu phạm vi đồ án.", bold_prefix="2. Administrator (Quản trị viên hệ thống): "))
    elements.append(make_bullet("Hệ thống trí tuệ nhân tạo bên ngoài (Gemini/OpenAI); tiếp nhận prompt đã làm sạch, phản hồi cấu trúc JSON Schema trong thời gian <= 55s; bị kiểm soát bởi Schema Validation Gate.", bold_prefix="3. External LLM Provider: "))
    elements.append(make_bullet("Ứng dụng lịch tiêu chuẩn của người dùng (Google/Apple Calendar); kéo dữ liệu 1 chiều qua URL WebCal token bảo mật định dạng iCalendar RFC 5545 (.ics).", bold_prefix="4. External Calendar Application: "))
    
    elements.append(make_heading("3. PHÂN TÍCH 3 HÌNH MẪU NGƯỜI DÙNG (USER ARCHETYPES THEO ALAN COOPER)", level=1))
    elements.append(make_para("Xây dựng dựa trên dữ liệu báo cáo ngành công nghệ (Stack Overflow 2023, Tạp chí Science) kết hợp thực nghiệm công thái học:"))
    
    elements.append(make_heading("3.1. Archetype 1: IT Student Archetype (Minh họa: Sinh viên An, 21 tuổi - ~60%)", level=2))
    elements.append(make_para("• Tuổi: 21 | Trường: ĐH Sư phạm Kỹ thuật TP.HCM | Trình độ: Khá-Giỏi | Thiết bị: MacBook, Ubuntu, Android."))
    elements.append(make_para("• Mục tiêu: Tự học Golang, Docker & K8s trong 2 tháng để làm đồ án tốt nghiệp và phỏng vấn Backend."))
    elements.append(make_para("• Nỗi đau: Bế tắc khi chia nhỏ kiến thức; lộ trình ChatGPT nằm chết trong chatbox; hay bị dồn việc thi cử làm sập lịch."))
    elements.append(make_bullet("Says: 'Lộ trình trên mạng nhiều quá, em không biết bắt đầu từ đâu và phân bổ thời gian thế nào cho vừa sức.'", bold_prefix="Empathy Map: "))
    elements.append(make_bullet("Thinks: 'Sắp ra trường rồi, nếu không có kế hoạch rõ ràng thì lại lướt web hết buổi tối.'", level=1))
    elements.append(make_bullet("Does: Xin prompt ChatGPT -> copy vào bookmark -> loay hoay chuẩn bị mất 30 phút -> mệt mỏi đi ngủ.", level=1))
    elements.append(make_bullet("Feels: Lo âu, bất lực khi nhìn kế hoạch vỡ nợ, nản lòng trước công cụ phức tạp.", level=1))
    elements.append(make_para("• Giải pháp tương ứng: Chế độ Mode B (khung giờ cố định 20:00 - 22:30) + Study Workspace Pomodoro + Scratchpad."))
    
    elements.append(make_heading("3.2. Archetype 2: Career Switcher Archetype (Minh họa: Kỹ sư Hùng, 26 tuổi - ~25%)", level=2))
    elements.append(make_para("• Tuổi: 26 | Nghề nghiệp: Kỹ sư thiết kế cơ khí | Quỹ thời gian: 1.5h/tối | Thiết bị: Laptop Windows cũ, iPhone."))
    elements.append(make_para("• Mục tiêu: Tự học Web Frontend (React) trong 6 tháng để chuyển ngành lập trình."))
    elements.append(make_para("• Nỗi đau: Suy hao ý chí sau ngày làm việc; thường xuyên tăng ca đột xuất (OT) khiến kế hoạch bị vỡ nợ."))
    elements.append(make_bullet("Says: 'Tôi chỉ có 1.5 tiếng mỗi tối, tôi không muốn làm thư ký kéo thả lịch, tôi muốn vào là học ngay.'", bold_prefix="Empathy Map: "))
    elements.append(make_bullet("Thinks: 'Học lập trình ở tuổi 26 khá muộn, nếu không kiên trì thì mãi giậm chân tại chỗ.'", level=1))
    elements.append(make_bullet("Does: Đi làm về mệt -> không biết học gì tiếp -> xem video giải trí rồi ngủ trong cảm giác tội lỗi.", level=1))
    elements.append(make_bullet("Feels: Mệt mỏi thể xác, áp lực tuổi tác, sợ bị bỏ lại phía sau.", level=1))
    elements.append(make_para("• Giải pháp tương ứng: Chế độ Mode A (quỹ giờ 1.5h/ngày) + Nút Pause Roadmap kích hoạt Domino Shift dời lịch khi tăng ca."))
    
    elements.append(make_heading("3.3. Archetype 3: Certification Seeker Archetype (Minh họa: Chuyên viên Mai, 24 tuổi - ~15%)", level=2))
    elements.append(make_para("• Tuổi: 24 | Nghề nghiệp: Data Analyst | Lịch trình: Thường xuyên công tác | Thiết bị: MacBook Pro, iPhone, iPad."))
    elements.append(make_para("• Mục tiêu: Ôn thi đỗ chứng chỉ AWS Solutions Architect Associate (SAA) trong 8 tuần."))
    elements.append(make_para("• Nỗi đau: Lịch công tác xáo trộn; chỉ xem lịch trên Google Calendar điện thoại; học lab dài không đúc kết được."))
    elements.append(make_bullet("Says: 'Nếu lịch học không nằm trên Google Calendar của tôi, nó coi như không tồn tại.'", bold_prefix="Empathy Map: "))
    elements.append(make_para("• Giải pháp tương ứng: Luồng WebCal Feed 1 chiều bảo mật token + Bắt buộc đúc kết Key Takeaways & AI Review."))
    
    elements.append(make_heading("4. MA TRẬN ÁNH XẠ PERSONA SANG TÍNH NĂNG FOCUSFLOW", level=1))
    p_headers = ["Persona", "Nỗi đau cốt tử", "Giải pháp FocusFlow", "Mã yêu cầu SRS v1.0"]
    p_data = [
        ["An (Sinh viên CNTT)", "Khó chia nhỏ mục tiêu, lười dựng template", "AI phân rã 2 cấp (Milestones & Proposal) + Nút Apply", "FR-PLAN-001..003, BUSR-02"],
        ["An (Sinh viên CNTT)", "Mất tập trung vì mở nhiều tab công cụ", "Study Workspace: Checklist + Pomodoro + Scratchpad", "FR-SESSION-001..002"],
        ["Hùng (Chuyển ngành)", "Quỹ giờ phân tán không cố định khung giờ", "Cấu hình thời gian rảnh Mode A: Daily Hours Quota", "FR-AVAIL-001, BUSR-03"],
        ["Hùng (Chuyển ngành)", "Tăng ca đột xuất, áp lực nợ task quá hạn", "Pause Roadmap & Tịnh tiến dây chuyền Domino Shift", "FR-PAUSE-001..002, BUSR-07"],
        ["Mai (Ôn chứng chỉ)", "Chỉ dùng Google Calendar điện thoại", "Đăng ký theo dõi WebCal 1 chiều bảo mật token (.ics)", "FR-CALENDAR-002..003, BUSR-08"],
        ["Mai (Ôn chứng chỉ)", "Học xong hay quên, thiếu đúc kết thi cử", "Trường bắt buộc Key Takeaways & Trợ lý AI Review tuần", "FR-SESSION-002, FR-REPORT-002"]
    ]
    elements.append(make_table([2000, 2600, 2760, 2000], p_headers, p_data))
    
    save_docx(elements, "WBS 1.3 - Xác định tác nhân hệ thống & Phân tích chân dung người dùng (Personas).docx")

# ==============================================================================
# 4. WBS 2.1 BUILDER
# ==============================================================================
def build_wbs_2_1():
    elements = []
    elements.append(make_para("HỒ SƠ ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS v1.0)", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 2.1 — SOFTWARE REQUIREMENTS SPECIFICATION THEO CHUẨN ISO/IEC/IEEE 29148:2018", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 2.1: Soạn thảo hồ sơ SRS v1.0 theo chuẩn ISO/IEC/IEEE 29148:2018"),
        ("Sinh Viên Phụ Trách", "Vũ Toàn Thắng (Lead BA / System Analyst)"),
        ("Thời Gian Thực Hiện", "06/09/2026 – 12/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Chuẩn Mực Kỹ Thuật", "ISO/IEC/IEEE 29148:2018 (Systems and software engineering — Requirements engineering)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Chuẩn Cơ sở Đã Đóng Băng (Baseline Frozen)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. GIỚI THIỆU TỔNG QUAN & PHẠM VI SẢN PHẨM", level=1))
    elements.append(make_para("Hồ sơ SRS v1.0 đặc tả đầy đủ các yêu cầu cho nền tảng FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI, giải quyết triệt để 3 nút thắt của người tự học (Rào cản phân rã, Phân mảnh công cụ, Đứt gãy kỷ luật khi có biến cố)."))
    elements.append(make_para("Hệ thống quản lý vòng đời học tập qua 4 giai đoạn logic khép kín: (1) Khởi tạo lộ trình & Duyệt lịch 2 cấp; (2) Không gian thực thi phiên học tập trung; (3) Thích ứng & Quản trị lịch; (4) Tổng kết & Cải tiến chu kỳ."))
    
    elements.append(make_heading("2. DANH MỤC CA SỬ DỤNG CẤP YÊU CẦU (USE CASE INVENTORY)", level=1))
    uc_headers = ["Mã UC", "Tên Use Case", "Tác nhân chính", "Tác nhân hỗ trợ", "Mô tả tóm tắt"]
    uc_data = [
        ["UC-AUTH-01", "Đăng ký tài khoản", "Learner", "Hệ thống", "Đăng ký email/mật khẩu, băm bảo mật Argon2id/bcrypt"],
        ["UC-AUTH-02", "Đăng nhập hệ thống", "Learner", "Hệ thống", "Xác thực phiên, cấp JWT/Session HttpOnly"],
        ["UC-AVAIL-01", "Cấu hình thời gian rảnh", "Learner", "Hệ thống", "Cấu hình Mode A (quỹ giờ) hoặc Mode B (khung giờ)"],
        ["UC-PLAN-01", "Khởi tạo mục tiêu", "Learner", "External LLM", "Thu thập mục tiêu, AI đối thoại làm rõ ngữ cảnh"],
        ["UC-PLAN-02", "Duyệt Milestones", "Learner", "Hệ thống", "Xem xét và phê duyệt các mốc kiến thức Cấp 1"],
        ["UC-PLAN-03", "Tạo Proposal & Apply", "Learner", "External LLM", "AI sinh task chi tiết Cấp 2, User chỉnh sửa và bấm Apply"],
        ["UC-PLAN-04", "Lập kế hoạch thủ công", "Learner", "Hệ thống", "Fallback dự phòng khi AI quá tải hoặc lỗi timeout"],
        ["UC-SESS-01", "Thực hiện phiên học", "Learner", "Hệ thống", "Study Workspace: Checklist + Pomodoro + Scratchpad + Takeaway"],
        ["UC-SESS-02", "Xử lý gián đoạn", "Learner", "Hệ thống", "Dừng sớm/rớt mạng: lưu phút thực học, task dở dang về Backlog"],
        ["UC-TASK-01", "Cập nhật trạng thái Task", "Learner", "Hệ thống", "Tick COMPLETED task, cập nhật tiến độ"],
        ["UC-ADAPT-01", "Quét quá hạn tất định", "Hệ thống", "Backend Logic", "Tự động phát hiện task trễ hạn: date < TODAY"],
        ["UC-ADAPT-02", "AI sắp xếp lại tồn đọng", "Learner", "External LLM", "Tùy chọn kích hoạt nhờ AI gợi ý lại thứ tự ưu tiên task tồn"],
        ["UC-PAUSE-01", "Tạm dừng & Domino Shift", "Learner", "Hệ thống", "Pause Roadmap, tự động dời tịnh tiến lịch về sau"],
        ["UC-CAL-01", "Xuất tệp lịch .ics", "Learner", "Hệ thống", "Kết xuất tệp iCalendar tĩnh tải về máy"],
        ["UC-CAL-02", "Đăng ký luồng WebCal", "Learner", "External Cal", "Lấy URL Secure Token dán vào Google/Apple Calendar"],
        ["UC-REP-01", "Xem thống kê định lượng", "Learner", "Hệ thống", "Biểu đồ toán học tổng thời gian học, tỷ lệ hoàn thành"],
        ["UC-REP-02", "Yêu cầu AI Review", "Learner", "External LLM", "AI đọc thống kê và Takeaways để nhận xét chu kỳ"],
        ["UC-QUOTA-01", "Mock Upgrade Sandbox", "Learner", "Hệ thống", "Mô phỏng nâng cấp tài khoản, mở rộng quota gọi AI"]
    ]
    elements.append(make_table([1400, 2200, 1400, 1600, 2760], uc_headers, uc_data))
    
    elements.append(make_heading("3. ĐẶC TẢ YÊU CẦU CHỨC NĂNG CỐT LÕI (FUNCTIONAL REQUIREMENTS)", level=1))
    elements.append(make_para("SRS v1.0 định nghĩa 13 phân hệ chức năng chi tiết với cấu trúc tiền điều kiện, luồng chính, luồng ngoại lệ và tiêu chí chấp nhận:"))
    elements.append(make_bullet("FR-AUTH-001 & 002: Bắt buộc Onboarding định danh trước khi dùng AI; 100% mật khẩu được băm mã hóa.", bold_prefix="Phân hệ Xác thực: "))
    elements.append(make_bullet("FR-PLAN-001 đến 003: Phân rã 2 cấp (Milestones & Proposal); Cổng kiểm duyệt Backend Validation Gate ngăn chặn xếp lịch quá tải trước khi lưu Official Schedule.", bold_prefix="Phân hệ Lập kế hoạch AI: "))
    elements.append(make_bullet("FR-AVAIL-001 đến 003: Hỗ trợ Mode A (0.5h - 14h/ngày), Mode B (tràn giờ mềm tối đa 30 phút có cảnh báo), và kiểm tra dung lượng khi học đa lộ trình.", bold_prefix="Phân hệ Thời gian rảnh: "))
    elements.append(make_bullet("FR-SESSION-001 đến 003: Study Workspace tích hợp Pomodoro/Stopwatch, Scratchpad và Key Takeaways; bảo toàn số phút thực học khi bị dừng sớm.", bold_prefix="Phân hệ Phiên học: "))
    elements.append(make_bullet("FR-ADAPT-001 & FR-PAUSE-001..002: Phát hiện quá hạn tất định thuần túy backend; Tạm dừng lộ trình kích hoạt Domino Shift dời lùi đúng số ngày tương ứng, vô hiệu hóa cảnh báo quá hạn khi Pause.", bold_prefix="Phân hệ Thích ứng & Lịch trình: "))
    elements.append(make_bullet("FR-AI-001..002 & FR-QUOTA-001..002: Hard Timeout 55s, auto-retry schema tối đa 2 lần không tính quota, kiểm tra quota nguyên tử tại middleware, Mock Upgrade Sandbox.", bold_prefix="Phân hệ An toàn AI & Quota: "))
    
    elements.append(make_heading("4. ĐẶC TẢ YÊU CẦU PHI CHỨC NĂNG ĐỊNH LƯỢNG (NFRs)", level=1))
    elements.append(make_bullet("NFR-PERF-001: Timeout AI 55s, trần hiển thị 60s. NFR-PERF-002: Thao tác UI <= 500ms, API backend <= 200ms ở mức tải 20 concurrent users.", bold_prefix="Hiệu năng (NFR-PERF): "))
    elements.append(make_bullet("NFR-SEC-001: 0 secret rò rỉ trong git/client. NFR-SEC-002: Băm Argon2id/bcrypt. NFR-SEC-003: Làm sạch prompt không gửi dữ liệu nhạy cảm ra LLM. NFR-SEC-004: Che giấu token WebCal khỏi access log.", bold_prefix="Bảo mật (NFR-SEC): "))
    elements.append(make_bullet("NFR-AVAIL-001: Đạt độ sẵn sàng Uptime >= 95% trong suốt đợt thử nghiệm.", bold_prefix="Độ sẵn sàng (NFR-AVAIL): "))
    elements.append(make_bullet("NFR-UX-001: Responsive Desktop (>= 1024px) và Mobile (375px - 768px). NFR-UX-002: Google Lighthouse Accessibility >= 90 điểm.", bold_prefix="Trải nghiệm (NFR-UX): "))
    elements.append(make_bullet("NFR-AI-001: 100% output AI tuân thủ nghiêm ngặt định dạng JSON Schema.", bold_prefix="An toàn AI (NFR-AI): "))
    
    save_docx(elements, "WBS 2.1 - Soạn thảo hồ sơ SRS v1.0 theo chuẩn ISO-IEC-IEEE 29148.docx")

# ==============================================================================
# 5. WBS 2.2 BUILDER
# ==============================================================================
def build_wbs_2_2():
    elements = []
    elements.append(make_para("TẬP ĐẶC TẢ QUY TẮC NGHIỆP VỤ & MÁY TRẠNG THÁI HỆ THỐNG", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 2.2 — BUSINESS RULES & STATE MACHINE SPECIFICATIONS (STRICT APPLY, AVAILABILITY, QUOTA)", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 2.2: Xây dựng quy tắc nghiệp vụ (Business Rules: Strict Apply, Availability, Quota)"),
        ("Sinh Viên Phụ Trách", "Vũ Toàn Thắng (Lead BA / System Analyst)"),
        ("Thời Gian Thực Hiện", "09/09/2026 – 14/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Căn Cứ Đánh Giá", "Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Hoàn thành 100% (Deliverable Approved)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. NGUYÊN TẮC QUẢN TRỊ QUY TẮC NGHIỆP VỤ", level=1))
    elements.append(make_para("Quy tắc nghiệp vụ (Business Rules - BUSR) là các ràng buộc hoặc công thức tính toán mang tính bắt buộc, định hình hành vi hệ thống và bảo vệ tính toàn vẹn dữ liệu. Toàn bộ quy tắc trong FocusFlow được thiết kế độc lập với giải pháp hiện thực (công nghệ cơ sở dữ liệu hay ngôn ngữ lập trình cụ thể)."))
    
    elements.append(make_heading("2. CHI TIẾT 10 QUY TẮC NGHIỆP VỤ CỐT LÕI (BUSR-01 ĐẾN BUSR-10)", level=1))
    busr_headers = ["Mã BUSR", "Tên Quy tắc Nghiệp vụ", "Mô tả Logic & Ràng buộc Kỹ thuật", "Mã FR chi phối"]
    busr_data = [
        ["BUSR-01", "Định danh bắt buộc (Onboarding First)", "Bắt buộc Đăng ký/Đăng nhập trước khi tạo kế hoạch; Roadmap, Session, Quota gắn chặt với User ID.", "FR-AUTH-001, FR-GOAL-001"],
        ["BUSR-02", "Phân tách Proposal & Official (Strict Apply)", "AI chỉ sinh Proposal tạm thời. Tuyệt đối không tự lưu. Bắt buộc User bấm Apply và vượt qua Validation Gate.", "FR-PLAN-002, FR-PLAN-003"],
        ["BUSR-03", "Backend Hard Ceiling (Chặn vượt giờ rảnh)", "Backend kiểm tra tổng thời lượng task trong ngày không được vượt quá thời gian rảnh. Cận Mode A: 0.5h – 14h.", "FR-AVAIL-001, FR-PLAN-003"],
        ["BUSR-04", "Tràn giờ mềm có kiểm soát (Soft Overflow)", "Chỉ áp dụng task cuối cùng trong ngày của Mode B: Được vượt tối đa 30 phút kèm cảnh báo và xác nhận.", "FR-AVAIL-002"],
        ["BUSR-05", "Dung lượng đa lộ trình (Multi-Roadmap)", "Xếp lịch mới phải trừ đi thời gian đã cam kết cho Official Schedule hiện có; ưu tiên Earliest Deadline First.", "FR-AVAIL-003"],
        ["BUSR-06", "Phát hiện quá hạn tất định (Deterministic)", "Điều kiện suy diễn: task.status != COMPLETED AND task.scheduled_date < TODAY. Không phụ thuộc LLM.", "FR-ADAPT-001"],
        ["BUSR-07", "Tịnh tiến dây chuyền khi tạm dừng (Domino Shift)", "Pause từ ngày A đến B: Tự động dời toàn bộ lịch từ A lùi về sau đúng số ngày khả dụng, giữ nguyên thứ tự task.", "FR-PAUSE-001, FR-PAUSE-002"],
        ["BUSR-08", "Bảo mật lịch ngoại vi (1-Way WebCal)", "WebCal chỉ đọc 1 chiều; chỉ xuất Official Schedule; Reset Token hủy ngay token cũ; che giấu URL khỏi server log.", "FR-CALENDAR-002, 003"],
        ["BUSR-09", "Bảo toàn dữ liệu khi gián đoạn phiên học", "Dừng sớm: Lưu phút thực học; task xong giữ nguyên COMPLETED; task dở dang về Backlog; phân định PARTIAL vs CANCELLED.", "FR-SESSION-003"],
        ["BUSR-10", "Kiểm soát hạn ngạch & An toàn AI", "Middleware giữ chỗ Quota nguyên tử; không trừ quota khi retry lỗi schema/timeout; sanitization prompt.", "FR-QUOTA-001, FR-AI-001"]
    ]
    elements.append(make_table([1200, 2200, 4460, 1500], busr_headers, busr_data))
    
    elements.append(make_heading("3. ĐẶC TẢ 4 MÁY TRẠNG THÁI VÒNG ĐỜI (STATE TRANSITION MACHINES)", level=1))
    elements.append(make_bullet("INITIALIZED (nhập mục tiêu/sinh milestone) -> ACTIVE (bấm Apply Official Schedule thành công) <-> PAUSED (bấm Pause, kích hoạt Domino Shift) -> COMPLETED (100% task hoàn thành, chuyển thành bất biến).", bold_prefix="1. Vòng đời Lộ trình (Roadmap Lifecycle): "))
    elements.append(make_bullet("PENDING (vòng đời bền vững) -> tick hoàn thành chuyển COMPLETED. OVERDUE không phải trạng thái bền vững mà là điều kiện tính toán suy diễn (Derived Condition) khi date < TODAY.", bold_prefix="2. Vòng đời Task & Điều kiện Quá hạn: "))
    elements.append(make_bullet("IN_PROGRESS -> kết thúc bình thường chuyển COMPLETED. Khi dừng sớm/mất mạng: Nếu có >= 1 task COMPLETED hoặc đạt >= 50% thời gian dự kiến -> PARTIAL_COMPLETED; ngược lại -> CANCELLED.", bold_prefix="3. Vòng đời Phiên học (Session Lifecycle - OS-01): "))
    elements.append(make_bullet("DRAFT (AI sinh proposal xem trước) -> DISCARDED (User hủy) hoặc APPLIED (User bấm Apply). Chính sách khi có lịch cũ: Merge / Future Shift (giữ nguyên task quá khứ, chỉ ghép task mới vào tương lai).", bold_prefix="4. Vòng đời Đề xuất Lịch (Proposal Lifecycle - OS-03): "))
    
    save_docx(elements, "WBS 2.2 - Xây dựng quy tắc nghiệp vụ (Business Rules).docx")

# ==============================================================================
# 6. WBS 2.3 BUILDER
# ==============================================================================
def build_wbs_2_3():
    elements = []
    elements.append(make_para("MA TRẬN TRUY VẾT YÊU CẦU PHẦN MỀM (RTM)", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 2.3 — REQUIREMENT TRACEABILITY MATRIX THEO CHUẨN ISO/IEC/IEEE 29148:2018", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 2.3: Thiết lập ma trận truy vết yêu cầu (Requirement Traceability Matrix - RTM)"),
        ("Sinh Viên Phụ Trách", "Phan Đình Duẩn (Senior BA / Quality Lead)"),
        ("Thời Gian Thực Hiện", "12/09/2026 – 16/09/2026 (Theo kế hoạch WBS Gantt Chart)"),
        ("Tiêu Chuẩn Áp Dụng", "ISO/IEC/IEEE 29148:2018 (Requirements Traceability & Verification)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Phiên Bản & Trạng Thái", "Phiên bản 1.0 — Hoàn thành 100% (Deliverable Approved)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. NGUYÊN LÝ TRUY VẾT YÊU CẦU ĐA TẦNG (TRACEABILITY ARCHITECTURE)", level=1))
    elements.append(make_para("Ma trận RTM thiết lập mối liên kết hai chiều (Bidirectional Traceability) khép kín qua 6 tầng giá trị: Nguồn gốc bài toán / Khảo sát thực tế -> Yêu cầu Nghiệp vụ (BR) -> Quy tắc Nghiệp vụ (BUSR) -> Yêu cầu Chức năng (FR) -> Yêu cầu Phi chức năng (NFR) -> Tiêu chí Đánh giá & Nghiệm thu (EVAL / AC)."))
    
    elements.append(make_heading("2. BẢNG MA TRẬN TRUY VẾT RTM TOÀN DIỆN (COMPREHENSIVE RTM TABLE)", level=1))
    rtm_headers = ["Nguồn gốc Bài toán", "Mã BR", "Mã BUSR", "Mã Yêu cầu Chức năng (FR)", "Mã NFR chi phối", "Tiêu chí Nghiệm thu (EVAL/AC)"]
    rtm_data = [
        ["Nỗi đau 1: Rào cản phân rã (WBS 1.1)", "BR-001", "BUSR-01, 02", "FR-AUTH-001..002, FR-GOAL-001..002, FR-PLAN-001..003", "NFR-PERF-001, NFR-AI-001, NFR-SEC-001", "EVAL-01: Tạo lịch <= 5m. AC: Proposal không tự lưu, Apply qua Gate."],
        ["Mô hình giờ rảnh lai (WBS 1.1, 1.3)", "BR-001, 003", "BUSR-03, 04, 05", "FR-AVAIL-001 (Mode A), FR-AVAIL-002 (Mode B), FR-AVAIL-003", "NFR-PERF-002 (UI <= 500ms, API <= 200ms)", "AC: Chặn vượt quỹ giờ Mode A (0.5h-14h); Soft Overflow tối đa 30p."],
        ["Nỗi đau 2: Phân mảnh công cụ (WBS 1.1)", "BR-002", "BUSR-09", "FR-SESSION-001..003, FR-TASK-001..002", "NFR-PERF-002, NFR-UX-001..002 (Lighthouse >= 90)", "EVAL-02: Hiệu quả >= 80%. EVAL-04: TSR >= 90%. EVAL-05: SUS >= 80."],
        ["Nỗi đau 3: Đứt gãy kế hoạch (WBS 1.1)", "BR-003", "BUSR-06, 07", "FR-ADAPT-001, FR-ADAPT-002, FR-PAUSE-001..002", "NFR-PERF-002, NFR-AVAIL-001 (>= 95%)", "EVAL-03: Duy trì >= 70%. AC: Quét date < TODAY; Domino Shift dời lùi."],
        ["Tích hợp Lịch ngoại vi (WBS 1.3)", "BR-004", "BUSR-08", "FR-CALENDAR-001 (.ics), FR-CALENDAR-002..003 (WebCal)", "NFR-SEC-004 (Secure Token & Log Hygiene)", "AC: Chỉ xuất Official Schedule; WebCal 1 chiều; Reset hủy token cũ."],
        ["Báo cáo & AI Review (WBS 1.1)", "BR-002, 003", "BUSR-10", "FR-REPORT-001 (Toán học), FR-REPORT-002 (AI Review)", "NFR-PERF-002, NFR-SEC-003 (Sanitization)", "AC: Thống kê toán học chính xác 100%; AI Review đọc đúng Takeaways."],
        ["Quản trị Chi phí & AI (WBS 1.2)", "BR-005", "BUSR-10", "FR-QUOTA-001..002 (Mock Sandbox), FR-AI-001..002", "NFR-PERF-001 (Timeout 55s), NFR-SEC-001, NFR-AI-001", "AC: Kiểm tra Quota nguyên tử; Retry <= 2 lần không tính quota; Sandbox."]
    ]
    elements.append(make_table([1400, 800, 1100, 2460, 1600, 2000], rtm_headers, rtm_data))
    
    elements.append(make_heading("3. BÁO CÁO PHÂN TÍCH ĐỘ PHỦ YÊU CẦU (COVERAGE & ORPHAN AUDIT)", level=1))
    elements.append(make_bullet("100% (Tất cả 13 nhóm FR và 5 nhóm NFR đều bắt nguồn từ bài toán thực tế và nghiên cứu đối sánh tại Báo cáo WBS 1.1).", bold_prefix="Độ phủ nguồn gốc (Origin Traceability): "))
    elements.append(make_bullet("100% (Tất cả yêu cầu đều có tiêu chí chấp nhận cụ thể hoặc chỉ số định lượng EVAL kiểm chứng được).", bold_prefix="Độ phủ kiểm chứng (Verification Coverage): "))
    elements.append(make_bullet("0 Orphan Requirements (Không có tính năng thừa thãi nằm ngoài phạm vi); 0 Orphan Rules (Mọi quy tắc nghiệp vụ đều có ca sử dụng và luồng mã nguồn bảo vệ).", bold_prefix="Kiểm toán phần tử mồ côi: "))
    
    save_docx(elements, "WBS 2.3 - Thiết lập ma trận truy vết yêu cầu (RTM).docx")

# ==============================================================================
# 7. WBS 2.4 BUILDER
# ==============================================================================
def build_wbs_2_4():
    elements = []
    elements.append(make_para("BIÊN BẢN THẨM ĐỊNH & ĐÓNG BĂNG CƠ SỞ YÊU CẦU", style="Title", bold=True, align="center", size=32, space_before=120, space_after=60))
    elements.append(make_para("WBS 2.4 — REQUIREMENTS VALIDATION, VERIFICATION & BASELINE FREEZE SIGN-OFF (MILESTONE M2)", style="Subtitle", italic=True, align="center", size=22, space_after=180))
    
    meta = [
        ("Tên Dự Án", "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI"),
        ("Hạng Mục WBS", "WBS 2.4: Thẩm định & Đóng băng cơ sở yêu cầu (Requirements Baseline Freeze)"),
        ("Sinh Viên Phụ Trách", "Vũ Toàn Thắng & Phan Đình Duẩn (Đồng chủ trì thẩm định)"),
        ("Thời Gian Thực Hiện", "15/09/2026 – 17/09/2026 (Mốc kết thúc Giai đoạn 1 - Milestone M2)"),
        ("Giảng Viên Hướng Dẫn", "Thầy/Cô Bộ môn Công nghệ Phần mềm — Khoa Công nghệ Thông tin"),
        ("Căn Cứ Thẩm Định", "Chuẩn ISO/IEC/IEEE 29148:2018 & Khung Rubric Đồ án Tốt nghiệp"),
        ("Trạng Thái Cơ Sở", "ĐÃ ĐÓNG BĂNG CHÍNH THỨC (Requirements Baseline Frozen v1.0)")
    ]
    elements.append(make_metadata_table(meta))
    elements.append(make_para("", space_after=180))
    
    elements.append(make_heading("1. MỤC ĐÍCH BIÊN BẢN & Ý NGHĨA MỐC MILESTONE M2", level=1))
    elements.append(make_para("Biên bản này xác nhận việc hoàn tất toàn diện công tác khảo sát, phân tích và đặc tả yêu cầu cho hệ thống FocusFlow theo đúng tiến độ Tuần 1–3 trong kế hoạch WBS Gantt Chart. Việc phê chuẩn đóng băng cơ sở yêu cầu (Baseline Freeze) đánh dấu cột mốc Milestone M2, chuyển giao hồ sơ kỹ thuật sang Giai đoạn 2: Phân tích Hệ thống & Thiết kế Kiến trúc, CSDL (UML 2.5)."))
    
    elements.append(make_heading("2. BẢNG KIỂM TRA ĐÁNH GIÁ CHẤT LƯỢNG HỒ SƠ YÊU CẦU (QUALITY AUDIT CHECKLIST)", level=1))
    audit_headers = ["Tiêu chuẩn Đánh giá", "Yêu cầu Kiểm tra theo ISO 29148", "Hiện trạng Đạt được của FocusFlow", "Đánh giá"]
    audit_data = [
        ["1. Tính Đầy đủ (Completeness)", "Đặc tả trọn vẹn chức năng, phi chức năng, dữ liệu, ngoại lệ", "Đủ 13 nhóm FR, 5 NFRs định lượng, 14 thực thể, 10 BUSR", "ĐẠT (100%)"],
        ["2. Tính Nhất quán (Consistency)", "Không có mâu thuẫn giữa các tài liệu và biểu đồ", "Đã rà soát chéo giữa Problem Definition, Survey, SRS, RTM", "ĐẠT (100%)"],
        ["3. Tính Khả kiểm (Verifiability)", "Mọi yêu cầu đều có phương pháp và tiêu chí đo kiểm", "100% FR có Acceptance Criteria; NFR & KPI có công thức đo", "ĐẠT (100%)"],
        ["4. Tính Khả thi (Feasibility)", "Khả thi về kỹ thuật, thời gian và chi phí đồ án", "Phạm vi Core MVP rõ ràng; cô lập Out-of-scope phức tạp", "ĐẠT (100%)"],
        ["5. Tính Phi Mơ hồ (Unambiguous)", "Thuật ngữ chuẩn hóa, mỗi yêu cầu chỉ có 1 cách hiểu", "Định nghĩa thuật ngữ Canonical tại Mục 1.5 của SRS v1.0", "ĐẠT (100%)"],
        ["6. Tính Độc lập Giải pháp", "Không gán cứng vào công nghệ cụ thể trong quy tắc nghiệp vụ", "Tách bạch logic nghiệp vụ khỏi DBMS vật lý hay ngôn ngữ", "ĐẠT (100%)"],
        ["7. Tính Truy vết (Traceability)", "Mối liên kết 2 chiều xuôi - ngược được bảo đảm", "Ma trận RTM 6 tầng phủ 100% yêu cầu; 0 Orphan Element", "ĐẠT (100%)"],
        ["8. Năng lực Làm chủ AI", "Có cơ chế kiểm soát rủi ro LLM, timeout, quota, schema", "Mô hình 6 tầng kiểm soát AI; Hard Ceiling; Fallback Manual", "ĐẠT (100%)"]
    ]
    elements.append(make_table([1800, 2600, 3760, 1200], audit_headers, audit_data))
    
    elements.append(make_heading("3. BÁO CÁO GIẢI QUYẾT TOÀN DIỆN CÁC QUYẾT ĐỊNH MỞ (OPEN DECISIONS RESOLUTION)", level=1))
    elements.append(make_para("Toàn bộ 8 quyết định mở (OS-01 đến OS-08) đã được Product Owner phê duyệt chính thức:"))
    elements.append(make_bullet("Ngưỡng ghi nhận PARTIAL_COMPLETED: Có >= 1 task COMPLETED hoặc thời gian thực học đạt >= 50% thời lượng dự kiến. Dưới ngưỡng này ghi nhận CANCELLED.", bold_prefix="OS-01 (Phiên học gián đoạn): "))
    elements.append(make_bullet("Gói Free: 3 lộ trình hoạt động, 30 lượt gọi AI/tháng; Gói Premium: 15 lộ trình hoạt động, 300 lượt gọi AI/tháng.", bold_prefix="OS-02 (Định mức Quota AI): "))
    elements.append(make_bullet("Áp dụng chính sách Merge / Future Shift: Giữ nguyên toàn bộ task COMPLETED trong quá khứ; chỉ xóa và thay thế các task trong tương lai bằng Proposal mới.", bold_prefix="OS-03 (Apply Proposal đè lịch cũ): "))
    elements.append(make_bullet("Áp dụng thuật toán Earliest Deadline First (EDF): Ưu tiên xếp lịch cho Roadmap có hạn chót mục tiêu gần hơn khi cạnh tranh slot trống.", bold_prefix="OS-04 (Ưu tiên đa lộ trình): "))
    elements.append(make_bullet("Mã token ngẫu nhiên bảo mật độ dài 32-byte hex (CSPRN), sinh bằng thuật toán mật mã an toàn.", bold_prefix="OS-05 (Định dạng WebCal Token): "))
    elements.append(make_bullet("Cận dưới tối thiểu 0.5 giờ (30 phút)/ngày; Cận trên tối đa 14 giờ/ngày.", bold_prefix="OS-06 (Giới hạn Quỹ giờ Mode A): "))
    elements.append(make_bullet("Client gửi Heartbeat ping mỗi 60 giây để đồng bộ thời gian thực học; Backend tự động chốt phiên nếu mất kết nối quá 5 phút.", bold_prefix="OS-07 (Đồng bộ phiên học mất kết nối): "))
    elements.append(make_bullet("Áp dụng Exponential Backoff với Full Jitter (chờ từ 2s, 4s, tối đa 10s) cho lỗi quá tải 429/503.", bold_prefix="OS-08 (Retry Backoff AI): "))
    
    elements.append(make_heading("4. TUYÊN BỐ ĐÓNG BĂNG CƠ SỞ YÊU CẦU & KÝ DUYỆT CHUYỂN GIAO", level=1))
    elements.append(make_callout("TUYÊN BỐ ĐÓNG BĂNG CHÍNH THỨC (BASELINE FREEZE STATEMENT):", "Bộ hồ sơ Yêu cầu Phần mềm FocusFlow (gồm Khảo sát & Benchmarking, Business Goals & KPIs, System Actors & Personas, SRS v1.0, Business Rules, và RTM) CHÍNH THỨC ĐƯỢNG ĐÓNG BĂNG ở phiên bản 1.0 (Frozen Baseline v1.0). Mọi sự thay đổi yêu cầu từ thời điểm này bắt buộc phải tuân thủ Quy trình Quản lý Thay đổi (Change Control Procedure) và có sự phê chuẩn của Giảng viên hướng dẫn."))
    elements.append(make_para("XÁC NHẬN CHUYỂN GIAO SANG GIAI ĐOẠN 2: Hồ sơ kỹ thuật đủ điều kiện chuyển giao sang Giai đoạn Phân tích Hệ thống & Thiết kế Kiến trúc, CSDL (UML 2.5: Use Case, Activity, Sequence, State Machine, Class Diagram, ERD).", bold=True, space_before=120, space_after=180))
    
    sig_headers = ["Đại diện Nhóm Thực hiện (Lead BA / Architect)", "Đại diện Kiểm soát Chất lượng (Senior BA / QA Lead)"]
    sig_data = [
        ["(Ký và ghi rõ họ tên)\n\n\nVũ Toàn Thắng\nNgày: 17/09/2026", "(Ký và ghi rõ họ tên)\n\n\nPhan Đình Duẩn\nNgày: 17/09/2026"]
    ]
    elements.append(make_table([4680, 4680], sig_headers, sig_data))
    
    save_docx(elements, "WBS 2.4 - Thẩm định & Đóng băng cơ sở yêu cầu (Requirements Baseline Freeze).docx")

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    print("Starting generation of 7 WBS DOCX deliverables...")
    build_wbs_1_1()
    build_wbs_1_2()
    build_wbs_1_3()
    build_wbs_2_1()
    build_wbs_2_2()
    build_wbs_2_3()
    build_wbs_2_4()
    print("All 7 WBS DOCX deliverables generated successfully!")
