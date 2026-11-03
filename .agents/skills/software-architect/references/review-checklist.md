# Checklist rà soát kiến trúc (tự chạy trước khi giao)

## Động lực và yêu cầu
- [ ] Mục tiêu kinh doanh, người dùng, phạm vi hệ thống và ranh giới (cái gì ngoài phạm vi) được nêu rõ.
- [ ] Có 3–7 ASR, mỗi cái là scenario **đo được** (nguồn, kích thích, thành phần, môi trường, phản ứng, thước đo); số liệu chưa biết đã đánh dấu giả định.
- [ ] Ràng buộc cứng (pháp lý, ngân sách, thời hạn, công nghệ bắt buộc, kỹ năng đội, nơi lưu dữ liệu) được liệt kê.
- [ ] Có ước lượng năng lực (tải trung bình/đỉnh, dữ liệu, tăng trưởng) với giả định ghi rõ.
- [ ] Use case/miền nghiệp vụ có ý nghĩa kiến trúc đã được chọn và truy vết.

## Phương án và đánh đổi
- [ ] Có ≥ 2 phương án thực tế (kể cả "đơn giản nhất có thể"), không chỉ một đáp án.
- [ ] So sánh theo tiêu chí lấy từ ASR, kèm lập luận bằng lời, kiểm tra độ nhạy.
- [ ] Phương án khuyến nghị nêu rõ cái được, cái mất, rủi ro, và **điều kiện đổi hướng**.
- [ ] Phong cách kiến trúc được chọn theo ngữ cảnh (đội, miền, vận hành), không theo xu hướng; microservices chỉ khi có lý do đo được.

## Cấu trúc
- [ ] Phân rã theo ranh giới nghiệp vụ (bounded context/module), không theo tầng kỹ thuật thuần túy.
- [ ] Mỗi thành phần có trách nhiệm một câu, dữ liệu sở hữu, giao diện công khai, phụ thuộc; không phụ thuộc vòng.
- [ ] Ranh giới dữ liệu rõ: ai sở hữu gì, nguồn sự thật, cách chia sẻ; không CSDL chung xuyên đội/dịch vụ.
- [ ] Kiểu tích hợp (đồng bộ/bất đồng bộ/lô) chọn có lý do; mọi lời gọi từ xa có timeout và chiến lược lỗi.
- [ ] Giao dịch xuyên thành phần có chiến lược (saga/outbox/idempotency) hoặc đã thiết kế lại ranh giới.

## Cross-cutting
- [ ] Bảo mật: xác thực, phân quyền (kiểm tra phía máy chủ), bí mật, mã hóa, mô hình đe dọa, kiểm toán.
- [ ] Quan sát: log có cấu trúc + trace id, metric, trace, SLI/SLO, cảnh báo hành động được.
- [ ] Chịu lỗi: dự phòng, failover, backup/restore đã nêu và khớp RTO/RPO; giảm cấp có kiểm soát.
- [ ] Triển khai: CI/CD, hạ tầng dạng mã, chiến lược phát hành và rollback, quản lý cấu hình.
- [ ] Dữ liệu: sao lưu, lưu giữ, di chuyển schema, dữ liệu cá nhân, tuân thủ nơi lưu trữ.
- [ ] Chi phí ước tính ở nhiều mức tải; có cơ chế theo dõi.

## Tài liệu
- [ ] C4 Context và Container (và Component/Deployment khi cần) đúng quy ước: tiêu đề, loại, công nghệ, mô tả, nhãn quan hệ một chiều, chú giải.
- [ ] 2–4 kịch bản chính có sequence/dynamic diagram, gồm luồng lỗi.
- [ ] Mỗi quyết định lớn có ADR (bối cảnh, quyết định, phương án đã xét, hệ quả, điều kiện xem lại).
- [ ] Tên khớp giữa diagram, bảng thành phần, ADR; mã diagram đã render thử hoặc ghi rõ chưa kiểm tra.

## Đánh giá và lộ trình
- [ ] Mỗi ASR đã được đi qua trên kiến trúc; rủi ro, điểm nhạy cảm, điểm đánh đổi được liệt kê.
- [ ] Rủi ro lớn nhất có kế hoạch giải sớm (spike, thử tải) với chủ sở hữu và hạn.
- [ ] Có fitness function hoặc cách đo cho ASR chính.
- [ ] Lộ trình có walking skeleton, các đợt tăng trưởng, chiến lược migration (nếu có hệ cũ), đội sở hữu.
- [ ] Phần nào đã chứng minh, phần nào chỉ là giả định: được phân biệt rõ.

## Bàn giao
- [ ] Tóm tắt: giả định, quyết định quan trọng, rủi ro hàng đầu, câu hỏi mở cần xác nhận; nói rõ những gì chưa kiểm chứng (số liệu giả định, mã diagram chưa render).
