# UML 2 Notation — Class Diagram

## 1. Chuẩn tham chiếu

Baseline notation của skill là OMG UML 2.5.1. Khi cần quyết định ngữ nghĩa UML, ưu tiên specification chính thức của OMG thay vì bài blog hoặc notation của công cụ. Một số stereotype dùng trong DDD là quy ước dự án, không tự động thuộc UML standard profile.

## 2. Classifier và class compartment

Class diagram có thể hiển thị nhiều loại classifier/phần tử như Class, Interface, DataType và Enumeration; không phải mọi phần tử đều là Class.

Class rectangle có thể có ba compartment:

1. Tên classifier.
2. Attributes.
3. Operations.

Compartment attribute/operation có thể bỏ trống hoặc ẩn tùy mục đích diagram.

Ví dụ:

```text
+------------------------------+
|          LearningGoal        |
+------------------------------+
| - title : String             |
| - targetDate : LocalDate     |
| / isOverdue : Boolean        |
+------------------------------+
| + complete() : void          |
| + reschedule(date: Date)     |
+------------------------------+
```

Tên class/interface/type phải nhất quán với language convention của deliverable.

## 3. Attribute và operation syntax

Syntax trình bày phổ biến:

```text
[visibility] name : Type [multiplicity] = defaultValue
[visibility] operationName(parameterName : Type, ...) : ReturnType
```

- Attribute multiplicity có thể biểu diễn collection/cardinality.
- Operation parameter có thể có direction (`in`, `out`, `inout`, `return`) khi cần mô hình hóa chi tiết.
- Return type có thể được lược bỏ nếu không liên quan đến mục tiêu.
- Không thêm mọi parameter hoặc implementation type vào Domain Overview.

## 4. Visibility

| Ký hiệu | Ý nghĩa |
|---|---|
| `+` | public |
| `-` | private |
| `#` | protected |
| `~` | package |

Visibility marker có thể được lược bỏ trong diagram. Không bắt buộc hiển thị visibility trong Domain Overview hoặc Detailed Domain Model nếu không phục vụ mục đích. Không diễn giải việc ẩn ký hiệu là visibility “chưa được định nghĩa”.

Static member thường được gạch chân theo notation UML; abstract classifier/operation thường được biểu diễn bằng chữ nghiêng hoặc `{abstract}` theo công cụ/notation.

## 5. Relationships

### 5.1. Generalization (kế thừa)

- Nét liền, tam giác rỗng hướng về general/superclass.
- Chỉ dùng khi subclass thực sự là một loại của superclass và có thể thay thế hợp lệ trong ngữ cảnh model.
- Không dùng inheritance chỉ để tái sử dụng vài field hoặc tránh lặp code.

### 5.2. Interface realization

- Nét đứt, tam giác rỗng hướng về interface.
- Dùng khi classifier thực hiện contract của interface.
- Trong Domain Overview, chỉ hiển thị interface nếu có giá trị nghiệp vụ/kiến trúc ở mức tổng quan.

### 5.3. Association

- Nét liền giữa classifier.
- Biểu diễn quan hệ cấu trúc giữa instances.
- Có thể có association name, role name, multiplicity và navigability.
- Association không tự động cho biết object reference cụ thể trong code; đó là một quyết định implementation.

### 5.4. Navigability

- Navigability chỉ hướng điều hướng trong model.
- Dùng mũi tên open arrow ở association end theo notation công cụ.
- Không đồng nhất navigability với business ownership, lifecycle hoặc Aggregate membership.
- Nếu không có yêu cầu, không cần vẽ arrow hai chiều chỉ vì database có hai FK/navigation properties.

### 5.5. Dependency

- Nét đứt, open arrow từ client/dependent đến supplier.
- Thường dùng cho quan hệ sử dụng/ phụ thuộc không được mô hình như association cấu trúc lâu dài.
- Không dùng dependency arrow đến enum chỉ để thể hiện enum là type của attribute.
- Không dùng Dependency thay cho relationship nghiệp vụ trong Domain Overview.

### 5.6. Shared Aggregation

