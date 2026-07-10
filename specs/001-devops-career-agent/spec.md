# Feature Specification: DevOps Career Agent

**Feature Branch**: `001-devops-career-agent`  
**Created**: 2026-07-08  
**Status**: Draft  
**Input**: User description: "create an AI agent that will assist an employee with advancing his or her career path in DevOps, the main technologies to focus on are Jenkins, Azure DevOps and GitLab CI for CICD orchestration, Kubernetes, ArgoCD, HELM, DotNet, MSI and Advanced Installer, Windows administration, Opeshift, Linux, Docker, Docker-Compose, managing certificates, managing secrets using hashicorp vault, Ansible, Terraform, VMWare, AWS, MLOPS, SecOps and more can be added in the future"

## Clarifications

### Session 2026-07-08

- Q: How should pilot success for immediate next-step identification and relevance be measured? -> A: Short post-session survey: next-step yes/no and relevance 1-5.
- Q: What security and data boundary applies to the initial proof of concept? -> A: Non-production PoC; exclude regulated HR records, performance-review data, secrets, and production employee datasets; defer security/privacy hardening.
- Q: What must each roadmap recommendation include to be considered practical? -> A: Skill area, experience-level fit, time horizon, concrete next action, and reason it matters.
- Q: How should unsupported or not-yet-covered skill topics be handled? -> A: State the topic is not covered yet, offer the closest supported DevOps topics, and avoid inventing detailed guidance.
- Q: How should prior roadmap and progress context be handled across sessions? -> A: Retain prior roadmaps, progress check-ins, and guidance across sessions.
- Q: What identity should be used to persist roadmap and progress history across sessions? -> A: Use the host application's existing employee identity as the stable key.
- Q: How many clarifying questions are allowed before the first roadmap is produced? -> A: Up to 3 clarifying questions.
- Q: What should happen if the employee still has not provided enough context after the clarifying-question limit? -> A: Generate a best-effort roadmap and state the assumptions explicitly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Career Roadmap Creation (Priority: P1)

An employee can describe their current experience, target role, and available
time, and receive a personalized DevOps career roadmap with clear next steps.

**Why this priority**: The primary value of the feature is turning an ambiguous
career goal into an actionable plan.

**Independent Test**: An employee can complete a guided conversation and
receive a roadmap that they can follow without needing another story.

**Acceptance Scenarios**:

1. **Given** an employee with a broad DevOps goal, **When** they share current
   experience and target direction, **Then** they receive a prioritized roadmap
   with immediate, near-term, and longer-term steps.
2. **Given** an employee with limited background information, **When** they
   answer a few follow-up questions, **Then** the roadmap reflects their current
   level and learning pace.

---

### User Story 2 - Skill-Specific Guidance (Priority: P2)

An employee can ask for guidance on a specific DevOps topic and receive
tailored recommendations, practice ideas, and common pitfalls for that topic.

**Why this priority**: Employees often need help with one skill area at a time
before they can act on a broader career plan.

**Independent Test**: An employee can ask about a single topic and get a
useful answer without first creating a full roadmap.

**Acceptance Scenarios**:

1. **Given** an employee asks about Kubernetes, GitOps, CI/CD, secrets, cloud,
   or automation, **When** they request help, **Then** they receive topic-
   specific guidance that matches their stated level.
2. **Given** an employee asks about a newer or less common topic, **When** the
   topic is recognized, **Then** they receive a useful answer even if the topic
   was added later.

---

### User Story 3 - Progress Review and Adaptation (Priority: P3)

An employee can review their progress over time and adjust their career plan as
their interests, current role, or target technologies change.

**Why this priority**: Career growth is iterative, so the assistant must adapt
as the employee gains experience.

**Independent Test**: An employee can return later, review prior guidance, and
get an updated plan based on new inputs.

**Acceptance Scenarios**:

1. **Given** an employee has completed some roadmap steps, **When** they check
   in with updated progress, **Then** the next recommendations reflect what is
   already done.
2. **Given** an employee changes target technologies or role direction, **When**
   they update their goals, **Then** the career plan is revised accordingly.

---

### Edge Cases

- An employee has no clear target role and only a general desire to grow in
  DevOps.
- An employee is already experienced in one area but needs a pivot to a
  different specialization.
