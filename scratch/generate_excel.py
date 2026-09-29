#!/usr/bin/env python3
import os
import zipfile
import datetime
import xml.etree.ElementTree as ET

TEMPLATE_PATH = "docs_ute/(2) IC-Work-Breakdown-Structure-with-Gantt-Chart Template.xlsx"
OUTPUT_PATH = "docs_ute/(2) FocusFlow-Work-Breakdown-Structure-with-Gantt-Chart.xlsx"

START_DATE = datetime.date(2026, 8, 28)
EXCEL_EPOCH = datetime.date(1899, 12, 30)

def to_serial(d):
    if d is None:
        return ""
    return str((d - EXCEL_EPOCH).days)

def col_letter(n):
    result = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

TOTAL_WEEKS = 15
DAYS_PER_WEEK = 7
TOTAL_DAYS = TOTAL_WEEKS * DAYS_PER_WEEK # 105 days
FIRST_DATE_COL = 9 # Col I
LAST_DATE_COL = FIRST_DATE_COL + TOTAL_DAYS - 1 # Col DI (113)

DAY_NAMES = ['F', 'Sa', 'Su', 'M', 'T', 'W', 'R']

col_to_date = {}
for i in range(TOTAL_DAYS):
    col_idx = FIRST_DATE_COL + i
    col_to_date[col_idx] = START_DATE + datetime.timedelta(days=i)

PHASES = [
    {
        "id": 1,
        "name": "Phase One: Khởi tạo dự án & Đặc tả yêu cầu (Tuần 1–3)",
        "start_col": FIRST_DATE_COL,
        "end_col": FIRST_DATE_COL + 21 - 1,
        "hdr_start_style": "11", "hdr_mid_style": "12",
        "bar_style": "53"
    },
    {
        "id": 2,
        "name": "Phase Two: Phân tích hệ thống & Thiết kế kiến trúc, CSDL (Tuần 4–6)",
        "start_col": FIRST_DATE_COL + 21,
        "end_col": FIRST_DATE_COL + 42 - 1,
        "hdr_start_style": "13", "hdr_mid_style": "14",
        "bar_style": "55"
    },
    {
        "id": 3,
        "name": "Phase Three: Lập trình chức năng cốt lõi MVP & Tích hợp AI (Tuần 7–11)",
        "start_col": FIRST_DATE_COL + 42,
        "end_col": FIRST_DATE_COL + 77 - 1,
        "hdr_start_style": "15", "hdr_mid_style": "16",
        "bar_style": "56"
    },
    {
        "id": 4,
        "name": "Phase Four: Kiểm thử, UAT & Đánh giá NFRs (Tuần 12–13)",
        "start_col": FIRST_DATE_COL + 77,
        "end_col": FIRST_DATE_COL + 91 - 1,
        "hdr_start_style": "17", "hdr_mid_style": "18",
        "bar_style": "57"
    },
    {
        "id": 5,
        "name": "Phase Five: Hoàn thiện Khóa luận, Slide & Bảo vệ tốt nghiệp (Tuần 14–15)",
        "start_col": FIRST_DATE_COL + 91,
        "end_col": FIRST_DATE_COL + 105 - 1,
        "hdr_start_style": "63", "hdr_mid_style": "64",
        "bar_style": "62"
    },
]

