# PROJECT STATUS REPORT
## (BÁO CÁO TÌNH TRẠNG DỰ ÁN)

**Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Kỳ Báo Cáo:** Tuần 9 - Từ ngày 23/10/2026 đến ngày 29/10/2026  
**Người Lập Báo Cáo:** Vũ Toàn Thắng (23110329) & Phan Đình Duẩn (23110192)  
**Gửi Đến:** ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)  
**Ngày Gửi:** 30/10/2026  

---

### 1. EXECUTIVE SUMMARY (TỔNG QUAN ĐIỀU HÀNH)

Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status).

| Hạng mục | Trạng thái | Diễn giải ngắn gọn |
| :--- | :---: | :--- |
| **Tiến độ (Schedule)** | <span style="color:#2e7d32">●</span> **Green** | Đạt mục tiêu của Sprint 2 theo đúng kế hoạch đề ra đến ngày 29/10/2026. Đã hoàn thành việc kết nối mô hình AI để sinh đề xuất lộ trình học tập, xây dựng giao diện xem trước và chỉnh sửa kế hoạch cho người học, đồng thời chuẩn bị xong khung giao diện cho Không gian học tập của Sprint tiếp theo. |
| **Phạm vi (Scope)** | <span style="color:#2e7d32">●</span> **Green** | Bám sát các yêu cầu chức năng về sinh kế hoạch học tập thích ứng (FR-AI-PLAN) và kiểm duyệt kế hoạch (FR-AI-APPROVAL). Đảm bảo nguyên tắc người học luôn có quyền kiểm soát: lộ trình do AI đề xuất chỉ là bản nháp, người học có thể tùy chỉnh trước khi chính thức áp dụng vào lịch cá nhân. Không phát sinh thay đổi phạm vi ngoài kế hoạch. |
| **Chất lượng (Quality)** | <span style="color:#2e7d32">●</span> **Green** | Kiểm thử thử nghiệm chức năng sinh kế hoạch trên các kịch bản học tập mẫu cho kết quả tốt: các bài học được phân bổ hợp lý vào thời gian rảnh đã thiết lập; giao diện phản hồi mượt mà và trực quan; dữ liệu hiển thị rõ ràng, dễ theo dõi. |
| **Rủi ro (Risk)** | <span style="color:#2e7d32">●</span> **Green** | Các vấn đề về thời gian chờ khi AI xử lý đã có phương án hiển thị tiến trình theo thời gian thực; cơ chế kiểm tra dữ liệu đầu ra giúp hạn chế tối đa sai lệch thông tin; tính ổn định của đồng hồ học tập khi chuyển tab làm việc đã được kiểm chứng. |

**Chú thích:**
- <span style="color:#2e7d32">●</span> **Green (Xanh):** Ổn định, đúng tiến độ, không có vấn đề lớn cản trở.
- <span style="color:#f57c00">●</span> **Amber (Vàng):** Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý theo dõi.
- <span style="color:#c62828">●</span> **Red (Đỏ):** Vấn đề nghiêm trọng, trượt hạn hoặc có lỗi chặn cần sự can thiệp ngay lập tức từ cấp trên.

---

### 2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)

Bám sát các mục tiêu đã đề ra tại Mục 3 của Báo cáo Tuần 8 thuộc **Phase Three: Lập trình chức năng cốt lõi MVP & Tích hợp AI (Sprint 2 - AI Roadmap Generation & Approval Flow)**:

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú |
| :---: | :--- | :---: | :---: | :--- |
| **6.1** | Tích hợp dịch vụ AI sinh kế hoạch học tập & Bộ kiểm tra cấu trúc dữ liệu (FR-AI-PLAN) | Vũ Toàn Thắng | Hoàn thành | Kết nối thành công dịch vụ AI để tiếp nhận yêu cầu tự học; xây dựng bộ kiểm tra dữ liệu đầu ra nhằm đảm bảo thông tin trả về luôn đúng định dạng cấu trúc, đầy đủ tên bài học, mục tiêu và thời lượng dự kiến. |
| **6.2** | Xây dựng luồng sinh lộ trình thích ứng theo giai đoạn và nhiệm vụ học tập (FR-AI-PLAN) | Vũ Toàn Thắng | Hoàn thành | Hoàn thiện luồng sinh lộ trình học tập theo 2 cấp độ: chia lộ trình thành các chặng lớn (Milestones) theo tuần và phân rã chi tiết thành từng nhiệm vụ học tập cụ thể theo ngày; phân bổ thời lượng học phù hợp với khung thời gian rảnh của người học. |
| **6.3** | Phát triển giao diện Xem trước, Kiểm duyệt và Chỉnh sửa đề xuất lộ trình học tập (FR-AI-APPROVAL) | Vũ Toàn Thắng & Phan Đình Duẩn | Hoàn thành | Xây dựng màn hình hiển thị trực quan bản nháp lộ trình học; cho phép người học xem chi tiết từng bài học, chỉnh sửa tên nhiệm vụ, thay đổi thời lượng, sắp xếp lại thứ tự hoặc xóa bớt nội dung trước khi bấm xác nhận lưu vào lịch học chính thức. |
| **7.1** | Khởi động phát triển Không gian học tập & Bộ công cụ hỗ trợ phiên học (FR-EXEC) | Phan Đình Duẩn | Hoàn thành | Thiết kế và dựng khung giao diện Không gian học tập tập trung (Study Workspace); tích hợp đồng hồ đếm ngược phiên học theo phương pháp Pomodoro kết hợp âm thanh hỗ trợ tập trung (tiếng mưa, tiếng ồn trắng). |
| **6.0** | Tổ chức thử nghiệm và đánh giá chất lượng lộ trình AI sinh ra trên các kịch bản người học mẫu | Vũ Toàn Thắng | Hoàn thành | Thử nghiệm tính năng sinh lộ trình trên 5 kịch bản tự học phổ biến (như học lập trình cơ bản, ôn luyện chứng chỉ, học kỹ năng bổ trợ); kết quả các bài học được gợi ý bám sát mục tiêu và phân bổ thời gian hợp lý. |

