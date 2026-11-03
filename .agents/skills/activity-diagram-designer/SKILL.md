---
name: activity-diagram-designer
description: Thiết kế UML 2.5.1 activity diagram (sơ đồ hoạt động) và đặc tả hoạt động chuẩn xác theo góc nhìn Senior Business Analyst / System Analyst, bám chuẩn OMG UML 2.5.1 (Clause 15) và đối chiếu BPMN 2.0.2. Dùng khi người dùng nhắc đến activity diagram, sơ đồ hoạt động, luồng nghiệp vụ, quy trình, workflow, swimlane, fork / join, decision / merge, luồng song song, luồng xử lý, thuật toán, timeout, ngoại lệ, hoặc muốn chuyển use case / yêu cầu / mô tả quy trình thành sơ đồ, kể cả khi không nói rõ chữ activity diagram. Also for process modeling, flowchart to UML, token semantics, PlantUML activity, BPMN vs UML activity.
---

# Activity Diagram Designer

Thiết kế **UML activity diagram** đúng ký hiệu **và đúng ngữ nghĩa** (token flow), kèm bảng đặc tả để dev, tester, BA và khách hàng cùng hiểu một cách. Làm như một senior analyst: chọn đúng loại sơ đồ trước, mô hình hóa ở một mức trừu tượng nhất quán, kiểm chứng bằng mô phỏng token (không chỉ "nhìn thấy hợp lý"), và dẫn chiếu chuẩn khi cần.

Chuẩn tham chiếu: **OMG UML 2.5.1, Clause 15 (Activities)**, đối chiếu **BPMN 2.0.2** cho quy trình nghiệp vụ. Liên kết, phiên bản đã xác minh và cách trích dẫn: `references/standards-and-links.md`. Khi cần khẳng định "bản mới nhất" mà có công cụ web, mở https://www.omg.org/spec/UML để xác nhận lại.

Ngôn ngữ đầu ra: theo người dùng (mặc định tiếng Việt), giữ thuật ngữ UML tiếng Anh trong ngoặc khi cần (Decision, Merge, Fork, Join, Activity Final, Flow Final).

## Nguyên tắc cốt lõi (kèm lý do)

1. **Activity diagram mô tả luồng điều khiển và luồng dữ liệu dựa trên token**, không phải flowchart tô điểm. Ngữ nghĩa quyết định đúng sai: một hành động chỉ chạy khi **mọi cạnh vào** đều có token (cạnh vào nhiều → ngầm là AND-join). Vì vậy kiểm chứng phải dựa vào mô phỏng token.
2. **Chọn đúng loại sơ đồ.** Activity diagram cho *hành vi/luồng xử lý*; sequence diagram cho *tương tác theo thời gian giữa các đối tượng*; state machine cho *vòng đời một đối tượng*; BPMN cho *quy trình nghiệp vụ nhiều bên có thông điệp, sự kiện, có thể thực thi bằng workflow engine*. Dùng sai loại là lỗi gốc của nhiều sơ đồ khó đọc.
3. **Một sơ đồ một mức trừu tượng.** Trộn "Khách bấm nút" với "Hệ thống phát sự kiện OrderPlaced" trong cùng một hàng làm sơ đồ mơ hồ. Phân rã bằng call behavior action thay vì kéo dài.
4. **Mọi đường đều phải kết thúc đúng cách và mọi rẽ nhánh đều phải đầy đủ.** Decision phải có nhánh bao phủ mọi trường hợp (`[else]`); vòng lặp phải có điều kiện thoát; hành động chờ ngoài (thanh toán, duyệt) phải có đường timeout/ngoại lệ.
5. **Không bịa quy tắc nghiệp vụ.** Điều kiện, ngưỡng, thời gian chưa biết thì ghi vào "câu hỏi mở", không tự đặt số.
6. **Nói rõ giới hạn công cụ.** PlantUML/Mermaid không vẽ được mọi ký hiệu UML (pin, interruptible region, exception handler...). Mô hình đúng chuẩn trước, xấp xỉ trên diagram sau, ghi chú phần xấp xỉ.

## Chọn đúng loại sơ đồ

| Câu hỏi của người dùng | Dùng |
|---|---|
| "Các bước xử lý một yêu cầu, có rẽ nhánh và song song" | **Activity diagram** |
| "Các thành phần/đối tượng gọi nhau theo thứ tự nào" | Sequence diagram |
| "Đối tượng X có những trạng thái nào, chuyển ra sao" | State machine (skill `state-machine-designer`) |
| "Quy trình nhiều tổ chức/bộ phận, thông điệp qua lại, cần chạy trên workflow engine, có người dùng tác vụ, sự kiện thời gian, bồi hoàn" | **BPMN** (activity diagram vẫn dùng được ở mức khái niệm) |
| "Thuật toán, lưu đồ logic một hàm" | Activity diagram (mức thấp) hoặc flowchart đơn giản |
| "Luồng dữ liệu giữa các kho/quá trình" | Data flow diagram (không thuộc UML) |

Nếu yêu cầu thật sự là BPMN, nói rõ và đưa mô hình BPMN (bảng ánh xạ ở `references/notation.md` §10), đừng ép vào UML.

## Quy trình

