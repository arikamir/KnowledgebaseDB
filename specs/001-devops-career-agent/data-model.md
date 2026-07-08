# Data Model: DevOps Career Agent

## EmployeeProfile

- **Purpose**: Captures the employee's current role, experience, goals, and
  constraints.
- **Fields**:
  - `id`
  - `role`
  - `experience_level`
  - `target_role`
  - `target_specializations`
  - `available_time_per_week`
  - `learning_preferences`
  - `constraints`
  - `created_at`
  - `updated_at`
- **Validation rules**:
  - `role` and `experience_level` must be present for a meaningful roadmap.
  - `available_time_per_week` must be non-negative when supplied.

## SkillArea

- **Purpose**: Describes a DevOps topic the assistant can guide on.
- **Fields**:
  - `id`
  - `name`
  - `category`
  - `description`
  - `related_skills`
  - `priority_level`
  - `is_active`
- **Validation rules**:
  - `name` must be unique within the catalog.
  - Inactive skills must not appear in new recommendations unless explicitly
    requested.

## CareerRoadmap

- **Purpose**: Stores the personalized growth plan for an employee.
- **Fields**:
  - `id`
  - `employee_profile_id`
  - `goal_summary`
  - `current_focus`
  - `milestones`
  - `next_actions`
  - `status`
  - `created_at`
  - `updated_at`
- **Relationships**:
  - Belongs to one `EmployeeProfile`.
  - Contains many actionable milestones.
- **Validation rules**:
  - Must include at least one immediate next action and one longer-term step.

## RoadmapStep

- **Purpose**: Represents a single step in the career roadmap.
- **Fields**:
  - `id`
  - `roadmap_id`
  - `title`
  - `description`
  - `skill_area_id`
  - `priority`
  - `time_horizon`
  - `completion_state`
- **Validation rules**:
  - `priority` must be ordered from highest to lowest within the roadmap.
  - `completion_state` must support progress updates without recreating the plan.

## ProgressCheckIn

- **Purpose**: Captures later updates from the employee and how the roadmap
  changes.
- **Fields**:
  - `id`
  - `employee_profile_id`
  - `roadmap_id`
  - `notes`
  - `completed_steps`
  - `new_goals`
  - `updated_recommendations`
  - `created_at`
- **Validation rules**:
  - A check-in must reference the employee and the roadmap it updates.

## Relationships Summary

- One employee profile can have many roadmaps over time.
- Each roadmap can contain many steps.
- Each roadmap step can reference one primary skill area.
- Progress check-ins update the active roadmap and preserve the previous plan
  history.
