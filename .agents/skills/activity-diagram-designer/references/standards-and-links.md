# Chuẩn và tài liệu tham chiếu (đã xác minh ngày 25/10/2026)

Mục đích: AI agent dùng các nguồn dưới đây làm **thẩm quyền** khi trả lời về ký hiệu và ngữ nghĩa. Khi có công cụ web, **mở lại trang OMG/W3C để xác nhận phiên bản trước khi khẳng định "mới nhất"**; chuẩn thay đổi chậm nhưng có thể có bản mới sau ngày xác minh.

## 1. Chuẩn chính

| Chuẩn | Phiên bản mới nhất đã xác minh | Mã tài liệu | Liên kết |
|---|---|---|---|
| **OMG UML** (nền tảng của activity và state machine diagram) | **2.5.1** (tháng 12/2017); trang OMG vẫn liệt kê đây là bản formal mới nhất | formal/17-12-05 (bản có đánh dấu thay đổi: formal/17-12-06) | Trang chính: https://www.omg.org/spec/UML/2.5.1 · PDF: https://www.omg.org/spec/UML/2.5.1/PDF · Giới thiệu: https://www.omg.org/spec/UML/About-UML · Bản đọc bằng máy (XMI): https://www.omg.org/spec/UML/machine-readable |
| **ISO/IEC 19505** (UML dạng ISO) | Phần 1 và 2, năm 2012, **tương ứng UML 2.4.1** (ISO chậm hơn OMG) | 19505-1:2012, 19505-2:2012 | Danh mục OMG: https://www.omg.org/spec/About |
| **OMG BPMN** (mô hình quy trình nghiệp vụ, đối chiếu với activity diagram) | **2.0.2** (tháng 1/2014), cũng là ISO/IEC 19510:2013; vẫn là bản mới nhất trên trang OMG | formal/13-12-09 | https://www.omg.org/spec/BPMN/2.0.2 · PDF: https://www.omg.org/spec/BPMN/2.0.2/PDF |
| **OMG PSSM** (ngữ nghĩa thực thi chính xác cho state machine) | **1.0** (tháng 5/2019) | formal/19-05-01 | https://www.omg.org/spec/PSSM/1.0 |
| **OMG fUML / Alf** (UML thực thi được; activity là nền tảng) | fUML **1.4** (đã chuyển sang UML 2.5.1) và Alf 1.1; nên mở trang để xác nhận bản hiện hành | | https://www.omg.org/spec/FUML · https://www.omg.org/spec/ALF |
| **W3C SCXML** (định dạng XML thực thi statechart) | **1.0**, W3C Recommendation (1/9/2015) | | https://www.w3.org/TR/scxml/ |

Số điều khoản (clause) trong UML 2.5.1: **Clause 14 = State Machines**, **Clause 15 = Activities** (đã đối chiếu qua các điều khoản trích dẫn 14.2.3.x về trạng thái và 15.3.2 về control nodes). Các clause khác (Actions, Common Behavior...) có số khác bản 2.1/2.4 nên **xem mục lục của PDF 2.5.1** thay vì nhớ số.

## 2. Tài liệu học thuật và sách tham chiếu

- David Harel, *Statecharts: A visual formalism for complex systems*, Science of Computer Programming 8(3), 1987: nguồn gốc statechart, nền của UML state machine (UML 2.5.1 nêu rõ dạng state machine của UML dựa trên biến thể hướng đối tượng của statecharts, với một số khác biệt ngữ nghĩa nhỏ).
- Rumbaugh, Jacobson, Booch, *The Unified Modeling Language Reference Manual*, 2nd ed.: từ điển khái niệm UML 2, dễ đọc hơn đặc tả.
- Martin Fowler, *UML Distilled* (3rd ed.): ngắn gọn, thực dụng.
- Miro Samek, *Practical UML Statecharts in C/C++* (2nd ed.): cài đặt state machine phân cấp.
- Workflow Patterns Initiative (van der Aalst, ter Hofstede và cộng sự), http://www.workflowpatterns.com : danh mục mẫu luồng điều khiển (rẽ nhánh, song song, đồng bộ, hủy) dùng để kiểm tra ngữ nghĩa của activity diagram. Trang này chưa được mở trong phiên xác minh.
- statecharts.dev (tài liệu cộng đồng về statechart): https://statecharts.dev . Chưa được mở trong phiên xác minh.

## 3. Tài liệu công cụ vẽ

| Công cụ | Trang tài liệu | Ghi chú đã xác minh |
|---|---|---|
| PlantUML activity (cú pháp mới) | https://plantuml.com/activity-diagram-beta | Đã đọc trực tiếp. Cú pháp cũ (https://plantuml.com/activity-diagram-legacy) vẫn chạy nhưng **không khuyến nghị** cho sơ đồ mới. Hỗ trợ `start/stop/end`, `if/elseif/else`, `switch`, `while`, `repeat`, `fork`/`end fork` (join) và `end merge`, `split`, swimlane `\|Tên\|`, partition/group, note, stereotype UML (`<<object>>`, `<<acceptEvent>>`, `<<sendSignal>>`, `<<timeEvent>>`...), `kill`/`detach`, nhãn joinspec `{and}`/`{or}` |
| PlantUML state | https://plantuml.com/state-diagram | Đã đọc trực tiếp. Hỗ trợ state đơn/phức (composite), vùng đồng thời `--` và `\|\|`, `<<choice>>`, `<<fork>>`, `<<join>>`, `[H]` và `[H*]` (history, deep history), `<<entryPoint>>`/`<<exitPoint>>`, note, alias |
| Mermaid state | https://mermaid.js.org/syntax/stateDiagram.html | Cú pháp `stateDiagram-v2` đã đối chiếu qua nhiều nguồn thứ cấp (trang gốc chưa mở được trong phiên xác minh). Có state phức, `<<choice>>`, `<<fork>>`/`<<join>>`, đồng thời `--`, note. Không thể vẽ chuyển tiếp giữa các trạng thái con thuộc hai composite khác nhau |
| Mermaid flowchart | https://mermaid.js.org/syntax/flowchart.html | Chưa mở trực tiếp; dùng làm phương án dự phòng cho activity diagram (không có ký hiệu fork/join chuẩn) |

## 4. Cách dùng nguồn trong câu trả lời

1. **Phân biệt ba lớp thông tin**: (a) điều chuẩn quy định (trích điều khoản), (b) quy ước thực hành tốt của ngành, (c) giới hạn của công cụ vẽ. Nói rõ đang ở lớp nào.
2. **Dẫn nguồn ngắn gọn**: nêu tên chuẩn, bản và clause ("UML 2.5.1, Clause 15, control nodes"), kèm liên kết khi người dùng cần kiểm chứng.
3. **Không chép nguyên văn dài** từ đặc tả (tài liệu có bản quyền OMG); diễn đạt lại bằng lời của mình, trích tối đa một cụm ngắn khi thật cần.
4. **Khi tra cứu**: mở trang chính trước (https://www.omg.org/spec/UML), xác nhận bản hiện hành, rồi mới mở PDF. PDF rất dài: đọc theo mục lục, không đọc toàn bộ.
5. **Khi không tra được**: dùng kiến thức trong skill này, nêu rõ "dựa trên UML 2.5.1, chưa đối chiếu lại nguồn trong phiên này".
6. **Xung đột**: nếu công cụ vẽ không biểu diễn được một yếu tố chuẩn (ví dụ interruptible region trong PlantUML), vẫn mô hình hóa đúng chuẩn ở phần mô tả bằng chữ, chọn cách xấp xỉ gần nhất trên diagram, và ghi chú giới hạn.
