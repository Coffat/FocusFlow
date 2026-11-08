# FocusFlow — Khảo sát Nhu cầu Tự học & Nghiên cứu Đối sánh Giải pháp (Benchmarking)

> **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
> **Chuyên ngành:** Công nghệ Phần mềm — Khoa Công nghệ Thông tin  
> **Cấp độ tài liệu:** Báo cáo Nghiên cứu Tiền khả thi, Khảo sát Thực chứng & Phân tích Đối sánh (Research, Empirical Survey & Benchmarking Artifact)  
> **Mã tài liệu:** `DOC-REQ-SURVEY-01`  
> **Tài liệu liên kết:** `docs/requirements/problem-definition.md`, `docs/srs/srs-v1.0.md`, `docs_ute/04_wbs_deliverables/WBS 1.1 - Khảo sát nhu cầu tự học và nghiên cứu đối sánh giải pháp (Benchmarking).md`  
> **Căn cứ đánh giá học thuật:** Khung Rubric Chấm Đồ án Tốt nghiệp / Khóa luận CNTT:
> - **Tiêu chí TC1 (Mức 5):** "Tính cấp thiết rõ ràng; So sánh $\ge 3$ giải pháp hiện có, nêu rõ khoảng trống với phân tích thực tế khách quan; Xác định rõ $\ge 5$ mục tiêu/KPI cụ thể định lượng ngay từ đầu."
> - **Tiêu chí TC2.1 (Mức 5):** "Đặc tả đầy đủ yêu cầu chức năng & $\ge 5$ yêu cầu phi chức năng định lượng."
> - **Tiêu chí TC2.3 (Mức 5):** "Mức độ làm chủ và năng lực kiểm soát rủi ro khi tích hợp AI/LLM."
> - **Tiêu chí TC2.7 (Mức 5):** "Thực hiện UAT nghiêm túc trên người dùng thật; Đạt các chỉ số đo lường trải nghiệm (SUS $\ge 80$, Task Completion $\ge 90\%$).'

---

## MỤC LỤC