TASKS = [
    # PHASE 1
    ("1.0", "Khởi tạo & Định nghĩa bài toán (Project Inception & Problem Statement)", "", None, None, None, 1, True),
    ("1.1", "Khảo sát nhu cầu tự học và nghiên cứu đối sánh giải pháp (Benchmarking)", "Phan Đình Duẩn", datetime.date(2026, 8, 28), datetime.date(2026, 9, 2), 1.0, 1, False),
    ("1.2", "Thiết lập Business Goals & 5 chỉ số KPI định lượng", "Vũ Toàn Thắng", datetime.date(2026, 9, 1), datetime.date(2026, 9, 5), 1.0, 1, False),
    ("1.3", "Xác định tác nhân hệ thống & Phân tích chân dung người dùng (Personas)", "Phan Đình Duẩn", datetime.date(2026, 9, 4), datetime.date(2026, 9, 8), 1.0, 1, False),

    ("2.0", "Đặc tả yêu cầu phần mềm (Software Requirements Specification - SRS)", "", None, None, None, 1, True),
    ("2.1", "Soạn thảo hồ sơ SRS v1.0 theo chuẩn ISO/IEC/IEEE 29148:2018", "Vũ Toàn Thắng", datetime.date(2026, 9, 6), datetime.date(2026, 9, 12), 1.0, 1, False),
    ("2.2", "Xây dựng quy tắc nghiệp vụ (Business Rules: Strict Apply, Availability, Quota)", "Vũ Toàn Thắng", datetime.date(2026, 9, 9), datetime.date(2026, 9, 14), 1.0, 1, False),
    ("2.3", "Thiết lập ma trận truy vết yêu cầu (Requirement Traceability Matrix - RTM)", "Phan Đình Duẩn", datetime.date(2026, 9, 12), datetime.date(2026, 9, 16), 1.0, 1, False),
    ("2.4", "Thẩm định & Đóng băng cơ sở yêu cầu (Requirements Baseline Freeze)", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 9, 15), datetime.date(2026, 9, 17), 1.0, 1, False),

    # PHASE 2
    ("3.0", "Mô hình hóa phân tích hệ thống (System Analysis & UML Modeling)", "", None, None, None, 2, True),
    ("3.1", "Thiết kế Use Case Diagram & Đặc tả kịch bản Use Case chi tiết", "Phan Đình Duẩn", datetime.date(2026, 9, 18), datetime.date(2026, 9, 23), 0.8, 2, False),
    ("3.2", "Thiết kế Activity Diagrams (Onboarding, AI Scheduling, Session Execution)", "Phan Đình Duẩn", datetime.date(2026, 9, 22), datetime.date(2026, 9, 27), 0.5, 2, False),
    ("3.3", "Thiết kế Sequence Diagrams (Workflow M2, Overdue Shift, WebCal Feed)", "Vũ Toàn Thắng", datetime.date(2026, 9, 26), datetime.date(2026, 10, 1), 0.4, 2, False),
    ("3.4", "Thiết kế State Machine Diagram (Vòng đời Roadmap, Task, Session, Proposal)", "Vũ Toàn Thắng", datetime.date(2026, 9, 30), datetime.date(2026, 10, 4), 0.3, 2, False),

    ("4.0", "Thiết kế kiến trúc & Cơ sở dữ liệu (System Architecture & Database Design)", "", None, None, None, 2, True),
    ("4.1", "Thiết kế kiến trúc phần mềm tổng thể (Layered Architecture / C4 Model)", "Vũ Toàn Thắng", datetime.date(2026, 9, 25), datetime.date(2026, 10, 2), 0.4, 2, False),
    ("4.2", "Thiết kế sơ đồ cơ sở dữ liệu (Database Diagram / DB Diagram) & Mô hình hóa", "Vũ Toàn Thắng", datetime.date(2026, 9, 29), datetime.date(2026, 10, 5), 0.3, 2, False),
    ("4.3", "Xây dựng từ điển dữ liệu (Data Dictionary), Index & Ràng buộc toàn vẹn CSDL", "Vũ Toàn Thắng", datetime.date(2026, 10, 3), datetime.date(2026, 10, 7), 0.0, 2, False),
    ("4.4", "Viết các bản ghi quyết định kiến trúc (Architecture Decision Records - ADRs)", "Vũ Toàn Thắng", datetime.date(2026, 10, 5), datetime.date(2026, 10, 8), 0.0, 2, False),

    # PHASE 3
    ("5.0", "Thiết lập nền tảng & Module cơ sở (Project Setup & Foundation Modules)", "", None, None, None, 3, True),
    ("5.1", "Khởi tạo Repository, cấu hình dự án & Thiết lập CI/CD Pipeline tự động", "Vũ Toàn Thắng", datetime.date(2026, 10, 9), datetime.date(2026, 10, 14), 0.0, 3, False),
    ("5.2", "Xây dựng Module Xác thực & Hồ sơ người dùng (FR-AUTH: JWT, Session Guard)", "Phan Đình Duẩn", datetime.date(2026, 10, 12), datetime.date(2026, 10, 18), 0.0, 3, False),
    ("5.3", "Xây dựng Module Cấu hình thời gian rảnh lai (FR-AVAIL Mode A Quota & Mode B)", "Phan Đình Duẩn", datetime.date(2026, 10, 16), datetime.date(2026, 10, 22), 0.0, 3, False),

    ("6.0", "Phát triển Module Lập kế hoạch AI & Duyệt lịch (AI Planning & Approval Gate)", "", None, None, None, 3, True),
    ("6.1", "Tích hợp LLM API với Structured Outputs (JSON Schema Validation Gate)", "Vũ Toàn Thắng", datetime.date(2026, 10, 19), datetime.date(2026, 10, 26), 0.0, 3, False),
    ("6.2", "Xây dựng luồng sinh Milestones Cấp 1 & Schedule Proposal Cấp 2", "Vũ Toàn Thắng", datetime.date(2026, 10, 24), datetime.date(2026, 11, 1), 0.0, 3, False),
    ("6.3", "Phát triển giao diện chỉnh sửa đề xuất & Cơ chế Validation khi Apply", "Vũ Toàn Thắng", datetime.date(2026, 10, 30), datetime.date(2026, 11, 6), 0.0, 3, False),

    ("7.0", "Phát triển Không gian phiên học & Lịch ngoại vi (Study Session & Calendar)", "", None, None, None, 3, True),
    ("7.1", "Xây dựng Study Tool Suite (Pomodoro/Stopwatch, Checklist, Scratchpad & Note)", "Phan Đình Duẩn", datetime.date(2026, 10, 26), datetime.date(2026, 11, 3), 0.0, 3, False),
    ("7.2", "Xử lý gián đoạn phiên học & Hoàn trả task dở dang về Backlog", "Phan Đình Duẩn", datetime.date(2026, 11, 1), datetime.date(2026, 11, 6), 0.0, 3, False),
    ("7.3", "Phát triển thuật toán thích ứng quá hạn tất định (Deterministic Overdue Shift)", "Vũ Toàn Thắng", datetime.date(2026, 11, 4), datetime.date(2026, 11, 9), 0.0, 3, False),
    ("7.4", "Phát triển tính năng Tạm dừng lộ trình (Pause Roadmap & Domino Shift)", "Vũ Toàn Thắng", datetime.date(2026, 11, 7), datetime.date(2026, 11, 12), 0.0, 3, False),
    ("7.5", "Xây dựng Secure Token WebCal Subscription Feed & Xuất tệp tin .ics", "Phan Đình Duẩn", datetime.date(2026, 11, 6), datetime.date(2026, 11, 12), 0.0, 3, False),

    ("8.0", "Phát triển Module Báo cáo định lượng & Quản trị Quota (Analytics & Quota Guard)", "", None, None, None, 3, True),
    ("8.1", "Xây dựng Dashboard thống kê định lượng thời gian học & Tỷ lệ hoàn thành task", "Phan Đình Duẩn", datetime.date(2026, 11, 5), datetime.date(2026, 11, 10), 0.0, 3, False),
    ("8.2", "Tích hợp AI Review phân tích định tính từ số liệu thống kê & Key Takeaways", "Vũ Toàn Thắng", datetime.date(2026, 11, 8), datetime.date(2026, 11, 12), 0.0, 3, False),
    ("8.3", "Xây dựng Service-level Quota Guard Middleware & Mock Upgrade Sandbox", "Vũ Toàn Thắng", datetime.date(2026, 11, 8), datetime.date(2026, 11, 12), 0.0, 3, False),

    # PHASE 4
    ("9.0", "Kiểm thử phần mềm & Đo lường NFRs (Software Testing & NFR Verification)", "", None, None, None, 4, True),
    ("9.1", "Xây dựng Unit Tests & Integration Tests tự động cho toàn bộ API và Core Logic", "Phan Đình Duẩn", datetime.date(2026, 11, 13), datetime.date(2026, 11, 18), 0.0, 4, False),
    ("9.2", "Kiểm thử hiệu năng & Độ trễ thao tác UI (Kiểm chứng NFR 1 <= 60s, NFR 2 <= 500ms)", "Vũ Toàn Thắng", datetime.date(2026, 11, 16), datetime.date(2026, 11, 21), 0.0, 4, False),
    ("9.3", "Kiểm thử bảo mật (Sanitization, 0 secret leak, hash mật khẩu - NFR 3)", "Vũ Toàn Thắng", datetime.date(2026, 11, 19), datetime.date(2026, 11, 23), 0.0, 4, False),
    ("9.4", "Đánh giá khả năng tiếp cận & Responsive (Google Lighthouse Score >= 90 - NFR 5)", "Phan Đình Duẩn", datetime.date(2026, 11, 20), datetime.date(2026, 11, 24), 0.0, 4, False),

    ("10.0", "Thử nghiệm người dùng & Triển khai thực tế (UAT Testing & Cloud Deployment)", "", None, None, None, 4, True),
    ("10.1", "Triển khai hệ thống lên môi trường Staging/Production công khai", "Phan Đình Duẩn", datetime.date(2026, 11, 17), datetime.date(2026, 11, 21), 0.0, 4, False),
    ("10.2", "Tổ chức thử nghiệm UAT với >= 10 người dùng thật thuộc đối tượng mục tiêu", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 11, 20), datetime.date(2026, 11, 25), 0.0, 4, False),
    ("10.3", "Khảo sát đo lường điểm SUS (System Usability Scale) & Đánh giá 5 KPIs", "Vũ Toàn Thắng", datetime.date(2026, 11, 23), datetime.date(2026, 11, 26), 0.0, 4, False),

    # PHASE 5
    ("11.0", "Hoàn thiện báo cáo khóa luận tốt nghiệp (Thesis Report Writing & Formatting)", "", None, None, None, 5, True),
    ("11.1", "Soạn thảo Chương 1 (Tổng quan) & Chương 2 (Cơ sở lý thuyết & Hiện trạng)", "Phan Đình Duẩn", datetime.date(2026, 11, 27), datetime.date(2026, 12, 1), 0.0, 5, False),
    ("11.2", "Soạn thảo Chương 3 (Phân tích nghiệp vụ & Thiết kế hệ thống)", "Phan Đình Duẩn", datetime.date(2026, 11, 29), datetime.date(2026, 12, 4), 0.0, 5, False),
    ("11.3", "Soạn thảo Chương 4 (Hiện thực hóa hệ thống & Tích hợp AI)", "Vũ Toàn Thắng", datetime.date(2026, 12, 1), datetime.date(2026, 12, 6), 0.0, 5, False),
    ("11.4", "Soạn thảo Chương 5 (Thực nghiệm UAT, Đo lường KPI & Kết luận)", "Vũ Toàn Thắng", datetime.date(2026, 12, 3), datetime.date(2026, 12, 7), 0.0, 5, False),
    ("11.5", "Rà soát tính truy vết & Chuẩn hóa định dạng khóa luận tốt nghiệp", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 12, 6), datetime.date(2026, 12, 8), 0.0, 5, False),

    ("12.0", "Chuẩn bị & Bảo vệ khóa luận tốt nghiệp (Thesis Defense Preparation & Defense)", "", None, None, None, 5, True),
    ("12.1", "Thiết kế Slide báo cáo thuyết trình khoa học & Thu âm video demo kịch bản", "Vũ Toàn Thắng", datetime.date(2026, 12, 4), datetime.date(2026, 12, 8), 0.0, 5, False),
    ("12.2", "Chạy thử nghiệm tổng duyệt bảo vệ thử (Dry-run Defense & Mock Q&A)", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 12, 7), datetime.date(2026, 12, 9), 0.0, 5, False),
    ("12.3", "Tiếp thu góp ý của GVHD & Hoàn thiện hồ sơ khóa luận hoàn chỉnh", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 12, 8), datetime.date(2026, 12, 9), 0.0, 5, False),
    ("12.4", "Bảo vệ khóa luận chính thức trước Hội đồng chấm thi tốt nghiệp", "Vũ Toàn Thắng & Phan Đình Duẩn", datetime.date(2026, 12, 10), datetime.date(2026, 12, 10), 0.0, 5, False),
]