### 1. Xác định phạm vi và góc nhìn (hỏi gộp, tối đa 4–5 câu)
Quy trình/hoạt động nào, **bắt đầu bởi sự kiện gì, kết thúc ở kết quả nào**; ai tham gia (người, hệ thống, hệ thống ngoài) để chia swimlane; mức chi tiết (nghiệp vụ, hệ thống, thuật toán); có yếu tố thời gian, song song, lỗi/hủy quan trọng không; có use case spec hoặc SRS không. Đã có tài liệu: **đọc hết trước khi hỏi**. Không hỏi được thì ghi giả định và tiếp tục.

### 2. Thu thập luồng
Từ use case spec: luồng chính → trục chính; luồng thay thế → decision; luồng ngoại lệ → nhánh lỗi/timeout; tiền điều kiện → điều kiện vào; hậu điều kiện → kết quả; quy tắc nghiệp vụ → guard. Liệt kê: hành động, quyết định, điểm song song, sự kiện chờ (accept event), sự kiện thời gian, đối tượng dữ liệu trao đổi, hành động gọi hoạt động khác.

### 3. Chọn mức trừu tượng và phân rã
Mục tiêu 5–15 nút hành động trên một sơ đồ. Hơn thế thì tách thành hoạt động con (call behavior action, ký hiệu rake) hoặc nhiều sơ đồ theo giai đoạn. Tên hành động: **động từ + đối tượng**, ở dạng nhất quán.

### 4. Dựng cấu trúc token
Chọn nút: initial, action, decision/merge, fork/join, final (activity final hay flow final), object node, accept/send event. Gán swimlane (partition) cho từng hành động theo **ai thực hiện**. Chi tiết ký hiệu và ngữ nghĩa: `references/notation.md`. Các mẫu luồng (duyệt nhiều cấp, song song có tổng hợp, thử lại, timeout, hủy): `references/modeling-guide.md`.

### 5. Kiểm chứng ngữ nghĩa bằng mô phỏng token
Chạy "token game" cho 2–4 kịch bản (đường thành công, một nhánh rẽ, một ngoại lệ, một đường song song) và các kiểm tra tĩnh trong `references/modeling-guide.md` §5: không deadlock (decision rồi join), không nhân token ngoài ý muốn (fork rồi merge), mọi decision có `[else]`, mọi vòng lặp có lối thoát, mọi hành động có ≥ 1 cạnh ra (trừ kết thúc), mọi nhánh kết thúc đúng loại final.

### 6. Xuất sơ đồ và bảng đặc tả
PlantUML (cú pháp mới) là mặc định; mẫu ở `references/templates.md`. Mermaid flowchart chỉ làm phương án dự phòng. Kèm bảng đặc tả: hành động, decision và guard, swimlane, object, sự kiện/timer, ngoại lệ, tiền/hậu điều kiện. Render thử nếu có công cụ; nếu không, nói rõ mã chưa render.

### 7. Rà soát
Chạy `references/review-checklist.md` rồi mới giao.

## Định dạng đầu ra mặc định

1. **Phạm vi, góc nhìn, giả định** (3–6 dòng) và lý do chọn activity diagram
2. **Sơ đồ** (PlantUML + hình nếu render được)
3. **Bảng đặc tả hoạt động**: danh sách hành động (ID, tên, swimlane, mô tả, đầu vào/ra), decision và guard, đối tượng dữ liệu, sự kiện/timer, ngoại lệ, tiền/hậu điều kiện
4. **Kết quả kiểm chứng token**: 2–4 kịch bản đã mô phỏng, kết luận về deadlock, nhân token, kết thúc
5. **Truy vết**: ánh xạ về use case, quy tắc nghiệp vụ (BR-xx)
6. **Câu hỏi mở và giới hạn công cụ**
7. **Tham chiếu chuẩn** (tên chuẩn, bản, clause; liên kết khi cần)

Yêu cầu nhỏ (một sơ đồ nhanh) thì chỉ giao mục 1–2 và một dòng kiểm chứng token; vẫn phải đúng ngữ nghĩa.

## Kết hợp với các skill khác
Use case spec (`usecase-analyst`) là nguồn chính của luồng. Vòng đời một đối tượng xuất hiện trong luồng (đơn, vé) thì tách sang `state-machine-designer`. Quyết định đồng bộ/bất đồng bộ, saga, workflow engine thuộc `software-architect`. Dữ liệu trao đổi nối với `class-diagram-designer` / `database-designer`.

## Ví dụ ngắn

Input: "Khách đặt vé online: chọn ghế, nếu ghế còn thì giữ 10 phút, thanh toán qua cổng, thành công thì gửi vé và email đồng thời, hết 10 phút mà chưa thanh toán thì nhả ghế."

Cách nghĩ: Swimlane Khách hàng / Hệ thống / Cổng thanh toán. Initial → "Chọn ghế" → Decision [ghế còn?]: [không] → "Thông báo hết ghế" → flow về chọn lại (merge); [còn] → "Giữ ghế 10 phút". Chờ kết quả: **accept event** "Kết quả thanh toán" **song song** với **time event** "sau 10 phút" (cả hai cùng đi vào một decision/merge phù hợp, hoặc dùng interruptible region cho đường timeout). Nhánh thanh toán thành công → **Fork**: "Phát hành vé" và "Gửi email" → **Join** → Activity Final. Nhánh timeout → "Nhả ghế" → Activity Final. Kiểm chứng token: sau Fork phải là Join (không phải Merge) để chỉ kết thúc khi cả hai xong; hai nhánh kết quả thanh toán/timeout loại trừ nhau nên hợp bằng **Merge**, không phải Join (Join sẽ deadlock).
