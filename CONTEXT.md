# Agent Engineering Book

This repository grows a beginner-friendly Agent engineering book from source research, executable examples, active recall, and failure-driven verification.

## Language

**Public Textbook**:
A beginner-friendly Agent engineering book whose chapters must teach a coherent path and provide verifiable examples; personal notes feed it, while portfolio value is a consequence rather than its organizing goal.
_Avoid_: Personal notebook, portfolio-first showcase, authoritative encyclopedia

**Target Reader**:
A reader who can use basic Python, Git, and the command line but has not studied Agent engineering systematically; the book does not assume prior knowledge of tool protocols, context management, persistence, evaluation, or sandboxing.
_Avoid_: Non-programmer, experienced Agent engineer

**Canonical Chapter**:
The only actively maintained full-text version of a lesson, stored in this book repository.
_Avoid_: Blog source, mirrored article, duplicate chapter

**Published Blog Snapshot**:
A previously published Blog article kept as a historical version and entry point to its Canonical Chapter; it is not maintained as a second full-text source.
_Avoid_: Canonical chapter, synchronized copy

**Chapter Promotion**:
The one-chapter-at-a-time process that turns a Published Blog Snapshot into a Canonical Chapter only after active recall, current-source verification, practical evidence, and beginner-level review.
_Avoid_: File copy, bulk migration

**Chapter Quality Gate**:
The shared evidence a chapter must contain before promotion, without forcing every topic into identical headings or prose structure.
_Avoid_: Fixed chapter template, formatting checklist

**Practice Contract**:
The learning agreement attached to each lesson that separates code the learner must write once, code AI may generate, behavior that must be verified, and infrastructure that only needs boundary-level understanding.
_Avoid_: Homework list, code-generation rule

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
