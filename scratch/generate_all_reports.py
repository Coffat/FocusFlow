#!/usr/bin/env python3
import os
import zipfile
import xml.etree.ElementTree as ET

TEMPLATE_PATH = "docs_ute/PROJECT STATUS REPORT.docx"

WEEKS_DATA = [
    {
        "week_num": 1,
        "week_str": "01",
        "date_range": "Từ ngày 28/08/2026 đến ngày 03/09/2026",
        "send_date": "03/09/2026",
        "summary": [
            ("Tiến độ (Schedule)", "🟢 Green", "Dự án khởi động đúng ngày 28/08/2026, hoàn thành khảo sát và xác lập mục tiêu theo đúng tiến độ kế hoạch."),
            ("Phạm vi (Scope)", "🟢 Green", "Đã thống nhất phạm vi cốt lõi Core MVP (không làm ứng dụng mobile native và cổng thanh toán thực tế)."),
            ("Chất lượng (Quality)", "🟢 Green", "Bảng phân tích đối sánh 3 giải pháp hiện có hoàn thành chi tiết, đáp ứng tiêu chí TC1 khung Rubric tốt nghiệp."),
            ("Rủi ro (Risk)", "🟢 Green", "Nhóm đã thiết lập quy trình làm việc và các kênh trao đổi; chưa phát sinh trở ngại kỹ thuật lớn.")
        ],
        "accomplishments": [
            ("1.0", "Khởi tạo dự án & Họp Kick-off định hướng đề tài", "Vũ Toàn Thắng & Phan Đình Duẩn", "Hoàn thành 100%", "Họp với GVHD ThS. Vũ Đình Bảo, chốt tên đề tài và kế hoạch tổng thể"),
            ("1.1", "Khảo sát nhu cầu tự học và nghiên cứu đối sánh giải pháp", "Phan Đình Duẩn", "Hoàn thành 100%", "Đối sánh chi tiết Google Calendar, Notion và Chatbots độc lập"),
            ("1.2", "Thiết lập Business Goals & 5 chỉ số KPI định lượng", "Vũ Toàn Thắng", "Hoàn thành 100%", "Xác lập 5 KPIs: Plan Creation Time <= 5m, Session Efficiency >= 80%, SUS >= 80...")
        ],
        "planned": [
            ("1.3", "Xác định tác nhân hệ thống & Phân tích chân dung người dùng (Personas)", "Phan Đình Duẩn", "08/09/2026", "High"),
            ("2.1", "Soạn thảo hồ sơ SRS v1.0 theo chuẩn ISO/IEC/IEEE 29148:2018", "Vũ Toàn Thắng", "12/09/2026", "High"),
            ("2.2", "Xây dựng quy tắc nghiệp vụ cốt lõi (Business Rules & Transitions)", "Vũ Toàn Thắng", "14/09/2026", "High")
        ],
        "risks": [
            ("Risk", "Nguy cơ lạm dụng và phát sinh chi phí API LLM ngoài dự kiến khi thử nghiệm phân rã lộ trình", "Trung bình", "Thiết lập hạn mức ngân sách cứng (Hard Cap Budget) tại tài khoản nhà cung cấp và thiết kế Quota Middleware sớm", "Vũ Toàn Thắng", "Monitor"),
            ("Risk", "Người dùng tự học có thời gian biểu không cố định, khó áp dụng time-blocking truyền thống", "Thấp", "Nghiên cứu mô hình thời gian rảnh lai (Hybrid Availability: Mode A Quota & Mode B Slots) đưa vào SRS", "Phan Đình Duẩn", "In-Progress")
        ],
        "milestones": [
            ("Hoàn thiện Hồ sơ Yêu cầu & Đặc tả SRS v1.0 (Milestone 1)", "17/09/2026", "17/09/2026", "On-track"),
            ("Hoàn thành Phân tích UML & Thiết kế Kiến trúc, Database Diagram (Milestone 2)", "08/10/2026", "08/10/2026", "On-track")
        ]
    },
    {
        "week_num": 2,
        "week_str": "02",
        "date_range": "Từ ngày 04/09/2026 đến ngày 10/09/2026",
        "send_date": "10/09/2026",
        "summary": [
            ("Tiến độ (Schedule)", "🟢 Green", "Hoàn thành đúng tiến độ đặc tả chân dung người dùng và bộ quy tắc nghiệp vụ cốt lõi."),
            ("Phạm vi (Scope)", "🟡 Amber", "Phát sinh bài toán xếp lịch khi người dùng tham gia đồng thời nhiều lộ trình học; đã bổ sung quy tắc Soft Overflow 30 phút."),
            ("Chất lượng (Quality)", "🟢 Green", "Các quy tắc chuyển đổi trạng thái (State Transitions) của Roadmap, Task, Session và Schedule Proposal được định nghĩa chặt chẽ."),
            ("Rủi ro (Risk)", "🟢 Green", "Các vướng mắc nghiệp vụ được phân tích và xử lý kịp thời, không ảnh hưởng đến mốc chốt SRS.")
        ],
        "accomplishments": [
            ("1.3", "Xác định tác nhân hệ thống & Phân tích chân dung người dùng", "Phan Đình Duẩn", "Hoàn thành 100%", "Phân định rõ Learner (End-User) và Administrator (Service Role Quota Guard)"),
            ("2.1", "Soạn thảo nội dung đặc tả yêu cầu SRS v1.0 (Phần 1 - 4)", "Vũ Toàn Thắng", "Hoàn thành 75%", "Hoàn thành phần Giới thiệu, Bối cảnh, Actors và Business Requirements"),
            ("2.2", "Xây dựng quy tắc nghiệp vụ (Business Rules: Strict Apply, Availability, Quota)", "Vũ Toàn Thắng", "Hoàn thành 100%", "Định nghĩa mô hình thời gian rảnh lai và cơ chế Strict Apply Proposal")
        ],
        "planned": [
            ("2.1", "Hoàn thiện toàn bộ các yêu cầu chức năng (FRs) và phi chức năng (NFRs) trong SRS", "Vũ Toàn Thắng", "12/09/2026", "High"),
            ("2.3", "Thiết lập ma trận truy vết yêu cầu (Requirement Traceability Matrix - RTM)", "Phan Đình Duẩn", "16/09/2026", "High"),
            ("2.4", "Rà soát chéo, Audit và đóng băng cơ sở yêu cầu (Baseline Freeze)", "Vũ Toàn Thắng & Phan Đình Duẩn", "17/09/2026", "High")
        ],
        "risks": [
            ("Issue", "Khả năng AI sinh kế hoạch học tập quá tải hoặc tràn ngoài khung giờ rảnh của người dùng", "Cao", "Xây dựng Backend Hard Ceiling Enforcement: Backend kiểm tra tổng thời lượng task trước khi cho phép Apply, cấm vượt trần", "Vũ Toàn Thắng", "Closed"),
            ("Risk", "Mô hình ngôn ngữ lớn (LLM) trả về kết quả không đúng schema JSON mong muốn", "Trung bình", "Yêu cầu sử dụng cơ chế Structured Outputs (JSON Schema) và thiết kế bộ lọc Validation Gate tại tầng dịch vụ backend", "Vũ Toàn Thắng", "In-Progress")
        ],
        "milestones": [
            ("Đóng băng Cơ sở Yêu cầu & Phê duyệt SRS v1.0 (Milestone 1)", "17/09/2026", "17/09/2026", "On-track"),
            ("Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)", "08/10/2026", "08/10/2026", "On-track")
        ]
    },
    {
        "week_num": 3,
        "week_str": "03",
        "date_range": "Từ ngày 11/09/2026 đến ngày 17/09/2026",
        "send_date": "17/09/2026",
        "summary": [
            ("Tiến độ (Schedule)", "🟢 Green", "Hoàn thành 100% Phase 1 đúng thời hạn 21 ngày; đạt mốc Milestone 1 quan trọng của dự án."),
            ("Phạm vi (Scope)", "🟢 Green", "Hồ sơ SRS v1.0 được đóng băng cơ sở (Baseline Freeze), bảo đảm không bị Scope Creep trong các giai đoạn sau."),
            ("Chất lượng (Quality)", "🟢 Green", "Hoàn thiện Ma trận truy vết 100% từ Vấn đề bài toán -> KPIs -> Yêu cầu chức năng -> NFRs định lượng."),
            ("Rủi ro (Risk)", "🟢 Green", "Đã báo cáo kết quả Phase 1 với ThS. Vũ Đình Bảo và nhận được định hướng chuyển tiếp sang Phase 2.")
        ],
        "accomplishments": [
            ("2.1", "Hoàn thiện toàn diện tài liệu Software Requirements Specification (SRS v1.0)", "Vũ Toàn Thắng", "Hoàn thành 100%", "Tuân thủ chuẩn ISO/IEC/IEEE 29148:2018 với 8 nhóm FRs và 5 NFRs định lượng"),
            ("2.3", "Thiết lập ma trận truy vết yêu cầu (Requirement Traceability Matrix)", "Phan Đình Duẩn", "Hoàn thành 100%", "Đảm bảo tính khả chứng và liên kết 2 chiều giữa bài toán thực tế và chức năng"),
            ("2.4", "Rà soát, thẩm định và chính thức đóng băng yêu cầu (Baseline Freeze)", "Vũ Toàn Thắng & Phan Đình Duẩn", "Hoàn thành 100%", "Cả 2 thành viên ký duyệt baseline, sẵn sàng cho công tác phân tích thiết kế")
        ],
        "planned": [
            ("3.1", "Thiết kế Use Case Diagram tổng thể & Đặc tả kịch bản Use Case chi tiết", "Phan Đình Duẩn", "23/09/2026", "High"),
            ("3.2", "Thiết kế Activity Diagrams (Onboarding, AI Scheduling, Session Execution)", "Phan Đình Duẩn", "27/09/2026", "High"),
            ("4.1", "Khởi động nghiên cứu kiến trúc phần mềm tổng thể (Layered Architecture / C4 Model)", "Vũ Toàn Thắng", "02/10/2026", "High")
        ],
        "risks": [
            ("Risk", "Nguy cơ độ trễ phản hồi từ dịch vụ AI vượt quá giới hạn cam kết (NFR 1: <= 60s)", "Cao", "Thiết lập ngắt cứng (Hard Timeout) ở giây thứ 55, trả về mã lỗi có cấu trúc kèm tùy chọn Thử lại hoặc Tạo kế hoạch thủ công", "Vũ Toàn Thắng", "Monitor"),
            ("Risk", "Sự thiếu nhất quán giữa mô hình ca sử dụng (Use Case) và kiến trúc cơ sở dữ liệu sau này", "Trung bình", "Thống nhất quy trình chuyển giao: Use Case & Activity Diagram -> Sequence Diagram -> Database Diagram & API specs", "Phan Đình Duẩn", "Open")
        ],
        "milestones": [
            ("Hoàn thiện Hồ sơ Yêu cầu & Đặc tả SRS v1.0 (Milestone 1)", "17/09/2026", "17/09/2026", "Completed"),
            ("Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)", "08/10/2026", "08/10/2026", "On-track")
        ]
    },
    {
        "week_num": 4,
        "week_str": "04",
        "date_range": "Từ ngày 18/09/2026 đến ngày 24/09/2026",
        "send_date": "24/09/2026",
        "summary": [
            ("Tiến độ (Schedule)", "🟢 Green", "Bắt đầu Phase 2 đúng kế hoạch; hoàn thành biểu đồ Use Case Diagram và phần lớn Activity Diagrams."),
            ("Phạm vi (Scope)", "🟢 Green", "Bám sát 8 ca sử dụng trọng tâm đã được phê duyệt trong SRS v1.0."),
            ("Chất lượng (Quality)", "🟢 Green", "Các kịch bản Use Case và luồng hoạt động Activity Diagram được mô hình hóa chặt chẽ theo chuẩn UML."),
            ("Rủi ro (Risk)", "🟢 Green", "Đang chuẩn bị kỹ lưỡng cho công tác thiết kế Database Diagram và Sequence Diagram ở tuần tiếp theo.")
        ],
        "accomplishments": [
            ("3.1", "Thiết kế Use Case Diagram tổng quát & Đặc tả kịch bản Use Case chi tiết", "Phan Đình Duẩn", "Hoàn thành 100%", "Hoàn thiện biểu đồ Use Case mức hệ thống và kịch bản luồng chính/rẽ nhánh"),
            ("3.2", "Thiết kế Activity Diagrams (Onboarding, AI Scheduling, Session Execution)", "Phan Đình Duẩn", "Hoàn thành 80%", "Đã hoàn thành 2/3 luồng hoạt động chính, đang hoàn thiện luồng gián đoạn phiên học"),
            ("4.1", "Khảo sát và phác thảo cấu trúc kiến trúc tổng thể (Layered Architecture / C4 Model)", "Vũ Toàn Thắng", "Hoàn thành 40%", "Định hình 3 tầng kiến trúc (Presentation, Service Layer, Data Layer) và tích hợp LLM")
        ],
        "planned": [
            ("3.3", "Thiết kế Sequence Diagrams (Workflow M2, Deterministic Overdue, WebCal Feed)", "Vũ Toàn Thắng", "01/10/2026", "High"),
            ("3.4", "Thiết kế State Machine Diagram (Vòng đời Roadmap, Task, Session)", "Vũ Toàn Thắng", "04/10/2026", "Medium"),
            ("4.2", "Thiết kế sơ đồ cơ sở dữ liệu (Database Diagram / DB Diagram) & Mô hình hóa dữ liệu", "Vũ Toàn Thắng", "05/10/2026", "High"),
            ("4.3", "Xây dựng từ điển dữ liệu (Data Dictionary), Index & Ràng buộc toàn vẹn CSDL", "Vũ Toàn Thắng", "07/10/2026", "High")
        ],
        "risks": [
            ("Issue", "Cần giải thuật tối ưu cho tính năng Tạm dừng lộ trình (Domino Shift) để tránh cập nhật quá nhiều dòng dữ liệu khi tịnh tiến ngày học", "Cao", "Thiết kế Database Diagram cho phép quản lý ngày học linh hoạt (theo slot/offset tương đối) thay vì ngày tuyệt đối cho từng task", "Vũ Toàn Thắng", "In-Progress"),
            ("Risk", "Tích hợp dịch vụ WebCal Feed có nguy cơ rò rỉ dữ liệu lịch nếu không có cơ chế xác thực phù hợp", "Trung bình", "Sử dụng URL chứa mã bí mật ngẫu nhiên (Secure Token WebCal Feed) và cung cấp tính năng Reset Token trên UI", "Phan Đình Duẩn", "Closed")
        ],
        "milestones": [
            ("Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)", "08/10/2026", "08/10/2026", "On-track"),
            ("Hoàn thiện Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3)", "12/11/2026", "12/11/2026", "On-track")
        ]
    }
]

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
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz": str(size)
        })
        ET.SubElement(rPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}szCs", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}szCs": str(size)
        })
        
    t = ET.SubElement(r, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t", {
        "{http://www.w3.org/XML/1998/namespace}space": "preserve"
    })
    t.text = text
    return p