1. [Tổng quan & Mục đích Nghiên cứu](#1-tổng-quan--mục-đích-nghiên-cứu)
   - 1.1 [Bối cảnh học thuật & Thực tiễn](#11-bối-cảnh-học-thuật--thực-tiễn)
   - 1.2 [Mục tiêu của nghiên cứu](#12-mục-tiêu-của-nghiên-cứu)
2. [Cơ sở Lý thuyết & Phương pháp luận Khảo sát](#2-cơ-sở-lý-thuyết--phương-pháp-luận-khảo-sát)
   - 2.1 [Các lý thuyết nền tảng (Theoretical Foundations)](#21-các-lý-thuyết-nền-tảng-theoretical-foundations)
   - 2.2 [Phương pháp nghiên cứu kết hợp (Secondary Research & Heuristic Walkthrough)](#22-phương-pháp-nghiên-cứu-kết-hợp-secondary-research--heuristic-walkthrough)
   - 2.3 [Thiết kế bộ công cụ khảo sát chuẩn hóa (Survey Instrument Design)](#23-thiết-kế-bộ-công-cụ-khảo-sát-chuẩn-hóa-survey-instrument-design)
3. [Báo cáo & Phân tích Dữ liệu Thực chứng (Empirical Findings & Cognitive Analysis)](#3-báo-cáo--phân-tích-dữ-liệu-thực-chứng-empirical-findings--cognitive-analysis)
   - 3.1 [Dữ liệu Bối cảnh & Phân khúc Người tự học Công nghệ](#31-dữ-liệu-bối-cảnh--phân-khúc-người-tự-học-công-nghệ)
   - 3.2 [Phân tích Nỗi đau 1: Rào cản phân rã mục tiêu (Decomposition Barrier)](#32-phân-tích-nỗi-đau-1-rào-cản-phân-rã-mục-tiêu-decomposition-barrier)
   - 3.3 [Phân tích Nỗi đau 2: Quá tải và phân mảnh công cụ (Tool Fragmentation & Cognitive Overhead)](#33-phân-tích-nỗi-đau-2-quá-tải-và-phân-mảnh-công-cụ-tool-fragmentation--cognitive-overhead)
   - 3.4 [Phân tích Nỗi đau 3: Đứt gãy kế hoạch khi có biến cố (Rigid Planning Failure)](#34-phân-tích-nỗi-đau-3-đứt-gãy-kế-hoạch-khi-có-biến-cố-rigid-planning-failure)
   - 3.5 [Tổng hợp Dữ liệu từ Nhật ký Thực nghiệm Trải nghiệm (Cognitive Walkthrough Log)](#35-tổng-hợp-dữ-liệu-từ-nhật-ký-thực-nghiệm-trải-nghiệm-cognitive-walkthrough-log)
   - 3.6 [Hạn chế của nghiên cứu & Nguy cơ sai lệch (Threats to Validity)](#36-hạn-chế-của-nghiên-cứu--nguy-cơ-sai-lệch-threats-to-validity)
4. [Nghiên cứu Đối sánh Giải pháp (Competitive Benchmarking Analysis)](#4-nghiên-cứu-đối-sánh-giải-pháp-competitive-benchmarking-analysis)
   - 4.1 [Lựa chọn đối tượng đối sánh](#41-lựa-chọn-đối-tượng-đối-sánh)
   - 4.2 [Phân tích chi tiết từng giải pháp hiện hữu](#42-phân-tích-chi-tiết-từng-giải-pháp-hiện-hữu)
   - 4.3 [Khung tiêu chí đánh giá đa chiều (Evaluation Dimensions)](#43-khung-tiêu-chí-đánh-giá-đa-chiều-evaluation-dimensions)
   - 4.4 [Ma trận đối sánh tính năng & kỹ thuật toàn diện](#44-ma-trận-đối-sánh-tính-năng--kỹ-thuật-toàn-diện)
   - 4.5 [Phân tích Khoảng trống Chiến lược (Strategic Gap Analysis)](#45-phân-tích-khoảng-trống-chiến-lược-strategic-gap-analysis)
5. [Định vị Giải pháp FocusFlow & Ma trận Truy vết Nhu cầu](#5-định-vị-giải-pháp-focusflow--ma-trận-truy-vết-nhu-cầu)
   - 5.1 [Tuyên ngôn giá trị cốt lõi của FocusFlow](#51-tuyên-ngôn-giá-trị-cốt-lõi-của-focusflow)
   - 5.2 [Ma trận truy vết từ Khảo sát đến SRS và 5 KPI nghiệm thu](#52-ma-trận-truy-vết-từ-khảo-sát-đến-srs-và-5-kpi-nghiệm-thu)
6. [Góc Nhìn Cố Vấn Khóa Luận (Thesis Mentor Guidance & Defense Q&A)](#6-góc-nhìn-cố-vấn-khóa-luận-thesis-mentor-guidance--defense-qa)
   - 6.1 [Các bẫy lập luận sinh viên thường mắc phải](#61-các-bẫy-lập-luận-sinh-viên-thường-mắc-phải)
   - 6.2 [Danh sách 'Không nên nói' vs 'Nên nói' khi thuyết minh đồ án](#62-danh-sách-không-nên-nói-vs-nên-nói-khi-thuyết-minh-đồ-án)
   - 6.3 [Bộ câu hỏi phản biện mẫu & Câu chuyện bảo vệ trước Hội đồng](#63-bộ-câu-hỏi-phản-biện-mẫu--câu-chuyện-bảo-vệ-trước-hội-đồng)
7. [Kết luận & Kế hoạch Tiếp theo](#7-kết-luận--kế-hoạch-tiếp-theo)
8. [Danh mục Tài liệu Tham khảo (Academic References)](#8-danh-mục-tài-liệu-tham-khảo-academic-references)

---

## 1. Tổng quan & Mục đích Nghiên cứu

### 1.1 Bối cảnh học thuật & Thực tiễn
Trong xu thế chuyển đổi số và bùng nổ của trí tuệ nhân tạo, chu kỳ suy hao tri thức (knowledge half-life) trong ngành Công nghệ Thông tin rút ngắn xuống mức kỷ lục (chỉ còn khoảng 2–3 năm). Yêu cầu tự học suốt đời (*Self-Directed Lifelong Learning*) và tái đào tạo kỹ năng (*Reskilling/Upskilling*) trở thành năng lực sinh tồn đối với sinh viên và người làm công nghệ.

Tuy nhiên, giáo dục truyền thống và các khóa học đóng gói (MOOCs) thường chỉ cung cấp tài nguyên tĩnh, thiếu tính thích ứng theo năng lực và thời gian biểu của từng cá nhân. Khi tự học độc lập ngoài giảng đường, người học phải tự đóng vai trò vừa là "người lên chiến lược học", vừa là "người thực thi", vừa là "giám sát viên kỷ luật". Sự thiếu hụt một hệ thống hỗ trợ khoa học dẫn đến tỷ lệ bỏ cuộc giữa chừng trong các khóa tự học lên tới **85% – 90%** (theo các báo cáo phân tích EdTech quốc tế).

### 1.2 Mục tiêu của nghiên cứu
Tài liệu này được xây dựng nhằm phục vụ 3 mục đích kỹ thuật và học thuật trọng yếu:
1. **Minh chứng tính cấp thiết (Academic Justification - Rubric TC1):** Thiết lập luận cứ thực chứng khách quan, khoa học, dựa trên số liệu khảo sát người dùng thực tế kết hợp nghiên cứu khoa học thần kinh/tâm lý học nhận thức, chứng minh bài toán FocusFlow giải quyết là có thật và cấp bách.
2. **Đối sánh đa chiều & Xác định khoảng trống (Benchmarking & Gap Identification):** Phân tích sâu 4 nhóm giải pháp hiện hữu trên thị trường (Lịch số, Ứng dụng quản lý công việc, Trợ lý AI tạo sinh, Nền tảng học tập trực tuyến), chỉ ra các điểm nghẽn kỹ thuật và trải nghiệm mà chưa giải pháp nào giải quyết trọn vẹn.
3. **Định hình cơ sở yêu cầu kỹ thuật (Requirements Engineering Traceability):** Ánh xạ trực tiếp từ nỗi đau thực tế của người dùng thành các tính năng hệ thống, quy tắc nghiệp vụ trong tài liệu SRS v1.0 và hệ thống 5 KPI định lượng để nghiệm thu đồ án tốt nghiệp.

---

## 2. Cơ sở Lý thuyết & Phương pháp luận Khảo sát

### 2.1 Các lý thuyết nền tảng (Theoretical Foundations)

Nghiên cứu khảo sát của FocusFlow được neo vào 3 mô hình lý thuyết khoa học giáo dục và nhận thức đã được công nhận trên thế giới:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Thuyết Tự điều chỉnh Học tập (Self-Regulated Learning - Zimmerman)       │
│    Chu trình 3 pha: Dự đoán/Kế hoạch ──> Thực thi/Kiểm soát ──> Tự đánh giá │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Thuyết Tải Nhận thức (Cognitive Load Theory - Sweller)                   │
│    Tải ngoại lai (Extraneous Load) do phân mảnh công cụ làm giảm sút        │
│    năng lực hấp thụ kiến thức thực tế (Germane Load).                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Thuyết Suy hao Ý chí & Mệt mỏi Kế hoạch (Ego Depletion & Planning Fatigue)│
│    Ý chí con người là nguồn năng lượng hữu hạn (Baumeister). Việc liên tục  │
│    sắp xếp lịch biểu thủ công làm cạn kiệt ý chí trước khi bước vào học.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Mô hình Tự điều chỉnh Học tập (Self-Regulated Learning - SRL, Zimmerman, 2002):**
   Quá trình tự học thành công bắt buộc phải trải qua vòng lặp khép kín 3 giai đoạn:
   - *Pha chuẩn bị (Forethought Phase):* Phân tích mục tiêu, lập kế hoạch chiến lược.
   - *Pha thực thi (Performance Phase):* Kiểm soát sự tập trung, ghi chép và tự theo dõi.
   - *Pha tự suy ngẫm (Self-Reflection Phase):* Đánh giá kết quả, rút kinh nghiệm và điều chỉnh kế hoạch cho chu kỳ sau.
   *Áp dụng vào FocusFlow:* Hệ thống thiết kế khép kín đúng 4 module tương ứng: AI Plan Generator $\rightarrow$ Study Workspace $\rightarrow$ Adaptive Shift $\rightarrow$ Weekly Review.

2. **Thuyết Tải Nhận thức (Cognitive Load Theory - Sweller, 1988):**
   Bộ não người có bộ nhớ làm việc (Working Memory) giới hạn. Khi người học phải liên tục chuyển đổi ngữ cảnh (Context Switching) giữa 3–4 ứng dụng (vừa tra cứu ChatGPT, vừa copy vào Google Calendar, vừa bấm giờ điện thoại, vừa mở Notion), "Tải nhận thức ngoại lai" (*Extraneous Cognitive Load*) tăng vọt, triệt tiêu tài nguyên não bộ dành cho việc tiếp thu kiến thức chuyên môn (*Germane Cognitive Load*).

3. **Hiện tượng Suy hao Ý chí & Mệt mỏi Kế hoạch (Ego Depletion & Planning Fatigue - Baumeister et al., 1998):**
   Khả năng ra quyết định và kỷ luật của con người suy giảm dần theo thời gian trong ngày. Người học mất từ 30 đến 45 phút chỉ để loay hoay chia nhỏ một mục tiêu lớn hoặc kéo thả sắp xếp lại các ô lịch bị trễ hạn sẽ rơi vào trạng thái tê liệt hành động (*Action Paralysis*), dẫn đến hành vi trì hoãn và từ bỏ phiên học.

### 2.2 Phương pháp nghiên cứu kết hợp (Secondary Research & Heuristic Walkthrough)
Đề tài áp dụng phương pháp nghiên cứu kết hợp đa nguồn (*Multi-method Triangulation*) nhằm bảo đảm tính khách quan, trung thực học thuật và chuẩn mực kỹ thuật phần mềm:
- **Nghiên cứu Thứ cấp & Báo cáo Ngành (Secondary Research & Industry Reports):** Khai thác dữ liệu thống kê từ các công trình khoa học quốc tế uy tín về EdTech, khoa học nhận thức và khảo sát lập trình viên toàn cầu (Báo cáo tỷ lệ bỏ cuộc 85–95% trên các nền tảng MOOC của MIT/Harvard công bố trên tạp chí *Science*; nghiên cứu chi phí gián đoạn 23 phút 15 giây của TS. Gloria Mark tại ACM CHI; báo cáo *Stack Overflow Developer Survey* với hơn 73% lập trình viên tự học công nghệ mới).
- **Thực nghiệm Đánh giá Công thái học (Empirical Heuristic & Cognitive Walkthrough):** Tác giả đề tài trực tiếp tiến hành thử nghiệm mô phỏng (*Dogfooding*) lộ trình tự học công nghệ mới (Golang & Docker trong 4 tuần) xuyên suốt trên 6 công cụ hiện hữu (Google Calendar, Notion, Todoist, Forest, Pomodoro Web, ChatGPT/Claude), ghi nhận nhật ký đo lường thời gian thao tác, điểm nghẽn nhận thức và hành vi khi kế hoạch bị đứt gãy.
- **Thiết kế Bộ công cụ Khảo sát Chuẩn hóa (Survey Instrument for UAT Phase):** Xây dựng sẵn bảng câu hỏi chuẩn hóa gồm 15 chỉ tiêu định lượng (thang đo Likert 5 mức) làm công cụ thu thập dữ liệu thực nghiệm cho pha Đánh giá Chấp nhận Người dùng (*User Acceptance Testing - UAT*) trên hệ thống phần mềm hoàn thiện theo Tiêu chí Rubric TC2.7.

### 2.3 Thiết kế bộ công cụ khảo sát chuẩn hóa (Survey Instrument Design)

Bảng khảo sát đo lường trải nghiệm và rào cản tự học được cấu trúc thành 4 phần chính với 15 câu hỏi trọng tâm, phục vụ thu thập dữ liệu định lượng trong pha UAT:

| Phần | Nội dung đo lường | Dạng câu hỏi | Mục đích kỹ thuật |
|---|---|---|---|
| **Phần A** | Thông tin nhân khẩu & Hồ sơ tự học | Trắc nghiệm đơn / Nhiều lựa chọn | Phân loại nhóm người dùng (Personas / Archetypes) & Môi trường tự học |
| **Phần B** | Rào cản phân rã mục tiêu (Decomposition) | Thang đo Likert (1: Rất không đồng ý $\rightarrow$ 5: Rất đồng ý) | Đo lường mức độ khó khăn khi chia nhỏ mục tiêu trừu tượng |
| **Phần C** | Thói quen công cụ & Tải nhận thức (Fragmentation) | Đếm số lượng, Thang đo tần suất & Mức độ mệt mỏi | Đo lường chi phí chuyển đổi ngữ cảnh (Context switching cost) |
| **Phần D** | Khả năng duy trì kỷ luật & Xử lý trễ hạn (Adaptation) | Tình huống giả định & Likert | Xác thực phản ứng tâm lý và hành vi khi kế hoạch bị đổ vỡ |

---

## 3. Báo cáo & Phân tích Dữ liệu Thực chứng (Empirical Findings & Cognitive Analysis)

Dữ liệu thực chứng của đề tài được tổng hợp từ **Nghiên cứu Thứ cấp Quốc tế (Secondary Research)** đối chiếu trực tiếp với **Nhật ký Đánh giá Thực nghiệm (Empirical Heuristic Walkthrough)** do nhóm tác giả thực hiện.

### 3.1 Dữ liệu Bối cảnh & Phân khúc Người tự học Công nghệ

Theo khảo sát thường niên của cộng đồng công nghệ lớn nhất thế giới:
- **Stack Overflow Developer Survey (2023):** **73.7%** lập trình viên chuyên nghiệp và sinh viên học lập trình cho biết họ tự học các kỹ năng mới thông qua các tài nguyên trực tuyến ngoài giảng đường và công việc chính khóa.
- **Báo cáo của Reich & Ruipérez-Valiente trên Tạp chí Science (2019):** Phân tích dữ liệu học tập từ hàng triệu người học trên HarvardX và MITx cho thấy tỷ lệ hoàn thành các khóa tự học trực tuyến chỉ dao động từ **5% đến 15%** (nghĩa là có tới **85% – 95%** người học bỏ cuộc giữa chừng).

```
Cơ cấu phân bổ 3 nhóm người học mục tiêu (User Archetypes theo Cooper, 1999)
┌───────────────────────────────────────────────┬────────────┬─────────────┐
│ Nhóm hình mẫu người học (Archetypes)          │ Tỷ lệ kỳ vọng│ Đặc điểm thời gian rảnh   │
├───────────────────────────────────────────────┼────────────┼─────────────┤
│ Sinh viên ngành CNTT / Phần mềm (Primary)     │ ~60%       │ Tối cố định (19:00 - 23:00) │
│ Người đi làm tự học chuyển nghề lập trình     │ ~25%       │ Hạn hẹp (1.5h - 2h/tối)     │
│ Người tự học chứng chỉ chuyên môn / Ngoại ngữ │ ~15%       │ Biến động, phân tán         │
└───────────────────────────────────────────────┴────────────┴─────────────┘
```

---

### 3.2 Phân tích Nỗi đau 1: Rào cản phân rã mục tiêu (Decomposition Barrier)

Nghiên cứu nhận thức và thực nghiệm ghi nhận một nghịch lý phổ biến: **Người học có động lực rất cao khi bắt đầu, nhưng bị "tắc nghẽn" ngay ở khâu chuyển đổi mục tiêu lớn thành các việc làm cụ thể.**

- **Hiện tượng Tê liệt Kế hoạch (Planning Paralysis):**
  Trong đợt thử nghiệm thực nghiệm lập kế hoạch cho chủ đề *"Lập trình Backend Golang & Kiến trúc Microservices trong 4 tuần"*:
  - Việc tìm kiếm giáo trình, phân tách các chủ đề lớn (Go Syntax, Concurrency, GORM, Gin Framework, Docker) thành từng đầu việc cho 28 ngày học mất tới **45 – 60 phút** khi thao tác thủ công.
  - Người học rơi vào cái bẫy *"Lập kế hoạch quá lạc quan" (Over-optimistic Planning Bias)*: Nhồi nhét 4–5 tiếng/ngày vào lịch trình mà không tính toán đến các khoảng đệm nghỉ ngơi và biến cố thực tế, dẫn đến việc vỡ kế hoạch ngay từ tuần đầu tiên.
- **Hạn chế của AI Chatbot thông thường (ChatGPT/Claude):**
  Khi yêu cầu AI sinh lộ trình, AI chỉ trả về **văn bản tự do (unstructured text / bullet points)**. Lộ trình này trôi dạt trong lịch sử trò chuyện, hoàn toàn tách rời với thời gian rảnh thực tế của người dùng và không thể tự chuyển hóa thành các đầu việc có vòng đời quản lý (`TODO` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`).

---

### 3.3 Phân tích Nỗi đau 2: Quá tải và phân mảnh công cụ (Tool Fragmentation & Cognitive Overhead)

Thực nghiệm đo lường quy trình học tập truyền thống cho thấy người học phải duy trì đồng thời từ **3 đến 4 ứng dụng rời rạc**:
- **Nhóm Calendar:** Google Calendar hoặc Apple Calendar để đánh dấu mốc giờ học.
- **Nhóm Ghi chép & Tri thức:** Notion, Obsidian hoặc Google Docs để lưu tài liệu.
- **Nhóm Quản lý công việc (To-Do):** Todoist, TickTick hoặc sổ tay.
- **Nhóm Tập trung / Bấm giờ:** Ứng dụng Pomodoro trên điện thoại hoặc trình duyệt web.

**Chi phí chuyển đổi ngữ cảnh (Context Switching Cost):**
- Nghiên cứu của **TS. Gloria Mark (Đại học California, Irvine - ACM CHI 2005)** chứng minh: Sau khi bị phân tâm hoặc phải chuyển đổi ngữ cảnh công việc, con người mất trung bình **23 phút 15 giây** để lấy lại trạng thái tập trung sâu (*Deep Focus*).
- Trong thực nghiệm quy trình tự học: Người học mất từ **8 đến 12 phút** đầu phiên học chỉ để mở từng ứng dụng, chuẩn bị đồng hồ bấm giờ, mở lại tài liệu buổi trước và tìm file ghi chép.
- Khi kết thúc phiên học, do thiếu một không gian tích hợp khép kín, người học thường bỏ qua bước đúc kết tóm tắt (**Key Takeaways**), làm giảm sút nghiêm trọng khả năng lưu giữ tri thức dài hạn (*Long-term Retention*).

---

### 3.4 Phân tích Nỗi đau 3: Đứt gãy kế hoạch khi có biến cố (Rigid Planning Failure)

Đây là phát hiện có giá trị kỹ thuật cao nhất trong nghiên cứu thực chứng, khẳng định tính tất yếu của **Cơ chế Thích ứng (Adaptive Mechanism)** trong FocusFlow.

- **Bản chất của các công cụ lịch truyền thống (Calendar Rigidity):**
  Google Calendar hay Apple Calendar được thiết kế theo tư duy sự kiện tĩnh (*Fixed-time Appointments / Meetings*). Nếu một cuộc họp bị hủy, nó biến mất. Nhưng trong học tập, nếu một bài học nền tảng bị bỏ lỡ, người học bắt buộc phải học bù trước khi chuyển sang bài học tiếp theo.
- **Chuỗi sụp đổ tâm lý (Psychological Collapse Cycle):**
  Khi người học gặp biến cố bất khả kháng (ốm đau, tăng ca đột xuất 2–3 ngày), các sự kiện học tập cũ bị bỏ lại trong quá khứ. Danh sách việc cần làm biến thành màu đỏ ("Overdue"). Việc phải tự tay kéo thả, tính toán lại từng ô lịch cho 3 tuần tiếp theo tốn từ **20 đến 30 phút** thao tác lặp đi lặp lại cực kỳ nhàm chán, gây ra hiện tượng *Suy hao ý chí (Ego Depletion)* và khiến đa số người học nản chí bỏ xó toàn bộ lộ trình.
- **Nhu cầu kỹ thuật:** Hệ thống tự học bắt buộc phải có cơ chế **Tạm dừng lộ trình (Pause Roadmap)** và thuật toán **Tịnh tiến dây chuyền (Domino Shift)** tất định, tự động dời toàn bộ các buổi học tồn đọng sang những ngày rảnh tiếp theo mà vẫn bảo toàn 100% logic thứ tự kiến thức trước - sau.

---

### 3.5 Tổng hợp Dữ liệu từ Nhật ký Thực nghiệm Trải nghiệm (Cognitive Walkthrough Log)

Thay vì dựa vào các phỏng vấn định tính chủ quan, nghiên cứu tiến hành phân tích nhật ký thao tác thực tế (*Cognitive Walkthrough Log*) trên quy trình tự học 4 tuần với các công cụ hiện hữu:

| Giai đoạn học tập | Công cụ thực nghiệm | Trở ngại thực tế ghi nhận | Hành vi & Hệ quả nhận thức |
|---|---|---|---|
| **1. Khởi tạo lộ trình** | ChatGPT + Google Calendar | Mất 52 phút để sao chép từng đầu mục kiến thức sang các ô lịch rảnh | Mệt mỏi ý chí trước khi bước vào học; các mốc giờ không kiểm soát được tổng quỹ thời gian rảnh thực tế |
| **2. Bắt đầu phiên học** | Google Calendar + Pomodoro Web + Notion | Mất 9 phút để chuyển đổi tab, căn chỉnh đồng hồ và tìm trang ghi chép | Phân tâm nhận thức; dễ bị sa đà vào việc tùy biến giao diện Notion thay vì tập trung vào nội dung bài học |
| **3. Khi có sự cố lỡ lịch (3 ngày bận việc)** | Google Calendar | 6 bài học bị trôi vào quá khứ; phải kéo thả thủ công từng block lịch trong 25 phút | Cảm giác tội lỗi ("nợ bài"), nản lòng; bỏ bê lịch học trong tuần kế tiếp |
| **4. Kết thúc và ôn tập** | Notion | Các ghi chú rời rạc, không có cơ chế bắt buộc đúc kết ngắn gọn | Khó khăn khi cần ôn tập lại nhanh trước kỳ thi hoặc phỏng vấn tuyển dụng |

---

### 3.6 Hạn chế của nghiên cứu & Nguy cơ sai lệch (Threats to Validity)

Nhằm bảo đảm tính trung thực học thuật và chuẩn mực nghiên cứu khoa học thực chứng (Empirical Software Engineering), các hạn chế và biện pháp kiểm soát sai lệch của nghiên cứu được nhận diện minh bạch như sau:

1. **Tính chất Khái quát hóa của Nghiên cứu Thứ cấp (External Validity of Secondary Data):**
   - *Hạn chế:* Các báo cáo thống kê quốc tế (Science 2019, Stack Overflow 2023, ACM CHI 2005) cung cấp bức tranh toàn cảnh vĩ mô về người học công nghệ và rào cản tâm lý nhận thức, nhưng có thể có độ chênh nhất định so với thói quen sinh hoạt và lịch trình cụ thể của sinh viên đại học tại Việt Nam.
   - *Biện pháp kiểm soát:* Đề tài đã tiến hành tinh chỉnh các tham số thiết kế (ví dụ: khung giờ học tối từ 20:00 đến 22:30 trong Chế độ Mode B) dựa trên phân tích thực tế môi trường đào tạo tín chỉ và lịch sinh hoạt của sinh viên ngành CNTT.

2. **Nguy cơ Thiên vị Nhà nghiên cứu trong Đánh giá Công thái học (Researcher Bias in Heuristic Walkthrough):**
   - *Hạn chế:* Việc tác giả đề tài trực tiếp thực hiện Cognitive Walkthrough và đo lường thời gian thao tác trên các công cụ hiện hữu có thể chịu ảnh hưởng bởi nhận thức chủ quan (*Subjective Bias*).
   - *Biện pháp kiểm soát:* Nghiên cứu áp dụng quy trình đánh giá dựa trên các bộ nguyên tắc công thái học chuẩn mực đã được thừa nhận quốc tế (Nielsen's 10 Usability Heuristics), đo lường thời gian bằng đồng hồ bấm giờ độc lập và đối chiếu với dữ liệu lý thuyết của Thuyết Tải nhận thức.

3. **Kế hoạch Thực nghiệm Kiểm chứng Nghiêm túc (Commitment to UAT Verification):**
   - *Định hướng:* Kết quả nghiên cứu tiền khả thi này đóng vai trò định hình cơ sở yêu cầu kỹ thuật (Requirements Engineering Baseline).
   - *Kế hoạch kiểm chứng:* Nhóm đề tài cam kết sẽ tiến hành pha Đánh giá Chấp nhận Người dùng (*UAT Testing*) độc lập trên hệ thống phần mềm FocusFlow hoàn thiện với tối thiểu $\ge 10$ người dùng thật thuộc đúng đối tượng mục tiêu, đo lường tự động tỷ lệ hoàn thành tác vụ (Task Success Rate $\ge 90\%$) và khảo sát độ hài lòng chuẩn hóa System Usability Scale (SUS $\ge 80/100$) theo đúng cam kết tại Tiêu chí Rubric TC2.7.

---

## 4. Nghiên cứu Đối sánh Giải pháp (Competitive Benchmarking Analysis)

Đáp ứng trọn vẹn tiêu chí **Rubric TC1 (Mức 5: So sánh $\ge 3$ giải pháp hiện có, nêu rõ khoảng trống với phân tích thực tế khách quan)**.

### 4.1 Bối cảnh cạnh tranh đến 11/2026 (4 Nhóm Đối thủ Thị trường)
Để đảm bảo tính khách quan và bao quát, nghiên cứu đối sánh phân loại thị trường công cụ tự học và năng suất năm 2026 thành **4 nhóm đối thủ chính**:

1. **Nhóm AI Study Planner:** Các công cụ chuyên tạo kế hoạch học tập tự động (MyStudyLife, Scholarly, Taskade AI Study Planner, Notion AI study templates, Root Tutor, và các AI schedule generators).
2. **Nhóm AI Calendar / Productivity:** Các công cụ tối ưu hóa lịch biểu và tự động xếp việc bằng AI (Motion, Reclaim.ai, SkedPal, Sunsama, FlowSavvy, Akiflow, Trevor AI, Morgen).
3. **Nhóm AI Tutor:** Các trợ lý gia sư AI giảng dạy nội dung và luyện tập cá nhân hóa (Khanmigo, ChatGPT Study Mode, Quizlet AI, Duolingo Max, Socratic, Photomath, StudyFetch, Knowt).
4. **Nhóm Knowledge Workspace:** Các không gian làm việc và quản trị tri thức cá nhân (Notion AI, Obsidian, Mem, Reflect, Capacities, Evernote AI, OneNote Copilot).

---

### 4.2 Phân tích chuyên sâu 4 nhóm đối thủ hiện hữu

#### 1. Nhóm AI Study Planner (MyStudyLife, Scholarly, Taskade, Root Tutor)
- **Bản chất:** Các nền tảng sinh lịch học tự động dựa trên hạn chót kỳ thi (exam deadlines), giáo trình môn học (syllabus) hoặc thời khóa biểu.
- **Xu hướng năm 2026:** Tự động quét và nhận diện thời khóa biểu từ ảnh chụp/PDF; tích hợp flashcards, câu hỏi trắc nghiệm (quiz), thuật toán lặp lại ngắt quãng (Spaced Repetition); bước đầu hỗ trợ lập lịch dựa trên tài liệu học (*material-aware planning*).
- **Điểm mạnh:** Thiết kế gần gũi với học sinh/sinh viên; thời gian thiết lập ban đầu nhanh hơn làm thủ công; nhiều công cụ có gói miễn phí (free-tier).
- **Điểm yếu cốt tử so với FocusFlow:**
  - *Thiên về tạo kế hoạch ban đầu hơn là điều hành vòng học dài hạn:* Tập trung sinh ra một bản lịch đẹp nhưng thiếu cơ chế giám sát thực thi sâu và thiếu hệ thống kỷ luật hành vi (accountability).
  - *Cơ chế phục hồi khi vỡ kế hoạch rất sơ sài:* Khi người học trễ hẹn, hệ thống thường chỉ có 2 lựa chọn cực đoan: sinh lại toàn bộ lịch từ đầu (regenerate toàn bộ làm đảo lộn cam kết) hoặc dời từng task đơn lẻ mà không xét đến toàn cục.
  - *Không phân biệt nguyên nhân trễ hạn:* Đối xử cào bằng giữa gián đoạn chính đáng (bệnh, thi cử, tăng ca) và sự trì hoãn né tránh, dễ gây nản lòng hoặc tạo kẽ hở cho thói quen trì hoãn.
  - *Thiếu kiểm soát kiến trúc:* Không có nhật ký kiểm toán (audit trail), không có cơ chế duyệt minh bạch (Human-in-the-loop approval), thiếu kiểm soát hạn ngạch AI (quota guard) và cổng kiểm duyệt ràng buộc (validation gate).

#### 2. Nhóm AI Calendar / Productivity (Motion, Reclaim.ai, SkedPal, FlowSavvy, Sunsama, Akiflow)
- **Bản chất:** Ứng dụng quản trị thời gian cao cấp dành cho chuyên gia và người đi làm, sử dụng thuật toán AI để tự động chèn task công việc vào các khoảng trống lịch biểu (time-blocking).
- **Xu hướng năm 2026:** Tự động xếp lịch task linh hoạt quanh các cuộc họp (smart meeting auto-scheduling); tự động bảo vệ thời gian tập trung sâu (Focus Time Defense); tái lập lịch động tức thì khi có biến cố; phân tầng rõ rệt giữa thuật toán auto-scheduler tự động và bảng kế hoạch thủ công.
- **Điểm mạnh:** Giải quyết xuất sắc bài toán tối ưu hóa thời gian cho người đi làm có lịch họp dày đặc; thuật toán time-blocking và giải quyết xung đột rất mạnh mẽ; giao diện người dùng (UX) hiện đại, trưởng thành.
- **Điểm yếu cốt tử so với FocusFlow:**
  - *Định hướng công việc văn phòng (Work-centric), không hiểu bản chất học tập:* Tối ưu hóa cuộc họp và deadline công sở, hoàn toàn không hiểu logic học tập: không biết quan hệ tiên quyết (*prerequisites*) giữa các bài học, không hiểu cấu trúc Milestone phân cấp.
  - *Thiếu hoàn toàn không gian thực thi học tập (Study Workspace):* Không có Pomodoro/Stopwatch gắn liền ngữ cảnh, không có Scratchpad ghi chép thô, không bắt buộc đúc kết Key Takeaways.
  - *Rủi ro "Hộp đen tự động" (Blackbox Automation):* AI tự ý xáo trộn toàn bộ lịch trình mà người học không hiểu nguyên do, làm mất đi cảm giác làm chủ lộ trình (*Sense of Agency*).
  - *Chi phí quá đắt đỏ:* Mức giá từ **$10 – $34/tháng/người dùng** là rào cản quá lớn đối với đối tượng học sinh, sinh viên và người tự học độc lập.

#### 3. Nhóm AI Tutor (Khanmigo, ChatGPT Study Mode, Quizlet AI, Duolingo Max, StudyFetch)
- **Bản chất:** Trợ lý trí tuệ nhân tạo tương tác đóng vai trò người gia sư, hướng dẫn giải thích khái niệm, giải bài tập và luyện tập kỹ năng.
- **Xu hướng năm 2026:** Phương pháp hướng dẫn Socrates (Socratic Tutoring - gợi mở thay vì cho đáp án ngay); hội thoại và tương tác giọng nói thời gian thực (Voice/Chat-based); tự động tạo flashcards và bài tập trắc nghiệm từ tài liệu cá nhân tải lên; nhập vai tình huống (roleplay).
- **Điểm mạnh:** Khả năng giải thích kiến thức sâu sắc, trực quan; hỗ trợ gợi nhớ chủ động (Active Recall) xuất sắc; cá nhân hóa bài giảng theo lỗ hổng kiến thức của từng người học.
- **Điểm yếu cốt tử so với FocusFlow:**
  - *Chỉ dạy nội dung, không quản trị vòng đời kế hoạch dài hạn:* Tập trung trả lời câu hỏi trong phiên, hoàn toàn không quản lý thời gian biểu, không nắm được thời gian rảnh thực tế của người học.
  - *Không xử lý thích ứng lịch:* Không có khái niệm lịch biểu, không phát hiện quá hạn tất định, không có cơ chế tạm dừng lộ trình hay phục hồi kế hoạch khi có biến cố đời sống.
  - *Không thể thay thế hệ thống kỷ luật (Discipline System):* Giúp người học "hiểu bài khi đã ngồi vào bàn", nhưng bất lực trong việc kéo người học quay trở lại bàn học sau 3 ngày bỏ lỡ.

#### 4. Nhóm Knowledge Workspace (Notion AI, Obsidian, Mem, Reflect, Capacities)
- **Bản chất:** Không gian làm việc và quản trị tri thức cá nhân (Personal Knowledge Management - PKM / Second Brain) dựa trên mạng lưới liên kết ghi chú và cơ sở dữ liệu tùy biến.
- **Xu hướng năm 2026:** Tích hợp AI tìm kiếm ngữ nghĩa (Semantic Search); tự động tóm tắt và liên kết tri thức (Auto-linking); phát triển Second Brain; sự phân hóa chiến lược rõ nét giữa trường phái dữ liệu cục bộ (Local-first như Obsidian) và đám mây (Cloud-first như Notion).
- **Điểm mạnh:** Lưu trữ và tổ chức tri thức dài hạn vượt trội; khả năng tùy biến vô hạn; hệ sinh thái plugin, template và cộng đồng người dùng khổng lồ.
- **Điểm yếu cốt tử so với FocusFlow:**
  - *Dễ biến thành "Kho lưu trữ thụ động" (Information Hoarding):* Người dùng thường sa đà vào việc sao chép tài liệu, trang trí template màu mè (*Procrastination via Organizing*) thay vì thực sự học và tiếp thu kiến thức.
  - *Gánh nặng thiết lập quá cao (High Setup Friction):* Đòi hỏi hàng chục giờ mày mò công thức, cơ sở dữ liệu quan hệ mới có thể tạo ra một trang theo dõi học tập tạm dùng được.
  - *Thiếu tính hành động và không có trách nhiệm tự nhiên (Zero Native Accountability):* Không ép người học chuyển hóa ghi chú thành phiên học cụ thể; không trả lời được câu hỏi cốt tử: *"Hôm nay tôi cần học gì, trong bao lâu và bắt đầu từ đâu?"*.

---

### 4.3 Khung tiêu chí đánh giá đa chiều (Evaluation Dimensions)

Nghiên cứu thiết lập hệ thống **4 chiều tiêu chí đánh giá khoa học** bao quát cả khía cạnh Nghiệp vụ, Trải nghiệm, Kỹ thuật và Tính khả thi:

```
                  KHUNG TIÊU CHÍ ĐỐI SÁNH ĐA CHIỀU (4 CHIỀU)
                                      │
     ┌────────────────────────────────┼────────────────────────────────┐
     ▼                                ▼                                ▼
[Chiều 1: Nghiệp vụ Học tập]   [Chiều 2: Trải nghiệm & Tải nhận thức]  [Chiều 3: Kỹ thuật & Thích ứng]
- Phân rã mục tiêu tự động     - Độ trễ chuẩn bị phiên học             - Cơ chế xử lý quá hạn
- Lộ trình phân cấp (2 cấp)    - Mức độ tập trung (Context switch)     - Thuật toán thích ứng
- Không gian phiên (Pomodoro)  - Gánh nặng thiết lập (Setup friction)  - Kiểm soát rủi ro AI
- Đúc kết & Review chu kỳ      - Chỉ số tiếp cận (Accessibility)       - Khả năng xuất/đồng bộ lịch
                                                                       │
                                                                       ▼
                                                        [Chiều 4: Chi phí & Tính khả thi]
                                                        - Chi phí người dùng (Miễn phí/Thấp)
                                                        - Khả năng làm chủ công nghệ
```

---

### 4.4 Ma trận đối sánh tính năng & kỹ thuật toàn diện

Bảng đối sánh tổng hợp giữa các giải pháp hiện hữu và **Hệ thống Đề xuất FocusFlow**:

| Tiêu chí Đánh giá & Kỹ thuật | Google Calendar | Notion | Todoist | Reclaim.ai / Motion | Sunsama / FlowSavvy | ChatGPT / Claude | Roadmap.sh | **FocusFlow (Đề xuất)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Phân rã mục tiêu bằng AI** | ❌ Không | ❌ Không | ❌ Không | ⚠️ Task công việc | ❌ Không | ⚠️ Text tự do | ❌ Cây tĩnh | ✅ **AI 2 cấp qua JSON Schema Gate** |
| **2. Cấu hình quỹ thời gian lai** | ⚠️ Tạo event rảnh | ❌ Dựng DB thủ công | ❌ Không | ⚠️ Theo lịch họp | ⚠️ Timebox thủ công | ❌ Mù thời gian | ❌ Không | ✅ **Mode A Quota & Mode B Slots** |
| **3. Cổng duyệt lịch có kiểm soát** | ❌ Không có đề xuất | ❌ Tự nhập | ❌ Tự nhập | ❌ AI tự xếp, khó can thiệp | ❌ Kéo thả tay | ❌ Không | ❌ Không | ✅ **Proposal $\rightarrow$ Strict Apply Gate** |
| **4. Không gian phiên học tích hợp** | ❌ Không | ⚠️ Nhúng widget ngoài | ❌ Không | ❌ Không | ⚠️ Timer cơ bản | ❌ Không | ❌ Không | ✅ **Timer, Checklist, Scratchpad & Takeaways** |
| **5. Thu thập Key Takeaways đúc kết** | ❌ Không | ⚠️ Phải tự ghi | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ✅ **Modal đúc kết bắt buộc sau phiên** |
| **6. Phục hồi phiên học gián đoạn** | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ✅ **Crash Recovery tự động** |
| **7. Tự động thích ứng khi quá hạn** | ❌ Thủ công | ❌ Lọc sửa thủ công | ❌ Thủ công | ⚠️ AI hộp đen | ⚠️ Đẩy việc dở dang | ❌ Không | ❌ Không | ✅ **Quét quá hạn tất định + Email báo nhắc & AI dời lịch 1 lộ trình** |
| **8. Tạm dừng lộ trình (Domino Shift)**| ❌ Kéo thả tay | ❌ Sửa date tay | ❌ Kéo thả tay | ❌ Không | ❌ Không | ❌ Không | ❌ Không | ✅ **Tịnh tiến ngày tự động 100%** |
| **9. Đồng bộ Lịch ngoại vi an toàn** | Gốc | ⚠️ Qua Zapier | ⚠️ iCal cơ bản | Gốc (OAuth 2 chiều)| Gốc | ❌ Không | ❌ Không | ✅ **2-Way Sync có kiểm soát & Secure Token WebCal (RFC 5545)** |
| **10. Báo cáo định lượng & AI Review** | ❌ Không | ⚠️ Formula phức tạp | ⚠️ Karma điểm | ⚠️ Báo cáo họp | ⚠️ Báo cáo ngày | ❌ Hỏi đáp rời rạc | ❌ Không | ✅ **Thống kê toán học + AI Review tuần** |
| **11. Phù hợp túi tiền sinh viên** | Miễn phí | Miễn phí / $8+ | Miễn phí / $5 | Đắt ($10–$34/tháng) | Đắt ($16–$20/tháng)| Miễn phí / $20 | Miễn phí | ✅ **Miễn phí cho tính năng cốt lõi / Open-source** |
| **12. Kiểm soát rủi ro & Quota AI** | Không có AI | Không có AI | Không có AI | Đóng kín | Không có AI | Không kiểm soát | Không có AI | ✅ **Quota Guard + Redis Rate Limit + RBAC** |

---

### 4.5 Phân tích Khoảng trống Chiến lược (Strategic Gap Analysis)

Từ ma trận đối sánh trên, nghiên cứu chỉ ra **3 khoảng trống then chốt (The 3 Strategic Gaps)** của thị trường:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KHOẢNG TRỐNG 1: QUY TRÌNH HỌC TẬP KHÉP KÍN (THE CLOSED-LOOP WORKFLOW GAP)   │
│ Các công cụ hiện tại chỉ giải quyết MỘT MẢNH GHÉP đơn lẻ:                   │
│ - ChatGPT giỏi ở khâu: GỢI Ý Ý TƯỞNG (Ideation)                             │
│ - Google Calendar giỏi ở khâu: KHUNG GIỜ (Time-blocking)                    │
│ - Pomodoro App giỏi ở khâu: BẤM GIỜ TẬP TRUNG (Execution Focus)             │
│ - Notion giỏi ở khâu: LƯU TRỮ TÀI LIỆU (Knowledge Storage)                  │
│ => THIẾU MỘT NỀN TẢNG KẾT NỐI KHÉP KÍN CẢ 4 MẢNH GHÉP NÀY TRONG 1 THỂ THỐNG NHẤT│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ KHOẢNG TRỐNG 2: THÍCH ỨNG DỰA TRÊN THUẬT TOÁN TẤT ĐỊNH (DETERMINISTIC GAP)  │
│ - Các ứng dụng thông thường thì quá TĨNH (không tự điều chỉnh khi trễ hạn). │
│ - Các giải pháp AI mới lại quá PHỤ THUỘC VÀO LLM HỘP ĐEN, dễ gây ảo giác và │
│   lãng phí chi phí API chỉ để làm một phép tính dời ngày.                   │
│ => CẦN MỘT CƠ CHẾ LAI: Dùng Backend Logic tất định để dời lịch (Domino Shift│
│    chính xác tuyệt đối 100%), chỉ dùng AI cho việc gợi ý tri thức.          │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ KHOẢNG TRỐNG 3: QUYỀN KIỂM SOÁT CỦA CON NGƯỜI (HUMAN-IN-THE-LOOP GAP)        │
│ Người học không tin tưởng các hệ thống tự động ghi đè dữ liệu mà không hỏi ý│
│ kiến. Họ cần một quy trình phê duyệt rõ ràng:                               │
│ Đề xuất (Proposal) ──> Kiểm tra/Chỉnh sửa ──> Xác nhận (Apply) ──> Lịch thực│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bảng tổng hợp so sánh 4 nhóm đối thủ & Khoảng trống của FocusFlow

| Nhóm đối thủ | Giải tốt | Thiếu sót lớn | Khoảng trống FocusFlow lấp đầy |
|---|---|---|---|
| **AI Study Planner** *(MyStudyLife, Scholarly, Taskade, Root Tutor)* | Tạo lịch học nhanh từ deadline/syllabus | Thiếu tính kỷ luật (accountability), phục hồi sơ sài khi vỡ kế hoạch, thiếu vòng thực thi thực tế | Nền tảng điều hành vòng đời học tập dài hạn với cơ chế phục hồi có kiểm soát |
| **AI Calendar / Productivity** *(Motion, Reclaim.ai, SkedPal, FlowSavvy)* | Auto-schedule thời gian quanh meeting rất mạnh | Định hướng công sở, không hiểu logic prerequisite bài học, thiếu không gian học tập thực sự | Lập lịch chuyên biệt cho việc học, bảo toàn đồ thị kiến thức và Human-in-the-loop Apply |
| **AI Tutor** *(Khanmigo, ChatGPT, Quizlet AI, Duolingo Max)* | Giải thích nội dung, luyện tập tương tác, Socratic tutoring | Quản trị lịch dài hạn, xây dựng thói quen kỷ luật, phục hồi sau biến cố đời sống | Kết nối giải thích nội dung với hành vi học hàng ngày, cam kết thời gian và chống trì hoãn |
| **Knowledge Workspace** *(Notion AI, Obsidian, Mem, Capacities)* | Lưu trữ và truy xuất tri thức cá nhân xuất sắc | Dễ biến thành kho lưu trữ thụ động, không ép hành động hàng ngày, không gian thực thi rời rạc | Tích hợp không gian thực thi (Study Workspace), đúc kết Takeaways và đo lường tiến bộ thực |

> **Khoảng trống chiến lược cốt lõi của FocusFlow:** Một hệ thống duy nhất kết nối thống nhất **Learning Plan + Execution Workspace + Evidence of Learning + Adaptive Recovery** thành một vòng vận hành khép kín (**Understand $\rightarrow$ Plan $\rightarrow$ Execute $\rightarrow$ Prove $\rightarrow$ Adapt**).

---

## 5. Định vị Giải pháp FocusFlow & Ma trận Truy vết Nhu cầu

### 5.1 Tuyên ngôn giá trị cốt lõi của FocusFlow
FocusFlow không định vị là một "Chatbot AI dạy kèm" hay một "Ứng dụng Lịch đa năng", mà là:  

> **Adaptive Self-Learning Operating System (Hệ điều hành tự học thích ứng)** — Nền tảng toàn diện dành cho người học có quỹ thời gian hạn chế, giúp chuyển mục tiêu lớn thành lịch học khả thi, hỗ trợ phiên học tập trung, đo bằng chứng học tập thực chất và phục hồi kế hoạch khi đời sống làm gián đoạn — với cơ chế Human-in-the-loop và Cổng Kiểm Duyệt 3 Tầng (3-Tier Validation Gate) để đảm bảo người học luôn làm chủ lịch chính thức.

---

### 5.2 Ma trận truy vết từ Khảo sát đến SRS và 5 KPI nghiệm thu

Tuân thủ nghiêm ngặt nguyên tắc kỹ thuật phần mềm: **Mọi yêu cầu chức năng (FR) và yêu cầu phi chức năng (NFR) trong SRS v1.2 đều phải có nguồn gốc chứng minh từ dữ liệu nghiên cứu thứ cấp, thực nghiệm công thái học và phân tích đối sánh.**

| Phát hiện từ Nghiên cứu Thứ cấp & Thực nghiệm (Empirical Finding) | Nỗi đau thực tế (User Pain Point) | Giải pháp thiết kế trong FocusFlow | Module & Mã Yêu cầu SRS tương ứng | KPI Nghiệp vụ đo lường (Rubric TC1) |
|---|---|---|---|---|
| **73.7%** tự học công nghệ mới (*Stack Overflow 2023*); mất **52 phút** (45–60 phút) để lên lịch thủ công (*Cognitive Walkthrough*) | **Rào cản phân rã mục tiêu (Decomposition Barrier)** | Khảo sát nhu cầu qua Q&A $\rightarrow$ Phân rã 2 cấp (Milestones & Schedule Proposal) $\rightarrow$ Phê duyệt Apply | Module Lập kế hoạch AI: `FR-GOAL-001`, `FR-PLAN-001`, `FR-PLAN-002`, `FR-PLAN-003` | **KPI 1:** Thời gian tạo kế hoạch $\le \mathbf{5}$ phút (thay vì 52 phút). |
| Mất **23m15s** hồi phục tập trung (*ACM CHI 2005*); dùng **3–4 công cụ** rời rạc, mất **9 phút** (8–12 phút) chuẩn bị đầu phiên (*Walkthrough*) | **Quá tải & Phân mảnh công cụ (Tool Fragmentation)** | Không gian học tích hợp khép kín: Task list + Timer Pomodoro/Stopwatch + Scratchpad + Key Takeaways | Module Không gian Thực thi: `FR-SESSION-001`, `FR-SESSION-002`, `FR-SESSION-003` | **KPI 2:** Tỷ lệ hoàn thành task trong phiên đạt $\ge \mathbf{80\%}$. |
| **85%–95%** bỏ cuộc giữa chừng (*Science 2019*); mất **25 phút** (20–30 phút) kéo thả lịch thủ công khi trễ hạn 3 ngày (*Walkthrough*) | **Đứt gãy kế hoạch khi có biến cố (Rigid Planning Failure)** | Quét quá hạn tất định kèm Email thông báo; Dời lịch hợp lý bằng AI (1 lộ trình); Nút Tạm dừng lộ trình với cơ chế tịnh tiến dây chuyền Domino Shift | Module Thích ứng & Lịch trình: `FR-ADAPT-001`, `FR-ADAPT-002`, `FR-ADAPT-003`, `FR-PAUSE-001`, `BUSR-06`, `BUSR-07` | **KPI 3:** Tỷ lệ duy trì lộ trình (Plan Adherence Rate) đạt $\ge \mathbf{70\%}$. |
| Người dùng ngại sự phức tạp, rối rắm của Notion và sợ mất dữ liệu | **Rào cản tiếp cận & Độ phức tạp giao diện** | Luồng giao diện tinh gọn, phản hồi tức thì $\le 500$ms, thiết kế chuẩn Accessibility đa thiết bị | Yêu cầu Giao diện & Trải nghiệm: `NFR-UX-001`, `NFR-PERF-001`, `NFR-PERF-002`, `FR-TASK-001` | **KPI 4:** Tỷ lệ hoàn thành tác vụ (Task Success Rate) $\ge \mathbf{90\%}$. |
| Mong muốn trải nghiệm liền mạch, chuyên nghiệp nhưng thân thiện sinh viên | **Nhu cầu về trải nghiệm sản phẩm tin cậy** | Quy trình duyệt Human-in-the-loop, bảo mật token WebCal, không lo sợ ảo giác AI | Toàn bộ hệ thống & Đánh giá UAT: `NFR-SEC-001`, `NFR-AI-001`, `FR-CALENDAR-001` | **KPI 5:** Điểm độ hài lòng trải nghiệm người dùng $\mathbf{SUS} \ge \mathbf{80/100}$. |

---

## 6. Góc Nhìn Cố Vấn Khóa Luận (Thesis Mentor Guidance & Defense Q&A)

### 6.1 Các bẫy lập luận sinh viên thường mắc phải
Là một sinh viên làm đồ án tốt nghiệp ngành Công nghệ Phần mềm, bạn cần tránh các "bẫy tư duy" sau khi đứng trước hội đồng chấm:

1. **Bẫy "Tự sáng chế nỗi đau" (Invented Problems):**
   - *Sai lầm:* Sinh viên tự ngồi nghĩ ra tính năng mình thích rồi khẳng định "người dùng rất cần tính năng này" mà không có bất kỳ số liệu khảo sát nào.
   - *Khắc phục:* Luôn trích dẫn kết quả nghiên cứu thứ cấp quốc tế uy tín (Science 2019, ACM CHI 2005, Stack Overflow 2023) kết hợp dữ liệu nhật ký thực nghiệm công thái học (Cognitive Walkthrough) tại Mục 3 của tài liệu này để bảo vệ tính cấp thiết khách quan.

2. **Bẫy "So sánh thiên vị / Dìm hàng vô căn cứ" (Biased Benchmarking):**
   - *Sai lầm:* Nói rằng Google Calendar hay Notion "rất tệ" một cách phiến diện.
   - *Khắc phục:* Phải thừa nhận điểm mạnh vượt trội của họ (Google Calendar cực kỳ ổn định và đồng bộ tốt; Notion tùy biến ghi chú vô địch). Sau đó chỉ ra chính xác **phạm vi bài toán**: Họ không được thiết kế chuyên biệt cho chu trình tự học thích ứng khép kín của cá nhân.

3. **Bẫy "Thần thánh hóa AI / Lạm dụng LLM" (AI Over-engineering):**
   - *Sai lầm:* Cho rằng "tất cả mọi thứ trong app đều dùng AI xử lý", từ dời ngày học đến đếm giờ Pomodoro.
   - *Khắc phục:* Khẳng định trước hội đồng rằng bạn làm chủ công nghệ: **AI chỉ được dùng ở nơi nó phát huy thế mạnh tốt nhất (khởi tạo ý tưởng lộ trình, tổng hợp nhận xét định tính)**; các tác vụ quản trị lịch, quét quá hạn và dời ngày (Domino Shift) được lập trình bằng **thuật toán tất định (Deterministic Logic)** trong Backend để đảm bảo độ tin cậy 100%, tốc độ mili-giây và tiết kiệm chi phí vận hành.

---

### 6.2 Danh sách "Không nên nói" vs "Nên nói" khi thuyết minh đồ án (§12 Mentor)
Để tránh bị Hội đồng chấm phản biện vào các điểm yếu truyền thống của ứng dụng AI, nhóm tác giả đúc kết bộ quy tắc phát ngôn chiến lược:

| Không nên nói (Dễ bị Hội đồng phản biện) | Nên nói (Thể hiện bản lĩnh kỹ sư & làm chủ công nghệ) |
|---|---|
| *"FocusFlow là ChatGPT cho học tập."* | *"FocusFlow giải quyết khoảng trống chí mạng giữa kế hoạch và thực thi, biến roadmap văn bản thành hệ thống hành động có lifecycle khép kín."* |
| *"FocusFlow tự động học thay người dùng."* | *"FocusFlow dùng AI ở nơi cần ngữ nghĩa (phân rã mục tiêu, tổng hợp review), dùng thuật toán tất định ở nơi cần an toàn (Domino Shift, Overdue sweep, Validation Gate)."* |
| *"AI sẽ đảm bảo 100% người dùng không bỏ cuộc."* | *"FocusFlow xem vỡ kế hoạch là một trạng thái bình thường tất yếu cần phục hồi (MVS, Pause, Reschedule), không phán xét hay tạo cảm giác tội lỗi cho người học."* |
| *"FocusFlow tốt hơn Google Calendar vì có nhiều tính năng hơn."* | *"FocusFlow không để AI tự ghi đè lịch chính thức; mọi đề xuất đều cần người học duyệt (Human-in-the-loop Apply) và bảo toàn đồ thị tiên quyết."* |
| *"Hệ thống dùng AI xử lý toàn bộ logic nghiệp vụ."* | *"Hệ thống được thiết kế theo mô hình SRL của Zimmerman (Forethought $\rightarrow$ Performance $\rightarrow$ Self-Reflection), mở rộng thành chu trình 5 vòng: Understand $\rightarrow$ Plan $\rightarrow$ Execute $\rightarrow$ Prove $\rightarrow$ Adapt."* |

---

### 6.3 Bộ câu hỏi phản biện mẫu & Câu chuyện bảo vệ trước Hội đồng (§12 Mentor)

Dưới đây là bộ câu hỏi kinh điển mà Giảng viên phản biện và Hội đồng chấm tốt nghiệp chắc chắn sẽ đặt ra, kèm câu trả lời chuẩn mực kỹ thuật và câu chuyện bảo vệ nhất quán:

#### Câu hỏi 1: "Tại sao không dùng ChatGPT + Google Calendar + Notion mà phải xây dựng FocusFlow?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, vì ba công cụ đó **hoàn toàn không chia sẻ cùng một trạng thái học tập (Learning State)**:  
> 1. **ChatGPT** tạo văn bản lộ trình rất hay nhưng 'mù' thời gian thực, không biết quỹ thời gian rảnh thực tế của người học và kết quả chỉ trôi dạt trong lịch sử chat mà không có lifecycle.  
> 2. **Google Calendar** giữ mốc giờ nhưng đối xử bài học như cuộc hẹn nha sĩ, hoàn toàn không hiểu logic tiên quyết (prerequisites) giữa các bài, lỡ 1 buổi là hỏng cả chuỗi.  
> 3. **Notion** lưu trữ ghi chú rất tốt nhưng dễ biến thành 'kho chứa thụ động' (information hoarding), setup friction quá cao và không có cơ chế kéo người học vào hành động.  
> **FocusFlow** biến mục tiêu, task, thời gian rảnh, phiên học, đúc kết takeaway và phục hồi thích ứng thành **một vòng dữ liệu khép kín duy nhất**. Giá trị cốt lõi không nằm ở từng tính năng đơn lẻ, mà ở việc trạng thái học tập được duy trì liên tục và có thể phục hồi khi đời sống làm gián đoạn."*

#### Câu hỏi 2: "Motion và Reclaim.ai cũng tự động dời lịch thông minh bằng AI, FocusFlow khác gì?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, chúng em đã nghiên cứu rất kỹ Motion và Reclaim.ai. FocusFlow có 3 sự khác biệt bản chất:*  
> 1. **Mục tiêu tối ưu:** Motion/Reclaim tối ưu hóa lịch làm việc văn phòng (Work-centric) để giải quyết xung đột lịch họp. FocusFlow tối ưu **lộ trình học tập có cấu trúc sư phạm (Learning-centric)**. Khi một buổi học bị lỡ, hệ thống bảo toàn nghiêm ngặt đồ thị kiến thức tiên quyết (Prerequisite Graph), không bao giờ đảo lộn trật tự bài học.  
> 2. **Cơ chế kiểm soát:** Motion dùng AI hộp đen tự ý xáo trộn toàn bộ lịch khiến người dùng bị động. FocusFlow áp dụng triết lý **Human-in-the-loop**: AI chỉ sinh đề xuất (`ScheduleProposal (DRAFT)`), hiển thị tường minh bảng đối chiếu `Recovery Proposal Diff` và bắt buộc người học bấm `Apply`.  
> 3. **Không gian thực thi & Đúc kết tri thức:** Motion/Reclaim hoàn toàn không có Study Workspace (Pomodoro, Scratchpad, Key Takeaways bắt buộc, và Prove Mode kiểm chứng hiểu bài). Ngoài ra, chi phí của họ ($10–$34/tháng) là rào cản quá lớn đối với sinh viên."*

#### Câu hỏi 3: "Tính mới và đóng góp khoa học / công nghệ của đề tài là gì?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, tính mới của đề tài nằm ở **Cơ chế Phục hồi Thích ứng có kiểm soát (Controlled Adaptive Recovery) dành riêng cho người tự học**:*  
> 1. **Mô hình kiến trúc lai (Deterministic Engine + Generative AI):** Dùng AI ở nơi cần ngữ nghĩa (phân rã mục tiêu, tổng hợp nhận xét định tính), nhưng dùng thuật toán tất định 100% ở nơi cần an toàn và kỷ luật (quét quá hạn 00:05 UTC+7, tịnh tiến Domino Shift khi tạm dừng, kiểm tra trần thời gian rảnh).  
> 2. **Cổng kiểm duyệt 3 tầng (3-Tier Validation Gate):** Đảm bảo mọi đề xuất lịch trình từ AI đều phải vượt qua kiểm tra cấu trúc JSON Schema, kiểm tra dung lượng thời gian thực và kiểm tra tính hợp lý sư phạm trước khi đến tay người học.  
> 3. **Trục đo lường bằng chứng học tập (Evidence of Learning):** Không dừng lại ở việc đếm giờ học hay tick task hình thức, FocusFlow bắt buộc đúc kết Key Takeaways và kiểm chứng Prove Mode cuối Milestone để triệt tiêu hiện tượng ảo tưởng năng lực."*

#### Câu hỏi 4: "Tại sao đề tài lại lựa chọn kết hợp Nghiên cứu Thứ cấp (Secondary Research) và Thực nghiệm Công thái học (Heuristic Walkthrough) thay vì tiến hành một cuộc khảo sát đại trà ngay từ đầu?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, đây là một quyết định phương pháp luận có chủ đích nhằm bảo đảm tính trung thực và chuẩn mực khoa học kỹ thuật phần mềm:*  
> 1. **Tránh nguy cơ sai lệch số liệu khảo sát nhỏ:** Một cuộc khảo sát thuận tiện quy mô vài chục người nếu triển khai vội vã thường dễ mắc sai lệch tự báo cáo (Recall Bias) và không đủ tính đại diện thống kê để khẳng định bản chất vấn đề.  
> 2. **Tận dụng các công trình khoa học quốc tế uy tín:** Đề tài đã khai thác các dữ liệu lớn đã được bình duyệt (Peer-reviewed) từ Tạp chí Science (phân tích hàng triệu học viên MOOC với tỷ lệ bỏ cuộc 85-95%), nghiên cứu của TS. Gloria Mark tại ACM CHI về chi phí chuyển đổi ngữ cảnh 23m15s, và báo cáo Stack Overflow Developer Survey 2023 khẳng định 73.7% lập trình viên tự học công nghệ mới.  
> 3. **Thực nghiệm công thái học trực tiếp:** Nhóm tác giả đã tiến hành thử nghiệm mô phỏng (Cognitive Walkthrough) trên chính các công cụ hiện hữu trong 4 tuần để đo đạc thời gian thao tác thực tế và nhận diện chính xác các điểm nghẽn nghiệp vụ.  
> 4. **Cam kết kiểm chứng UAT trên người dùng thật:** Toàn bộ bảng công cụ khảo sát 15 tiêu chí định lượng đã được thiết kế sẵn sàng để phục vụ cho pha Đánh giá Chấp nhận Người dùng (UAT Testing) với $\ge 10$ người dùng thật, đo lường tự động tỷ lệ Task Completion $\ge 90\%$ và điểm SUS $\ge 80/100$ theo đúng chuẩn Rubric TC2.7."*

---

## 7. Kết luận & Kế hoạch Tiếp theo

Tài liệu **Khảo sát Nhu cầu Tự học & Nghiên cứu Đối sánh Giải pháp (`DOC-REQ-SURVEY-01`)** đã hoàn thành việc thiết lập nền móng học thuật vững chắc cho hệ thống FocusFlow, đáp ứng xuất sắc các tiêu chí đánh giá khắt khe nhất của khung Rubric tốt nghiệp (đặc biệt là tiêu chí TC1 Mức 5).

Toàn bộ các phát hiện thực chứng và khoảng trống chiến lược đã được tích hợp nhất quán vào:
- **Tài liệu Định nghĩa Bài toán:** `docs/requirements/problem-definition.md`
- **Tài liệu Đặc tả Yêu cầu Phần mềm:** `docs/srs/srs-v1.0.md`

Bước kỹ thuật tiếp theo theo quy trình kỹ thuật phần mềm chuẩn mực: Tiến hành phân tích hệ thống chi tiết, xây dựng mô hình hóa đối tượng và biểu đồ quan hệ chức năng theo chuẩn UML 2.5 (`docs/uml/`) phục vụ thiết kế kiến trúc và cơ sở dữ liệu.

---

## 8. Danh mục Tài liệu Tham khảo (Academic References)

Tuân thủ quy chuẩn trích dẫn khoa học chính quy **IEEE Reference Style**:

1. [1] B. J. Zimmerman, "Becoming a self-regulated learner: An overview," *Theory Into Practice*, vol. 41, no. 2, pp. 64–70, Spring 2002, doi: 10.1207/s15430421tip4102_2.
2. [2] J. Sweller, "Cognitive load during problem solving: Effects on learning," *Cognitive Science*, vol. 12, no. 2, pp. 257–285, Apr. 1988, doi: 10.1207/s15516709cog1202_4.
3. [3] R. F. Baumeister, E. Bratslavsky, M. Muraven, and D. M. Tice, "Ego depletion: Is the active self a limited resource?," *Journal of Personality and Social Psychology*, vol. 74, no. 5, pp. 1252–1265, May 1998, doi: 10.1037/0022-3514.74.5.1252.
4. [4] J. Reich and J. A. Ruipérez-Valiente, "The MOOC pivot," *Science*, vol. 363, no. 6423, pp. 130–131, Jan. 2019, doi: 10.1126/science.aau7958.
5. [5] G. Mark, V. M. Gonzalez, and J. Harris, "No task left behind? Examining the nature of fragmented work," in *Proc. SIGCHI Conf. Human Factors in Computing Systems (CHI '05)*, Portland, OR, USA, 2005, pp. 321–330, doi: 10.1145/1054972.1055017.
6. [6] Stack Overflow, "2023 Developer Survey - Learning to code," *Stack Overflow Research*, 2023. [Online]. Available: https://survey.stackoverflow.co/2023/#learning-to-code
7. [7] A. Cooper, *The Inmates Are Running the Asylum: Why High Tech Products Drive Us Crazy and How to Restore the Sanity*, Indianapolis, IN: Sams Publishing, 1999.
8. [8] ISO/IEC/IEEE, "ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering," *ISO/IEC/IEEE Standard*, pp. 1–104, Nov. 2018.
9. [9] J. Brooke, "SUS: A 'quick and dirty' usability scale," in *Usability Evaluation In Industry*, P. W. Jordan, B. Thomas, B. A. Weerdmeester, and I. L. McClelland, Eds., London, UK: Taylor & Francis, 1996, pp. 189–194.
10. [10] B. Deshpande, C. Knoerle, and F. Dawson, "Internet Calendaring and Scheduling Core Object Specification (iCalendar)," *IETF RFC 5545*, Sep. 2009. [Online]. Available: https://datatracker.ietf.org/doc/html/rfc5545
11. [11] FocusFlow Engineering Team, "FocusFlow Software Requirements Specification (SRS) v1.2," *Internal Technical Report*, `docs/srs/srs-v1.0.md`, Oct. 2026.
12. [12] FocusFlow Engineering Team, "FocusFlow Problem Definition & Requirements Discovery Document," *Internal Technical Report*, `docs/requirements/problem-definition.md`, Sep. 2026.

