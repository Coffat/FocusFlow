# Sources and Reading Notes

## 1. UML notation

- **OMG — Unified Modeling Language (UML) 2.5.1**  
  https://www.omg.org/spec/UML  
  Nguồn normative chính thức cho UML 2.5.1, bao gồm abstract syntax và semantics. Dùng để xác minh classifier, property, association, aggregation kind, multiplicity, visibility và notation. Không dùng bài blog làm nguồn thay thế cho ngữ nghĩa chuẩn khi có tranh chấp.

## 2. DDD domain model và tactical patterns

- **Microsoft Learn — Designing a microservice domain model**  
  https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/microservice-domain-model  
  Tham khảo về Entity behavior, Value Object, Aggregate và Aggregate Root. Lưu ý: một số hướng dẫn trong bài được trình bày theo ví dụ .NET/EF Core; không biến implementation choice đó thành quy tắc UML phổ quát.

- **Microsoft Learn — Design a DDD-oriented microservice**  
  https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice  
  Tham khảo về cách đặt Domain Model trong kiến trúc nhiều layer và vai trò của Aggregate Root.

- **Vaughn Vernon — Rule: Reference Other Aggregates by Identity**  
  https://www.informit.com/articles/article.aspx?p=2020371&seqNum=+4  
  Tham khảo nguyên tắc tham chiếu Aggregate khác bằng identity và giữ ranh giới consistency. Đây là guidance DDD, không phải cú pháp/điều khoản UML.

## 3. Domain analysis và Bounded Context

- **Microsoft Azure Architecture Center — Use Domain Analysis to Model Microservices**  
  https://learn.microsoft.com/en-us/azure/architecture/microservices/model/domain-analysis  
  Tham khảo phân tích domain, Bounded Context và Context Map. Nguồn nhấn mạnh rằng cùng một khái niệm ngoài đời có thể có model khác nhau ở các context khác nhau.

## 4. Cách sử dụng nguồn

- Ưu tiên OMG cho câu hỏi UML notation/semantics.
- Dùng DDD references để định hướng domain modeling, nhưng luôn kiểm chứng với business requirements của dự án.
- Microsoft Learn là nguồn hướng dẫn thực hành, không phải tiêu chuẩn DDD chính thức.
- Vaughn Vernon là nguồn chuyên sâu về thiết kế Aggregate; các nguyên tắc cần được áp dụng theo ngữ cảnh, không máy móc.
- Không lấy một ví dụ trong tài liệu tham khảo làm yêu cầu của dự án đang phân tích.