- An employee requests guidance on a topic not yet covered by the assistant;
  the assistant states the topic is not covered yet, offers the closest
  supported DevOps topics, and avoids inventing detailed guidance.
- An employee wants advice that depends on local policy, certifications, or
  internal career ladders; the assistant gives general career guidance, states
  that organization-specific rules are out of scope, and points to the
  appropriate internal source.
- The host application cannot provide a stable employee identity, or the
  identity changes over time; the assistant treats the session as a fresh
  context until a stable identity is available and does not merge prior
  roadmap history into the new identity.
- A request mixes career growth guidance with performance management or HR
  decisions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST collect enough context to understand the
  employee's current role, experience level, target direction, and learning
  constraints.
- **FR-002**: The system MUST generate a personalized DevOps career roadmap
  with prioritized next steps.
- **FR-003**: The system MUST provide topic-specific guidance for core DevOps
  domains including CI/CD orchestration, containers, GitOps, infrastructure
  as code, cloud platforms, operating systems, certificates, secrets, and
  automation.
- **FR-004**: The system MUST allow the employee to revisit and update the
  plan as their progress or goals change.
- **FR-005**: The system MUST distinguish career guidance from formal HR or
  performance decisions and avoid presenting itself as an authoritative HR
  system.
- **FR-006**: The system MUST support adding new skill areas in the future
  without requiring the core career-guidance flow to change.
- **FR-007**: The system MUST produce recommendations that are practical,
  role-relevant, and appropriate to the employee's stated experience level.
- **FR-008**: Each roadmap recommendation MUST include a skill area, experience-
  level fit, time horizon, concrete next action, and reason the step matters.
- **FR-009**: For unsupported skill topics, the system MUST state the topic is
  not covered yet, offer the closest supported DevOps topics, and avoid
  inventing detailed guidance.
- **FR-010**: If sufficient context is still missing after the allowed
  clarifying questions, the system MUST produce a best-effort roadmap and
  explicitly state the assumptions used.

### Key Entities *(include if feature involves data)*

- **Employee Profile**: The employee's current role, experience, interests,
  goals, and constraints.
- **Career Roadmap**: A prioritized sequence of milestones and next actions
  tailored to the employee. Each recommendation includes a skill area,
  experience-level fit, time horizon, concrete next action, and reason it
  matters.
- **Skill Area**: A DevOps topic such as CI/CD, Kubernetes, GitOps, cloud,
  security, automation, or platform operations.
- **Progress Check-In**: A later update showing completed steps, new goals, and
  revised recommendations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An employee can receive an initial career roadmap within a
  single guided session after no more than 3 clarifying questions.
- **SC-002**: At least 80% of pilot users answer yes in a short post-session
  survey when asked whether they can identify one immediate next step after
  using the assistant.
- **SC-003**: At least 85% of pilot users rate the session guidance 4 or 5 on a
  1-5 post-session relevance scale for their current role or target role.
- **SC-004**: Employees can revisit the assistant and get an updated plan that
  reflects new goals or completed work without restarting from scratch.
- **SC-005**: New topic areas can be added to the guidance scope and made
  available in future sessions without changing the core user experience.
- **SC-006**: During the initial internal pilot, initial career-roadmap
  responses complete within 30 seconds p95.
- **SC-007**: During the initial internal pilot, topic-specific guidance
  responses complete within 10 seconds p95.
- **SC-008**: The initial internal pilot supports up to 10 concurrent
  employees.

## Assumptions

- The primary audience is employees who want to grow into stronger DevOps,
  platform engineering, or related operational roles.
- The assistant is for guidance and planning, not for formal HR decisions or
  employee evaluation.
- The organization wants coverage across the listed DevOps domains and may add
  more topics later.
- Recommendations may include learning, hands-on practice, and portfolio-style
  growth activities appropriate to the employee's current level.
- The assistant should remain useful even when the employee's starting point is
  vague or incomplete.
- The assistant retains prior roadmaps, progress check-ins, and guidance across
  sessions so returning employees can continue from where they left off.
- The assistant uses the host application's existing employee identity as the
  stable key for stored roadmaps and progress history.
- Initial proof-of-concept use is non-production only. It excludes regulated HR
  records, performance-review data, secrets, and production employee datasets;
  security/privacy hardening, retention controls, and access controls are
  deferred until production readiness.
