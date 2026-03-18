# AI Harness Engineering

How to manage AI coding tools in production — lessons from 3,277 sessions and 1,000+ hours with Claude Code.

---

## The Problem

AI coding assistants are powerful but unreliable at scale. They lose context, drift from intent, hallucinate solutions, and forget constraints. If you treat them as autonomous agents and walk away, you get code that compiles but does the wrong thing.

The solution is not to avoid AI tools. It is to build a harness around them.

---

## CLAUDE.md Constitutions

Every repository has a `CLAUDE.md` file at its root that acts as a constitution — a set of rules the AI must follow when working in that codebase. This is loaded automatically at the start of every session.

A constitution typically includes:

```markdown
# Project Name

## What This Project Does
One paragraph. No ambiguity about scope.

## Architecture
Where code lives. What talks to what. What must never change.

## Routing Rules
Which module handles which responsibility. Prevents the AI
from putting weather code in the sportsbook module.

## Safety Rules
- Never deploy .env files
- Never modify production tracking files directly
- Every bug fix ships a regression test
- Minimum warning-level for caught exceptions

## Anti-Patterns
Named failure modes with descriptions. The AI reads these
and avoids them. Without this section, it will reinvent
every mistake you have already fixed.

## Deploy Patterns
Exact commands. No guessing. The AI copies and runs these.
```

**14 constitutions** across 6 repositories. Each is specific to its codebase. Generic rules go in the root-level file; project-specific rules go in project-level files.

**Why not a third-party governance tool?** Production trading data flows through these sessions. The fewer external tools touching that data, the better. A markdown file in the repo is auditable, version-controlled, and has zero attack surface.

---

## Context Compaction Survival

Claude Code sessions have context limits. When a session gets long, earlier messages are compressed (compacted). This is the single biggest source of subtle bugs in AI-assisted development.

**What happens during compaction:**
- The AI loses specific details from early in the conversation
- It retains general intent but may drift on implementation details
- It may re-introduce patterns you explicitly told it to avoid
- It may forget that a function was already modified and modify it again differently

**How to survive it:**

### Plan Documents as Session Bridges
Before any complex task, write a plan document to disk:

```markdown
# Plan: Feature X

## Goal
What we are building and why.

## Approach
Step-by-step implementation plan.

## Files to Modify
Explicit list. The AI re-reads this after compaction.

## Constraints
Things that must not change. Safety rails.

## Progress
- [x] Step 1 (completed)
- [ ] Step 2 (next)
- [ ] Step 3
```

After compaction, the AI reads the plan file and re-anchors. Without this, it starts improvising.

### Batch Execution (3-4 Tasks Per Checkpoint)
Do not give the AI 15 tasks and hope it remembers all of them. Break work into batches of 3-4. Complete a batch. Verify. Checkpoint. Start the next batch.

### Self-Contained Subagent Prompts
When dispatching work to subagents (parallel AI workers), give each one a complete, self-contained prompt. Do not assume the subagent knows anything about the parent session. Include:
- What to do
- Which files to read
- What constraints apply
- What output format to use

### Post-Compaction Verification
After any compaction event, verify:
1. Re-read the plan document
2. Check that current work matches the plan
3. Verify you have not drifted from the original request
4. If unsure about any detail, re-read the source file

---

## Persistent Memory

100+ memory files organized by type:

| Type | Purpose | Example |
|------|---------|---------|
| User | Who the human is, their preferences | "Prefers terse output, no summaries" |
| Feedback | Corrections to AI behavior | "Don't mock the database in integration tests" |
| Project | Ongoing work context | "Merge freeze starts Thursday" |
| Reference | Pointers to external systems | "Bugs tracked in Linear project INGEST" |

Memory files have YAML frontmatter with name, description, and type. An index file (`MEMORY.md`) is loaded at session start so the AI knows what memories exist without reading all of them.

**Key insight:** Memory is for things that cannot be derived from the code. If it is in the codebase, the AI can read it. Memory is for preferences, corrections, context, and pointers.

---

## Data Ontology

Inspired by Palantir's approach to entity relationships. Every data object in the system has a clear owner, schema, and lifecycle:

- **Who writes it?** Only one module may write to a given tracking file.
- **Who reads it?** Any module may read, but reads are explicit (no implicit dependencies).
- **How fresh must it be?** Every file has a staleness threshold monitored by the Doctor.
- **What happens when it is stale?** Defined escalation: alert, degrade gracefully, or halt trading.

This prevents the most common data bug in multi-agent systems: two agents writing to the same file with different assumptions about schema or timing.

---

## Quality Filters

### The Write + Monitor Principle
Every new data path requires three things before it is considered "done":
1. **Freshness check** in a Doctor health cycle
2. **Outcome resolution loop** that closes the feedback loop
3. **Heartbeat monitoring** that detects when the path goes silent

### Budget-Aware LLM Routing
4 model tiers with different cost/capability tradeoffs. Each department has a spend budget. The orchestrator routes requests to the cheapest model that can handle the task. Complex reasoning gets the expensive model. Simple formatting gets the cheap one.

### Anti-Blindspot Protocol
Before any pick or trade recommendation:
1. Check data completeness (reject if critical fields missing)
2. Check data freshness (reject if stale)
3. Check grade gates (minimum confidence threshold)
4. Check for known anti-patterns in the data

---

## What I Would Do Differently

1. **Start with the constitution.** I wrote mine after accumulating 50+ sessions of ad-hoc corrections. Should have been day one.
2. **Name anti-patterns immediately.** The moment a bug has a pattern, name it and write the guard. Unnamed bugs repeat within 48 hours.
3. **Batch from the start.** My early sessions were marathons that drifted badly. Short batches with verification produce better code.
4. **Memory is not a diary.** Early memory files were verbose narratives. Useful memory is terse, specific, and actionable.

---

*3,277 sessions. 1,000+ hours. These are the patterns that survived.*
