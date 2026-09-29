# Documentation Rules

## General

Project documentation must be:

- precise
- consistent
- traceable
- reviewable
- understandable by a software engineering student

Avoid unnecessary verbosity.

Do not generate filler content.

---

## Requirements

Every confirmed functional requirement should have:

- unique ID
- clear description
- relevant actor/user
- expected system behavior
- appropriate acceptance criteria when applicable

Requirements must be testable whenever practical.

---

## Decisions

Important technical decisions should record:

- Context
- Problem
- Alternatives
- Decision
- Rationale
- Consequences

Do not rewrite history to make a decision appear obvious after the fact.

---

## Changes

When changing an important requirement or architectural decision:

Identify affected:

- SRS sections
- Use Cases
- UML diagrams
- Database
- APIs
- Source code
- Tests
- Documentation

---

## Source of Truth

Prefer existing project artifacts over assumptions.

When two project documents disagree:

1. Identify the conflict.
2. Report it.
3. Ask which artifact should be authoritative.
4. Do not silently choose one.

---

## Academic Writing

Use precise technical terminology.

Separate:

- objective facts
- project decisions
- assumptions
- recommendations
- limitations

Do not exaggerate project capabilities or results.