# Shared String Manager
class SharedStrings:
    def __init__(self):
        self.strings = []
        self.str_to_idx = {}

    def get_or_add(self, s):
        if s not in self.str_to_idx:
            idx = len(self.strings)
            self.strings.append(s)
            self.str_to_idx[s] = idx
            return idx
        return self.str_to_idx[s]

    def to_xml(self):
        root = ET.Element("sst", {
            "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "count": str(len(self.strings)),
            "uniqueCount": str(len(self.strings))
        })
        for s in self.strings:
            si = ET.SubElement(root, "si")
            t = ET.SubElement(si, "t")
            t.text = s
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

sst = SharedStrings()

def generate_sheet_xml(is_blank=False):
    # Root worksheet
    ws = ET.Element("worksheet", {
        "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "xmlns:mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "mc:Ignorable": "x14ac",
        "xmlns:x14ac": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac"
    })
    
    # SheetViews
    svs = ET.SubElement(ws, "sheetViews")
    sv = ET.SubElement(svs, "sheetView", {"tabSelected": "1" if not is_blank else "0", "workbookViewId": "0"})
    
    # SheetFormatPr
    ET.SubElement(ws, "sheetFormatPr", {"defaultRowHeight": "15.0", "x14ac:dyDescent": "0.25"})
    
    # Cols
    cols = ET.SubElement(ws, "cols")
    ET.SubElement(cols, "col", {"min": "1", "max": "1", "width": "3.22", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "2", "max": "2", "width": "12.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "3", "max": "3", "width": "52.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "4", "max": "4", "width": "28.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "5", "max": "6", "width": "12.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "7", "max": "7", "width": "10.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "8", "max": "8", "width": "12.0", "customWidth": "1"})
    ET.SubElement(cols, "col", {"min": "9", "max": str(LAST_DATE_COL), "width": "3.0", "customWidth": "1"})
    
    # SheetData
    sd = ET.SubElement(ws, "sheetData")
    
    def add_cell(row_elem, ref, style, val_type=None, val=None, formula=None):
        c = ET.SubElement(row_elem, "c", {"r": ref, "s": str(style)})
        if val_type:
            c.attrib["t"] = val_type
        if formula is not None:
            f = ET.SubElement(c, "f")
            f.text = formula
        if val is not None and val != "":
            v = ET.SubElement(c, "v")
            v.text = str(val)
        return c

    # Row 1: Title
    r1 = ET.SubElement(sd, "row", {"r": "1", "ht": "36.0", "customHeight": "1"})
    add_cell(r1, "A1", 4)
    b1_text = "FocusFlow — Work Breakdown Structure & Gantt Chart (15 Tuần)" if not is_blank else "Work Breakdown Structure With Gantt Chart Template"
    add_cell(r1, "B1", 0, "s", sst.get_or_add(b1_text))
    for c_idx in range(3, LAST_DATE_COL + 1):
        add_cell(r1, col_letter(c_idx) + "1", 0)

    # Row 2: Project Title
    r2 = ET.SubElement(sd, "row", {"r": "2", "ht": "18.0", "customHeight": "1"})
    add_cell(r2, "A2", 4)
    add_cell(r2, "B2", 3, "s", sst.get_or_add("Project Title"))
    proj_name = "FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI" if not is_blank else ""
    add_cell(r2, "C2", 20, "s", sst.get_or_add(proj_name) if proj_name else None)
    add_cell(r2, "D2", 20)
    for c_idx in range(5, LAST_DATE_COL + 1):
        add_cell(r2, col_letter(c_idx) + "2", 0)

    # Row 3: Project Manager
    r3 = ET.SubElement(sd, "row", {"r": "3", "ht": "18.0", "customHeight": "1"})
    add_cell(r3, "A3", 4)
    add_cell(r3, "B3", 3, "s", sst.get_or_add("Project Manager"))
    pm_name = "Vũ Toàn Thắng (23110329) & Phan Đình Duẩn (23110192)" if not is_blank else ""
    add_cell(r3, "C3", 20, "s", sst.get_or_add(pm_name) if pm_name else None)
    add_cell(r3, "D3", 20)
    for c_idx in range(5, LAST_DATE_COL + 1):
        add_cell(r3, col_letter(c_idx) + "3", 0)

    # Row 4: Company Name
    r4 = ET.SubElement(sd, "row", {"r": "4", "ht": "18.0", "customHeight": "1"})
    add_cell(r4, "A4", 4)
    add_cell(r4, "B4", 3, "s", sst.get_or_add("Company Name"))
    comp_name = "Trường ĐH Sư phạm Kỹ thuật TP.HCM (HCMUTE) — Khoa CNTT" if not is_blank else ""
    add_cell(r4, "C4", 20, "s", sst.get_or_add(comp_name) if comp_name else None)
    add_cell(r4, "D4", 20)
    for c_idx in range(5, LAST_DATE_COL + 1):
        add_cell(r4, col_letter(c_idx) + "4", 0)

    # Row 5: Date & Phase Headers
    r5 = ET.SubElement(sd, "row", {"r": "5", "ht": "20.0", "customHeight": "1"})
    add_cell(r5, "A5", 4)
    add_cell(r5, "B5", 3, "s", sst.get_or_add("Date"))
    add_cell(r5, "C5", 21, "s", sst.get_or_add("28/08/2026") if not is_blank else None)
    add_cell(r5, "D5", 21)
    for c_idx in range(5, FIRST_DATE_COL):
        add_cell(r5, col_letter(c_idx) + "5", 0)
    
    # Phase headers in Row 5
    for p in PHASES:
        p_name = p["name"] if not is_blank else f"Phase {p['id']}"
        add_cell(r5, col_letter(p["start_col"]) + "5", p["hdr_start_style"], "s", sst.get_or_add(p_name))
        for c_idx in range(p["start_col"] + 1, p["end_col"] + 1):
            add_cell(r5, col_letter(c_idx) + "5", p["hdr_mid_style"])

    # Row 6: Empty spacer row
    r6 = ET.SubElement(sd, "row", {"r": "6", "ht": "6.0", "customHeight": "1"})
    for c_idx in range(1, LAST_DATE_COL + 1):
        add_cell(r6, col_letter(c_idx) + "6", 4)

    # Row 7: Column Titles & Week Headers
    r7 = ET.SubElement(sd, "row", {"r": "7", "ht": "18.0", "customHeight": "1"})
    add_cell(r7, "A7", 4)
    headers = [
        ("B7", "WBS Number"), ("C7", "Task Title"), ("D7", "Task Owner"),
        ("E7", "Start Date"), ("F7", "Due Date"), ("G7", "Duration"), ("H7", "% of Task Complete")
    ]
    for ref, h_title in headers:
        add_cell(r7, ref, 22, "s", sst.get_or_add(h_title))
    
    # Weeks in Row 7
    for w in range(1, TOTAL_WEEKS + 1):
        c_start = FIRST_DATE_COL + (w - 1) * DAYS_PER_WEEK
        add_cell(r7, col_letter(c_start) + "7", 23, "s", sst.get_or_add(f"Week {w}"))
        for c_idx in range(c_start + 1, c_start + DAYS_PER_WEEK - 1):
            add_cell(r7, col_letter(c_idx) + "7", 24)
        add_cell(r7, col_letter(c_start + DAYS_PER_WEEK - 1) + "7", 25)

    # Row 8: Day of week abbreviations
    r8 = ET.SubElement(sd, "row", {"r": "8", "ht": "18.0", "customHeight": "1"})
    add_cell(r8, "A8", 4)
    for col_char in ['B', 'C', 'D', 'E', 'F', 'G', 'H']:
        add_cell(r8, f"{col_char}8", 34)
    for c_idx in range(FIRST_DATE_COL, LAST_DATE_COL + 1):
        day_offset = (c_idx - FIRST_DATE_COL) % DAYS_PER_WEEK
        d_name = DAY_NAMES[day_offset]
        style = 35 if day_offset == 0 else (37 if day_offset == DAYS_PER_WEEK - 1 else 36)
        add_cell(r8, col_letter(c_idx) + "8", style, "s", sst.get_or_add(d_name))

    # Task Rows (Row 9 onward)
    task_list = TASKS if not is_blank else [
        (f"{i//5+1}.{i%5+1}" if i%5!=0 else f"{i//5+1}.0", "", "", None, None, 0.0, (i//5+1), i%5==0)
        for i in range(25)
    ]
    
    for idx, task in enumerate(task_list):
        r_num = 9 + idx
        wbs, title, owner, start_d, due_d, pct, p_idx, is_summary = task
        phase = PHASES[min(p_idx - 1, len(PHASES) - 1)]
        
        row_elem = ET.SubElement(sd, "row", {"r": str(r_num), "ht": "20.0" if is_summary else "18.0", "customHeight": "1"})
        add_cell(row_elem, f"A{r_num}", 4)
        
        if is_summary:
            add_cell(row_elem, f"B{r_num}", 41, None, wbs)
            add_cell(row_elem, f"C{r_num}", 42, "s", sst.get_or_add(title) if title else None)
            add_cell(row_elem, f"D{r_num}", 42)
            add_cell(row_elem, f"E{r_num}", 43)
            add_cell(row_elem, f"F{r_num}", 43)
            add_cell(row_elem, f"G{r_num}", 44)
            add_cell(row_elem, f"H{r_num}", 45)
            # Gantt columns in summary row: styled with 46
            for c_idx in range(FIRST_DATE_COL, LAST_DATE_COL + 1):
                add_cell(row_elem, col_letter(c_idx) + str(r_num), 46)
        else:
            add_cell(row_elem, f"B{r_num}", 47, None, wbs)
            add_cell(row_elem, f"C{r_num}", 48, "s", sst.get_or_add(title) if title else None)
            add_cell(row_elem, f"D{r_num}", 48, "s", sst.get_or_add(owner) if owner else None)
            
            # Start Date & Due Date
            if start_d:
                add_cell(row_elem, f"E{r_num}", 49, None, to_serial(start_d))
            else:
                add_cell(row_elem, f"E{r_num}", 49)
                
            if due_d:
                add_cell(row_elem, f"F{r_num}", 49, None, to_serial(due_d))
            else:
                add_cell(row_elem, f"F{r_num}", 49)
                
            # Duration Formula: =DAYS(F{r},E{r})+1
            if start_d and due_d:
                dur_days = (due_d - start_d).days + 1
                add_cell(row_elem, f"G{r_num}", 50, None, str(dur_days), f"DAYS(F{r_num},E{r_num})+1")
            else:
                add_cell(row_elem, f"G{r_num}", 50, None, "0", f"DAYS(F{r_num},E{r_num})+1")
                
            # % Complete
            pct_val = f"{pct:.2f}" if pct is not None else "0.0"
            add_cell(row_elem, f"H{r_num}", 51, None, pct_val)
            
            # Gantt bar cells
            for c_idx in range(FIRST_DATE_COL, LAST_DATE_COL + 1):
                d = col_to_date[c_idx]
                if start_d and due_d and (start_d <= d <= due_d):
                    cell_style = phase["bar_style"]
                else:
                    cell_style = "52"
                add_cell(row_elem, col_letter(c_idx) + str(r_num), cell_style)

    # Empty tail rows up to 100 rows total
    total_task_rows = len(task_list)
    for tail_idx in range(total_task_rows, 80):
        r_num = 9 + tail_idx
        row_elem = ET.SubElement(sd, "row", {"r": str(r_num), "ht": "18.0", "customHeight": "1"})
        add_cell(row_elem, f"A{r_num}", 4)
        add_cell(row_elem, f"B{r_num}", 47)
        add_cell(row_elem, f"C{r_num}", 48)
        add_cell(row_elem, f"D{r_num}", 48)
        add_cell(row_elem, f"E{r_num}", 49)
        add_cell(row_elem, f"F{r_num}", 49)
        add_cell(row_elem, f"G{r_num}", 50, None, "0", f"DAYS(F{r_num},E{r_num})+1")
        add_cell(row_elem, f"H{r_num}", 51, None, "0.0")
        for c_idx in range(FIRST_DATE_COL, LAST_DATE_COL + 1):
            add_cell(row_elem, col_letter(c_idx) + str(r_num), 52)

    # MergeCells
    merges = ET.SubElement(ws, "mergeCells")
    merge_list = [
        "C2:D2", "C3:D3", "C4:D4", "C5:D5",
        "B7:B8", "C7:C8", "D7:D8", "E7:E8", "F7:F8", "G7:G8", "H7:H8"
    ]
    # Phase merges in Row 5
    for p in PHASES:
        merge_list.append(f"{col_letter(p['start_col'])}5:{col_letter(p['end_col'])}5")
        
    # Week merges in Row 7
    for w in range(1, TOTAL_WEEKS + 1):
        c_start = FIRST_DATE_COL + (w - 1) * DAYS_PER_WEEK
        c_end = c_start + DAYS_PER_WEEK - 1
        merge_list.append(f"{col_letter(c_start)}7:{col_letter(c_end)}7")
        
    merges.attrib["count"] = str(len(merge_list))
    for m_ref in merge_list:
        ET.SubElement(merges, "mergeCell", {"ref": m_ref})
        
    # PageMargins
    ET.SubElement(ws, "pageMargins", {
        "left": "0.7", "right": "0.7", "top": "0.75", "bottom": "0.75",
        "header": "0.3", "footer": "0.3"
    })
    
    return ET.tostring(ws, encoding="utf-8", xml_declaration=True)

# Generate sheet1 and sheet2 XMLs
sheet1_bytes = generate_sheet_xml(is_blank=False)
sheet2_bytes = generate_sheet_xml(is_blank=True)
sst_bytes = sst.to_xml()

# Update styles.xml to add Phase 5 Header fill and xfs
with zipfile.ZipFile(TEMPLATE_PATH, "r") as z_in:
    ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    st_tree = ET.fromstring(z_in.read("xl/styles.xml"))
    
    # Check fills
    fills = st_tree.find("ns:fills", ns)
    fill_count = int(fills.attrib.get("count", len(fills)))
    new_fill_id = fill_count
    # Add Dark Green fill
    new_fill = ET.Element("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}fill")
    pf = ET.SubElement(new_fill, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}patternFill", {"patternType": "solid"})
    ET.SubElement(pf, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}fgColor", {"rgb": "FF375623"})
    ET.SubElement(pf, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}bgColor", {"indexed": "64"})
    fills.append(new_fill)
    fills.attrib["count"] = str(fill_count + 1)
    
    # Check cellXfs
    cell_xfs = st_tree.find("ns:cellXfs", ns)
    xf_count = int(cell_xfs.attrib.get("count", len(cell_xfs)))
    
    # xf 63: Phase 5 start header (border 5, fill new_fill_id, font 6)
    xf63 = ET.Element("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}xf", {
        "applyAlignment": "1", "applyBorder": "1", "applyFill": "1", "applyFont": "1",
        "borderId": "5", "fillId": str(new_fill_id), "fontId": "6", "numFmtId": "0", "xfId": "0"
    })
    ET.SubElement(xf63, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}alignment", {"horizontal": "left", "vertical": "center"})
    cell_xfs.append(xf63)
    
    # xf 64: Phase 5 mid header (border 6, fill new_fill_id, font 6)
    xf64 = ET.Element("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}xf", {
        "applyAlignment": "1", "applyBorder": "1", "applyFill": "1", "applyFont": "1",
        "borderId": "6", "fillId": str(new_fill_id), "fontId": "6", "numFmtId": "0", "xfId": "0"
    })
    ET.SubElement(xf64, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}alignment", {"horizontal": "left", "vertical": "center"})
    cell_xfs.append(xf64)
    
    cell_xfs.attrib["count"] = str(xf_count + 2)
    styles_bytes = ET.tostring(st_tree, encoding="utf-8", xml_declaration=True)
    
    # Update workbook.xml: rename sheet 1
    wb_tree = ET.fromstring(z_in.read("xl/workbook.xml"))
    sheet1_elem = wb_tree.find(".//ns:sheet[@sheetId='1']", ns)
    if sheet1_elem is not None:
        sheet1_elem.attrib["name"] = "WBS with Gantt Chart FOCUSFLOW"
    workbook_bytes = ET.tostring(wb_tree, encoding="utf-8", xml_declaration=True)

    # Now write new output zip
    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if item.filename == "xl/worksheets/sheet1.xml":
                z_out.writestr(item, sheet1_bytes)
            elif item.filename == "xl/worksheets/sheet2.xml":
                z_out.writestr(item, sheet2_bytes)
            elif item.filename == "xl/sharedStrings.xml":
                z_out.writestr(item, sst_bytes)
            elif item.filename == "xl/styles.xml":
                z_out.writestr(item, styles_bytes)
            elif item.filename == "xl/workbook.xml":
                z_out.writestr(item, workbook_bytes)
            else:
                z_out.writestr(item, z_in.read(item.filename))

print("Successfully generated:", OUTPUT_PATH)
print("File size:", os.path.getsize(OUTPUT_PATH), "bytes")
