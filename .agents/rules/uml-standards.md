# UML Modeling Rules

## General

UML diagrams must represent meaningful system models.

Do not create relationships merely to make a diagram visually complete.

Correct modeling is more important than visual appearance.

Use UML concepts according to the UML specification.

PlantUML is a diagram source/rendering tool, not the UML specification itself.

---

## Use Case Diagram

Use Case Diagrams must clearly identify:

- Actors
- System boundary
- Use Cases
- Associations
- Generalization where justified
- <<include>> where justified
- <<extend>> where justified

Do not use <<include>> or <<extend>> merely because two use cases are related.

Every important use case should trace back to one or more requirements.

---

## Activity Diagram

Use Activity Diagrams to model workflows and control/object flows.

Use:

- Initial nodes
- Actions
- Decision nodes
- Merge nodes
- Fork/join where parallelism is meaningful
- Final nodes

Do not use Activity Diagrams as a replacement for Sequence Diagrams.

---

## Sequence Diagram

Sequence Diagrams must represent interactions over time.

Identify appropriate:

- Actors
- Boundary objects
- Control objects
- Entity objects
- Services
- Repositories
- External systems

Messages must reflect realistic responsibilities and ordering.

Sequence Diagrams should be derived from approved use case flows and remain consistent with the architecture and class/domain model.

Include important alternative and exception flows when relevant.

---

## Class Diagram

Class Diagrams must represent meaningful structural/domain concepts.

Consider:

- Classes
- Attributes
- Operations
- Associations
- Multiplicity
- Generalization
- Dependency
- Aggregation
- Composition
- Interfaces

Do not automatically convert database tables into classes.

Do not add classes without a responsibility or modeling reason.

---

## Database / ERD

Database diagrams are data/persistence models.

Do not treat ERD and Class Diagram as identical artifacts.

Validate:

- Primary keys
- Foreign keys
- Cardinality
- Optionality
- Constraints
- Uniqueness
- Normalization
- Indexing requirements

Database design must remain traceable to domain and business requirements.

---

## Diagram Review

Before considering a diagram complete:

1. Check semantic correctness.
2. Check relationship correctness.
3. Check naming consistency.
4. Check traceability.
5. Check consistency with related diagrams.
6. Identify unsupported assumptions.

Do not claim a diagram is UML-correct merely because it renders successfully.
