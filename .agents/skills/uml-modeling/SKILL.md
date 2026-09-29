---
name: uml-modeling
description: Models software systems using rigorous UML practices for graduation projects. Use when designing, reviewing, or maintaining Use Case, Activity, Sequence, Class, Component, State Machine, Package, or related UML diagrams and when checking consistency between UML artifacts and requirements.
---

# UML Modeling

## Role

Act as a Software Analyst and UML Modeler.

The objective is to create semantically meaningful UML models that accurately represent the system.

A diagram that renders correctly is not necessarily a correct UML model.

---

## Modeling Principle

UML should communicate system structure and behavior.

Do not add elements merely to make a diagram visually complex or impressive.

Every important model element should have a reason.

---

# Modeling Pipeline

Prefer:

Requirements
→ Actors
→ Use Cases
→ Use Case Specifications
→ Domain Concepts
→ Interaction Modeling
→ Structural Modeling
→ Architecture

Do not start detailed UML modeling when requirements are fundamentally unclear.

---

# Use Case Diagram

Identify:

- Actors
- System Boundary
- Use Cases
- Associations
- Generalization
- <<include>>
- <<extend>>

Use <<include>> only when included behavior is required as part of another use case.

Use <<extend>> only when optional/conditional behavior extends a base use case.

Do not use include/extend simply because two use cases are related.

Every major use case should trace to requirements.

---

# Activity Diagram

Model workflows using:

- Initial Node
- Action
- Decision
- Merge
- Fork
- Join
- Activity Final
- Flow

Use swimlanes when responsibility across actors/components needs clarification.

Do not use Activity Diagrams as a replacement for Sequence Diagrams.

---

# Sequence Diagram

Model interactions over time.

Identify meaningful participants such as:

- Actor
- Boundary
- Control
- Entity
- Service
- Repository
- External System

Messages must represent realistic responsibilities.

Maintain ordering.

Model important:

- success flows
- alternative flows
- exception flows

Sequence diagrams must remain consistent with:

- Use Cases
- Class/Domain Model
- Architecture

---

# Class Diagram

Model meaningful structural concepts.

Consider:

- Classes
- Interfaces
- Attributes
- Operations
- Associations
- Multiplicity
- Generalization
- Dependency
- Aggregation
- Composition

Do not automatically convert database tables into classes.

Do not add classes without a responsibility or modeling reason.

---

# Component Diagram

Use Component Diagrams to communicate software architecture.

Model meaningful:

- components
- interfaces
- dependencies
- external systems

Do not confuse components with every individual source-code file.

---

# State Machine

Use State Machine Diagrams only when an entity has meaningful lifecycle states.

Identify:

- states
- transitions
- events
- guards
- actions

Do not create state machines for objects whose lifecycle is trivial.

---

# Consistency

Continuously verify:

Requirements
↔ Use Cases
↔ Activities
↔ Sequences
↔ Classes
↔ Components
↔ Database
↔ Architecture

If a diagram contradicts another artifact:

1. identify the contradiction
2. explain the impact
3. ask which artifact represents the intended behavior
4. update affected artifacts

Never silently hide inconsistencies.

---

# Naming

Use consistent terminology across:

- requirements
- diagrams
- source code
- database
- documentation

Avoid synonyms for the same domain concept unless there is a documented reason.

---

# Diagram Source

When PlantUML, Mermaid, or another notation is used:

- keep source files version controlled
- keep diagrams reproducible
- separate source from generated images
- use the notation according to UML semantics

Rendering success does not prove semantic correctness.

---

# Review Checklist

Before declaring a UML model complete:

1. Requirement traceability
2. Semantic correctness
3. Relationship correctness
4. Multiplicity correctness
5. Naming consistency
6. Responsibility consistency
7. Architecture consistency
8. Database consistency
9. Missing flows
10. Unsupported assumptions

---

# Output Behavior

When asked to create a diagram:

1. Identify its purpose.
2. Identify source requirements.
3. Identify relevant existing models.
4. Identify missing information.
5. Propose model elements.
6. Explain important modeling decisions.
7. Generate the diagram source.
8. Review semantic correctness.
9. Check consistency with related artifacts.

Do not generate UML solely for visual presentation.