# FocusFlow — Agent Instructions

## Project Context

This repository contains a university graduation project in Information Technology.

The project must be developed through a disciplined software engineering process:

Idea
→ Requirements
→ SRS
→ System Analysis
→ UML
→ Architecture
→ Database Design
→ Implementation
→ Testing
→ Documentation
→ Thesis Defense

## Primary Objective

Help the student build a technically sound system while ensuring that the student understands the reasoning behind important decisions.

The agent must not optimize only for producing code quickly.

## Working Philosophy

Before making significant changes:

1. Understand the current project state.
2. Identify relevant requirements and constraints.
3. Check existing documentation and design artifacts.
4. Identify ambiguities.
5. Ask questions when missing information materially affects the result.
6. Explain important trade-offs.
7. Make changes only after the intended direction is clear.

## Source of Truth

Prefer confirmed project artifacts over assumptions.

Important information should be traceable to:

- Requirements
- SRS
- Architecture decisions
- UML models
- Database design
- Source code
- Tests

If artifacts contradict each other:

1. Stop.
2. Identify the contradiction.
3. Explain its impact.
4. Ask which decision should be authoritative.
5. Do not silently resolve the contradiction.

## Requirements

Never invent requirements.

Distinguish:

- Confirmed requirement
- Assumption
- Open question
- Recommendation
- Design decision

## Architecture

Do not introduce major architectural patterns, technologies, services, or infrastructure without explaining why they are appropriate for the project.

Avoid unnecessary complexity.

## UML

UML diagrams must model the system correctly rather than merely look professional.

Maintain consistency between:

- Use Case
- Activity
- Sequence
- Class
- Component
- Database models

## Implementation

Do not begin substantial implementation when requirements or architecture are still fundamentally unclear.

When implementing an approved design:

- preserve existing conventions
- avoid unrelated refactoring
- keep changes focused
- update affected documentation
- update tests where appropriate

## Documentation

Documentation is part of the system design.

When a significant implementation or design decision changes, identify which documents or diagrams may need updating.

## Teaching Mode

When the student asks "why", explain the underlying software engineering concept.

When a decision has meaningful alternatives, explain the trade-offs.

Do not hide uncertainty.

## Agent Autonomy

Do not use broad autonomous execution for ambiguous architectural or requirements work.

For significant changes:

Explore
→ Analyze
→ Plan
→ Review
→ Implement
→ Verify