- Hình thoi rỗng ở đầu whole.
- UML định nghĩa aggregation kind `shared`, nhưng ý nghĩa chính xác phụ thuộc domain/application; không nên áp đặt một semantics ownership/lifecycle phổ quát.
- Chỉ dùng khi người đọc thật sự cần phân biệt shared whole-part semantics và dự án có quy ước rõ.
- Nếu không giải thích được vì sao Association thông thường không đủ, không dùng shared aggregation.

### 5.7. Composition

- Hình thoi đặc ở đầu composite/whole.
- Là dạng composite ownership mạnh. Một part có thể thuộc tối đa một composite tại một thời điểm.
- Quan hệ có lifecycle semantics; hãy kiểm tra creation, removal, transfer và deletion behavior.
- Không có quy tắc chung rằng multiplicity ở đầu Whole luôn phải là `1`; xác định theo domain lifecycle.
- Không dùng Composition chỉ vì “A chứa danh sách B”, “A có FK đến B”, hoặc “B thường được tạo cùng A”.
- Composition trong UML không đồng nghĩa với Aggregate membership trong DDD.

### 5.8. Association Class

- Một classifier vừa biểu diễn association vừa có features riêng.
- Dùng khi data/behavior thuộc về chính relationship.
- Có thể cần Entity liên kết nếu relationship có identity và lifecycle riêng.
- PlantUML/Mermaid có thể không hiển thị giống nhau; khi notation không biểu đạt đủ, dùng PlantUML hoặc ghi chú rõ.

## 6. Multiplicity

Các ký pháp thường gặp:

| Ký hiệu | Ý nghĩa |
|---|---|
| `1` | đúng một |
| `0..1` | không hoặc một |
| `*` / `0..*` | không hoặc nhiều |
| `1..*` | ít nhất một |
| `2..5` | từ hai đến năm |

Skill yêu cầu cố gắng ghi multiplicity ở cả hai đầu để nâng chất lượng review; đây là quy ước modeling của skill, không được tuyên bố nhầm là UML bắt buộc trong mọi trường hợp. Nếu chưa có căn cứ, dùng `TBD` trong registry hoặc ghi rõ multiplicity chưa xác định; không bịa số để làm sơ đồ trông hoàn chỉnh.

## 7. Constraints, notes và stereotypes

- Constraint có thể ghi trong `{...}` hoặc UML Note/Constraint tùy tool.
- Stereotype là phần mở rộng của UML Profile; nhãn như `«Entity»`, `«ValueObject»`, `«AggregateRoot»`, `«DomainService»`, `«BoundedContext»` cần được xem là project-defined nếu không có profile được chỉ rõ.
- Không trình bày stereotype DDD như một ký hiệu metamodel mặc định của UML.
- Dùng legend giải thích stereotype và semantics trong sơ đồ.

## 8. Derived properties và immutable values

- Derived property dùng `/` trước tên, ví dụ `/balance`.
- Dấu `+` public không có nghĩa immutable.
- Immutability nên được ghi bằng constraint/note như `{readOnly}` hoặc mô tả trong model specification nếu đó là rule quan trọng.
- Không biểu diễn computed field như field có thể mutate nếu không giải thích cache/materialization và source of truth.

## 9. Công cụ và giới hạn notation

### PlantUML

- Thường biểu diễn class, association, generalization, dependency, interface và note tốt hơn cho text-based modeling.
- Association class có syntax riêng, cần kiểm tra renderer thực tế.
- Stereotype tùy chỉnh cần legend.

### Mermaid classDiagram

- Phù hợp preview nhanh trong Markdown.
- Không phải mọi UML metamodel/relationship nuance đều được biểu diễn đầy đủ như UML tool chuyên dụng.
- Khi Mermaid không biểu đạt rõ association class, qualifier, n-ary association hoặc constraint quan trọng, dùng PlantUML hoặc tạo note/register bổ sung.
- Không được âm thầm thay association class bằng class thông thường nếu làm sai semantics; ghi rõ đây là cách biểu diễn thay thế.