def make_cell(text, is_header=False, width_dxa=1872):
    tc = ET.Element("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
    tcPr = ET.SubElement(tc, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcPr")
    
    tcBorders = ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcBorders")
    for b_name in ["top", "left", "bottom", "right"]:
        ET.SubElement(tcBorders, f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{b_name}", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "single",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz": "6",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space": "0",
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color": "000000"
        })
        
    shd_color = "e9eef6" if is_header else "f8fafd"
    ET.SubElement(tcPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val": "clear",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color": "auto",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill": shd_color
    })
    
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
    
    tblGrid = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblGrid")
    for w in col_widths:
        ET.SubElement(tblGrid, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}gridCol", {
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": str(w)
        })
        
    tr_h = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
    trPr_h = ET.SubElement(tr_h, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}trPr")
    ET.SubElement(trPr_h, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblHeader")
    for i, h_text in enumerate(headers):
        tr_h.append(make_cell(h_text, is_header=True, width_dxa=col_widths[i]))
        
    for row in data_rows:
        tr = ET.SubElement(tbl, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
        for i, val in enumerate(row):
            tr.append(make_cell(val, is_header=False, width_dxa=col_widths[i]))
            
    return tbl

def build_document_xml(w_data):
    doc = ET.Element("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document", {
        "xmlns:w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "xmlns:m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "xmlns:w14": "http://schemas.microsoft.com/office/word/2010/wordml"
    })
    body = ET.SubElement(doc, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body")
    
    # 1. Main Title
    body.append(make_para("PROJECT STATUS REPORT", style="Heading1", bold=True, size=32, align="center", space_after=60, space_before=120))
    body.append(make_para("(BÁO CÁO TÌNH TRẠNG DỰ ÁN)", style="Heading1", bold=True, size=28, align="center", space_after=240, space_before=0))
    
    # 2. Metadata
    body.append(make_para("Dự Án: FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI", bold=True, space_after=60))
    body.append(make_para(f"Kỳ Báo Cáo: Tuần {w_data['week_num']} - {w_data['date_range']}", space_after=60))
    body.append(make_para("Người Lập Báo Cáo: Vũ Toàn Thắng (Project Manager)", space_after=60))
    body.append(make_para("Gửi Đến: ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)", space_after=60))
    body.append(make_para(f"Ngày Gửi: {w_data['send_date']}", space_after=240))
    
    # 3. Section 1: Executive Summary
    body.append(make_para("1. EXECUTIVE SUMMARY", style="Heading2", bold=True, space_after=120, space_before=180))
    body.append(make_para('Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status).', space_after=120))
    
    t1 = make_table("Table1", [2200, 1600, 5560], ["Hạng mục", "Trạng thái", "Diễn giải ngắn gọn"], w_data["summary"])
    body.append(t1)
    
    body.append(make_para("Chú thích:", bold=True, space_after=60, space_before=120))
    body.append(make_para("🟢 Green (Xanh): Ổn định, không có vấn đề lớn.", space_after=40))
    body.append(make_para("🟡 Amber (Vàng): Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý.", space_after=40))
    body.append(make_para("🔴 Red (Đỏ): Vấn đề nghiêm trọng, cần sự can thiệp ngay lập tức từ cấp trên.", space_after=240))
    
    # 4. Section 2: Accomplishments
    body.append(make_para("2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)", style="Heading2", bold=True, space_after=120, space_before=180))
    body.append(make_para("Liệt kê các công việc đã làm được trong tuần qua so với kế hoạch ban đầu.", space_after=120))
    
    t2 = make_table("Table2", [800, 3100, 1900, 1560, 2000], ["ID", "Công việc / Hạng mục", "Người phụ trách", "Kết quả", "Ghi chú"], w_data["accomplishments"])
    body.append(t2)
    body.append(make_para("", space_after=120))
    
    # 5. Section 3: Planned Activities
    body.append(make_para("3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)", style="Heading2", bold=True, space_after=120, space_before=180))
    body.append(make_para("Danh sách các công việc dự kiến làm trong tuần tiếp theo, bao gồm cả các thay đổi về nguồn lực hoặc lịch trình nếu có.", space_after=120))
    
    t3 = make_table("Table3", [800, 3960, 2000, 1300, 1300], ["ID", "Công việc dự kiến", "Người phụ trách", "Deadline", "Mức độ ưu tiên"], w_data["planned"])
    body.append(t3)
    body.append(make_para("", space_after=120))
    
    # 6. Section 4: Issues & Risks
    body.append(make_para("4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)", style="Heading2", bold=True, space_after=120, space_before=180))
    body.append(make_para("Phần quan trọng nhất để báo cáo các vấn đề mở (Open Issues) và kế hoạch hành động.", space_after=120))
    
    t4 = make_table("Table4", [900, 2760, 1300, 2500, 1100, 800], ["Loại (Type)", "Mô tả vấn đề / Rủi ro", "Mức độ tác động", "Kế hoạch giải quyết (Action Plan)", "Người xử lý", "Trạng thái"], w_data["risks"])
    body.append(t4)
    body.append(make_para("", space_after=120))
    
    # 7. Section 5: Upcoming Milestones
    body.append(make_para("5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)", style="Heading2", bold=True, space_after=120, space_before=180))
    body.append(make_para("Theo dõi các mốc bàn giao chính (Deliverables) để đảm bảo không bị trượt deadline tổng.", italic=True, space_after=120))
    
    t5 = make_table("Table5", [4360, 1800, 1800, 1400], ["Mốc sự kiện (Milestone)", "Ngày theo kế hoạch", "Ngày dự kiến thực tế", "Trạng thái"], w_data["milestones"])
    body.append(t5)
    body.append(make_para("", space_after=240))
    
    # 8. SectPr
    sectPr = ET.SubElement(body, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr")
    ET.SubElement(sectPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgSz", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w": "12240",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}h": "15840",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}orient": "portrait"
    })
    ET.SubElement(sectPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgMar", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}top": "1440",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bottom": "1440",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}left": "1440",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}right": "1440",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}header": "0",
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}footer": "720"
    })
    ET.SubElement(sectPr, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgNumType", {
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}start": "1"
    })
    
    return ET.tostring(doc, encoding="utf-8", xml_declaration=True)

# Generate the 4 .docx files
for w_data in WEEKS_DATA:
    out_filename = f"docs_ute/PROJECT STATUS REPORT - Week {w_data['week_str']}.docx"
    doc_bytes = build_document_xml(w_data)
    
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as z_in:
        with zipfile.ZipFile(out_filename, "w", zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                if item.filename == "word/document.xml":
                    z_out.writestr(item, doc_bytes)
                else:
                    z_out.writestr(item, z_in.read(item.filename))
                    
    print(f"Generated: {out_filename} ({os.path.getsize(out_filename)} bytes)")

print("All 4 reports generated successfully.")
