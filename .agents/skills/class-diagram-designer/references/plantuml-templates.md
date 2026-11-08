# PlantUML Templates

Các template dưới đây là điểm khởi đầu. Luôn kiểm tra cú pháp bằng renderer thực tế nếu tuyên bố đã validate. Stereotype DDD/Context là quy ước dự án và phải có legend.

## 1. Domain Overview Class Diagram

```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle
hide methods
hide stereotypes

package "Planning Context" <<BoundedContext>> {
  class Goal <<Entity>>
  class Roadmap <<Entity>>
  class Milestone <<Entity>>

  Goal "1" -- "0..*" Roadmap : defines
  Roadmap "1" -- "0..*" Milestone : contains
}

package "Execution Context" <<ProposedContext>> {
  class Task <<Entity>>
  class StudySession <<Entity>>

  StudySession "1" -- "0..*" Task : executes
}

note bottom
  Legend:
  <<Entity>>, <<BoundedContext>>, <<ProposedContext>> are project-defined stereotypes.
  Context status and multiplicities must be evidence-backed.
end note
@enduml
```

Chỉ dùng ví dụ class/relationship khi phù hợp với domain thực tế. Không sao chép ví dụ thành yêu cầu.

## 2. Detailed DDD Model with Aggregate

```plantuml
@startuml
skinparam packageStyle rectangle

package "Ordering Context" <<BoundedContext>> {
  class Order <<Entity>> <<AggregateRoot>> {
    +addItem(productId: ProductId, quantity: int)
    +confirm()
  }

  class OrderLine <<Entity>> <<AggregateMember>> {
    -quantity: int
  }

  class ShippingAddress <<ValueObject>> {
    -street: String
    -postalCode: String
  }

  class ProductId <<ValueObject>>

  Order "1" *-- "1..*" OrderLine : contains
  Order "1" *-- "1" ShippingAddress : uses
  OrderLine ..> ProductId : references by identity
}

note right of Order
  Aggregate invariant:
  Add only project-confirmed business rules here.
end note

note bottom
  Composition shown only if lifecycle/ownership semantics are confirmed.
  Aggregate stereotypes are project-defined DDD conventions.
end note
@enduml
```

Không mặc định mọi Aggregate member phải dùng Composition. Có thể dùng association và Aggregate Map nếu semantics lifecycle UML khác consistency boundary.

## 3. Association Class

```plantuml
@startuml
class Student
class Course
class Enrollment {
  enrolledAt: Date
  result: ResultStatus
}

Student "1" -- "0..*" Course : enrolls in
(Student, Course) .. Enrollment
@enduml
```

Xác nhận syntax theo phiên bản PlantUML hiện dùng. Nếu tool không hỗ trợ tốt, mô tả Enrollment như relationship classifier với note rõ ràng.

## 4. Software Design Class Diagram

```plantuml
@startuml
interface ScheduleRepository {
  +findById(id: ScheduleId): Schedule
  +save(schedule: Schedule): void
}

class ScheduleApplicationService {
  +approveProposal(proposalId: ProposalId): void
}

class Schedule {
  -status: ScheduleStatus
  +approve(): void
}

ScheduleApplicationService ..> ScheduleRepository : uses
ScheduleApplicationService ..> Schedule : coordinates
@enduml
```

Đây là design-level illustration; không đưa application service/repository vào Domain Overview theo mặc định.

## 5. Context Map (minh họa tự định nghĩa)

```plantuml
@startuml
rectangle "Planning Context" as Planning
rectangle "Execution Context" as Execution
rectangle "Calendar Integration Context" as Calendar

Planning --> Execution : published plan / contract
Execution --> Calendar : request calendar sync
@enduml
```

Đây là sơ đồ tích hợp Context ở mức khái niệm, không phải UML Class Diagram và không đại diện đầy đủ mọi pattern DDD. Thêm legend giải thích upstream/downstream, contract, ACL hoặc pattern khác khi đã xác nhận.

## 6. Quy tắc naming và rendering

- Dùng tên class số ít (`Task`, không `Tasks`).
- Role name mô tả vai trò ở đầu association khi hữu ích.
- Association label dùng động từ nghiệp vụ.
- Tránh đường nối chéo; dùng package và diagram con.
- Tên package/Context không quá dài; giữ consistent language.
- Không đặt database column name trong domain diagram.
- Không dùng màu hoặc stereotype để ngụ ý trạng thái CONFIRMED nếu legend không định nghĩa.
- Nếu có nhiều bản PlantUML/Mermaid, một bản phải được chỉ định làm source of truth.
