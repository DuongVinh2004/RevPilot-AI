# Task packs and execution policy

Task hierarchy is `INITIATIVE -> PHASE -> EPIC -> FEATURE -> MICRO-TASK`. Only one-file MICRO-TASK packets may enter `execution/EXECUTOR-QUEUE.md`, and only after their governing specifications/ADRs are accepted and their readiness score meets the required threshold.

Use `tasks/TASK-TEMPLATE.md`. The canonical phases are `PHASE-00` through `PHASE-08`. Stage A micro-tasks complete specifications. Stage B implementation micro-tasks are generated afterward with exact repository paths and symbols. Implementation code must not begin before Phase 00 exit.

`tasks/PHASE-00/TASKS.md` is retained as a legacy planning record. Its broad objects are superseded EPICs and must never be sent directly to Antigravity.