---

### 3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)

Danh sách các công việc dự kiến triển khai trong tuần tiếp theo (Tuần 10: từ 30/10/2026 đến 05/11/2026) — Bước vào **Sprint 3: Không gian thực thi phiên học & Cơ chế thích ứng tự động**:

| ID | Công việc dự kiến | Người phụ trách | Deadline | Mức độ ưu tiên |
| :---: | :--- | :---: | :---: | :---: |
| **7.1** | Hoàn thiện bộ công cụ hỗ trợ trong Không gian học tập (danh sách đầu việc cần làm trong buổi, khung ghi chú nhanh cho bài học) | Phan Đình Duẩn | 02/11/2026 | High |
| **7.2** | Xây dựng tính năng xử lý gián đoạn phiên học (cho phép tạm dừng buổi học khi có việc bận và tự động lưu lại các bài học chưa hoàn thành) | Phan Đình Duẩn | 04/11/2026 | High |
| **7.3** | Xây dựng cơ chế tự động phát hiện và nhắc nhở/gợi ý dời lịch cho các nhiệm vụ học tập bị quá hạn (FR-OVERDUE) | Vũ Toàn Thắng | 04/11/2026 | High |
| **7.4** | Phát triển tính năng Tạm dừng lộ trình học (Pause Roadmap) và hỗ trợ dời tịnh tiến các bài học tiếp theo khi người dùng nghỉ dài ngày | Vũ Toàn Thắng | 05/11/2026 | High |
| **7.5** | Nghiên cứu và xây dựng tính năng liên kết lịch học sang ứng dụng lịch cá nhân bên ngoài (Google Calendar, Apple Calendar) | Phan Đình Duẩn | 05/11/2026 | Medium |

---

### 4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)

Theo dõi các vấn đề và rủi ro thực tế trong quá trình phát triển tính năng và trải nghiệm người dùng:

| Loại (Type) | Mô tả vấn đề / Rủi ro | Mức độ tác động | Kế hoạch giải quyết (Action Plan) | Người xử lý | Trạng thái |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Issue** | Quá trình AI suy nghĩ và sinh ra một lộ trình học tập hoàn chỉnh cần một khoảng thời gian chờ nhất định, có thể gây cảm giác chậm chạp cho người dùng. | Trung bình | Áp dụng cơ chế hiển thị tiến trình theo thời gian thực: hiển thị ngay các chặng học tổng quan trước để người học nắm bắt, sau đó lần lượt tải chi tiết từng nhiệm vụ bài học kết hợp hiệu ứng thông báo trạng thái rõ ràng. | Vũ Toàn Thắng | Closed |
| **Issue** | AI có thể phản hồi thiếu trường thông tin hoặc diễn đạt thời lượng học chưa đúng định dạng mong muốn để hiển thị lên giao diện. | Trung bình | Xây dựng bộ lọc kiểm tra dữ liệu trước khi hiển thị; nếu phát hiện dữ liệu chưa đạt yêu cầu, hệ thống sẽ tự động yêu cầu tạo lại nội dung phù hợp nhằm đảm bảo giao diện luôn nhận được thông tin chuẩn xác. | Vũ Toàn Thắng | Closed |
| **Risk** | Khi người học chuyển sang tab khác để tra cứu tài liệu, đồng hồ đếm ngược phiên học có thể bị gián đoạn hoặc đếm chậm nhịp do trình duyệt tự động hạn chế ứng dụng nền. | Thấp | Tách cơ chế đếm giờ chạy độc lập ở chế độ nền dựa trên thời gian thực tế của hệ thống thay vì phụ thuộc vào chu kỳ làm mới giao diện, đảm bảo thời gian đếm ngược luôn chính xác khi mở lại. | Phan Đình Duẩn | Closed |
| **Risk** | Trường hợp người dùng bị mất kết nối mạng trong quá trình đang tải dở lộ trình học tập, dẫn đến việc phải thực hiện lại từ đầu. | Thấp | Nghiên cứu giải pháp tự động lưu lại các phần lộ trình đã nhận thành công vào bộ nhớ tạm của phiên làm việc để người dùng có thể tiếp tục xem hoặc phục hồi mà không phải tạo mới. | Vũ Toàn Thắng | Open |

---

### 5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)

Theo dõi các mốc bàn giao chính (Deliverables) đối chiếu với tiến độ kế hoạch tổng thể:

| Mốc sự kiện (Milestone) | Ngày theo kế hoạch | Ngày hoàn thành thực tế / Dự kiến | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)** | 08/10/2026 | 08/10/2026 | Completed |
| **Hoàn thành Sprint 1: Nền tảng hệ thống, Xác thực & Cấu hình Thời gian rảnh (Milestone 2.5)** | 22/10/2026 | 22/10/2026 | Completed |
| **Hoàn thành Sprint 2: Lập kế hoạch AI & Cổng phê duyệt lộ trình thích ứng** | 29/10/2026 | 29/10/2026 | Completed |
| **Hoàn thành Sprint 3: Không gian thực thi phiên học & Cơ chế thích ứng tự động** | 05/11/2026 | 05/11/2026 | On-track |
| **Hoàn thiện Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3)** | 12/11/2026 | 12/11/2026 | On-track |
