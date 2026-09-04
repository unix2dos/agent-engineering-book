# Agent Engineering Book

This repository grows a beginner-friendly Agent engineering book from source research, executable examples, active recall, and failure-driven verification.

## Language

**Public Textbook**:
A beginner-friendly Agent engineering book whose chapters must teach a coherent path and provide verifiable examples; personal notes feed it, while portfolio value is a consequence rather than its organizing goal.
_Avoid_: Personal notebook, portfolio-first showcase, authoritative encyclopedia

**Learning North Star**:
The learner's ability to independently design, implement, and diagnose Agent systems; textbook quality supports that ability, while portfolio value and traffic are downstream results.
_Avoid_: Publishing volume, traffic target, portfolio-first roadmap

**Career Direction**:
Agent Runtime and AI Systems are the primary technical depth; one real Agent application must prove that the runtime knowledge can deliver useful work. Learning effort is roughly 70% systems principles and 30% application evidence.
_Avoid_: Framework operator, model-research curriculum, runtime theory without an application

**Core Lesson**:
A transferable capability that changes how most Agent systems are designed, verified, or operated and requires hands-on evidence to learn. Popularity, a framework feature, or a default-on setting does not by itself make a topic core.
_Avoid_: Framework tour, feature catalogue, default-enabled feature

**Curriculum Spine**:
The Pareto-filtered path from tools and state through reliability, safety, minimal observability, evaluation, orchestration, long-running work, and production operation. Only the next three lessons are planned in detail; fast-changing frameworks and specialized capabilities remain evidence or optional branches.
_Avoid_: Framework catalogue, fixed encyclopedia, personal learning chronology

**Target Reader**:
A reader who can use basic Python, Git, and the command line but has not studied Agent engineering systematically; the book does not assume prior knowledge of tool protocols, context management, persistence, evaluation, or sandboxing.
_Avoid_: Non-programmer, experienced Agent engineer

**Canonical Chapter**:
The only actively maintained full-text version of a lesson, stored in this book repository.
_Avoid_: Blog source, mirrored article, duplicate chapter

**Published Blog Snapshot**:
A previously published Blog article kept as a historical version and entry point to its Canonical Chapter. Broken links are repaired and load-bearing factual errors are corrected in place with a visible note, but its full text is never synchronized with the Book.
_Avoid_: Canonical chapter, synchronized copy, abandoned page

**Blog Gateway Post**:
A short Blog publication created when a curriculum phase completes, or when one reader problem deserves an independent entry, and directs readers to the Canonical Chapters; it is a discovery surface, not a mirrored lesson.
_Avoid_: Duplicate chapter, release log, second source of truth

**Chapter Promotion**:
The one-chapter-at-a-time process that turns a Published Blog Snapshot into a Canonical Chapter only after active recall, current-source verification, practical evidence, and beginner-level review.
_Avoid_: File copy, bulk migration

**Chapter Quality Gate**:
The shared evidence a chapter must contain before promotion, without forcing every topic into identical headings or prose structure.
_Avoid_: Fixed chapter template, formatting checklist

**Triggered Chapter Maintenance**:
Reopening a Canonical Chapter only after a concrete reader block, failing example, changed primary source, or contradiction with a later lesson is found.
_Avoid_: Scheduled rewrite, polish cycle, frozen forever

**Plain-language Entry**:
The first explanation of a load-bearing term: a visible action or failure comes first, a short everyday explanation gives it meaning, and only then does the technical name enter. It preserves technical precision without making the reader decode unexplained vocabulary.
_Avoid_: Glossary dump, analogy-only definition, simplified terminology

**Practice Contract**:
The learning agreement attached to each lesson that requires at least one visible piece of evidence and separates code the learner must write once, code AI may generate, behavior that must be verified, and infrastructure that only needs boundary-level understanding. Major curriculum milestones require integrated practice, and adjacent early stages may share one capstone.
_Avoid_: Homework list, code-generation rule, mandatory opening table

**Application Proof Project**:
The existing Workspace and Coding Agent that accumulates each stage's core mechanisms and provides one end-to-end portfolio artifact. New lessons extend this project unless a genuinely different environment is required.
_Avoid_: Toy collection, new demo per concept, framework showcase

**Agent Evaluation**:
A repeatable task set with explicit success conditions that runs the current Agent and checks its real output or environment state. Deterministic checks come first; subjective graders are added only when code cannot express the required quality.
_Avoid_: One successful chat, platform dashboard, judge-only score

**Regression Gate**:
The release check that blocks a change when a previously guaranteed behavior or safety invariant fails. Quality signals that naturally vary are tracked across runs rather than treated as one-shot hard failures.
_Avoid_: Generic CI, exact wording comparison, single judge score

**Recorded-session Replay**:
An optional Harness testing technique that feeds recorded Model or Tool outputs back through the current Runtime to reproduce Runtime behavior without paying for a live call. It does not prove that the current Model, Prompt, or external service still succeeds.
_Avoid_: Session recovery, live-model rerun, Agent evaluation

**Book Repository**:
The `agent-engineering-book` GitHub repository containing both Canonical Chapters and executable examples.
_Avoid_: Blog repository, generated GitBook site

**Book Site**:
The GitBook reading interface connected only after the first Canonical Chapter passes promotion; it renders the Book Repository and never becomes a second source of truth.
_Avoid_: Authoring source, canonical repository

**Core Reference Set**:
The eleven open-source repositories studied repeatedly across the book, grouped by purpose: Coding Agent Runtime (Pi, OpenClaw, Hermes, Codex, OpenCode, and DeepSeek Harness), Agent frameworks and interfaces (OpenAI Agents SDK, Claude Agent SDK Python, and LangGraph), and observability and evaluation (Phoenix and Inspect AI).
_Avoid_: List of every popular Agent framework

**Experimental Core Reference**:
A project important enough to compare repeatedly but not stable enough to treat its current interfaces as durable guidance; study a pinned version and separate architectural lessons from version-specific APIs. DeepSeek Harness is the current example because its official repository labels it a Developer Preview.
_Avoid_: Stable standard, unversioned best practice, topic-only reference

**Product Behavior Reference**:
A significant product whose core Runtime source is unavailable, studied through official behavior, documentation, configuration, plugins, and observable interfaces without presenting those materials as core source code. Claude Code is the primary example.
_Avoid_: Open-source Runtime, source implementation

**Topic Reference**:
An additional repository consulted only when a chapter needs its distinct implementation, rather than becoming another project studied end to end.
_Avoid_: Core reference, required framework
