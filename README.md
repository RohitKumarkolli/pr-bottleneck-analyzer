# Automated Code-Review & PR Bottleneck Analyzer

> Tracks GitHub PR idle time, classifies review comments with an LLM, and
> surfaces review bottlenecks for engineering managers.

## Problem

Engineering managers can't see *where* code review stalls: which PRs are idle,
who is the bottleneck, and whether review time goes to trivial nitpicks or
substantive design discussion.

## Solution
<!-- One-paragraph summary + demo GIF (Milestone 7) -->

## Architecture
<!-- Diagram goes here (Milestone 7). Draft flow:
GitHub API -> Ingestion -> SQLite -> Metrics engine -> LLM classifier (Groq)
                                          |                  |
                                          +------> Streamlit dashboard
GitHub Actions (daily cron) triggers ingestion + metrics
LangGraph agent: stalled PR + classified comments -> summary + nudge draft -->

## Tech Stack

Python · GitHub REST API · SQLite · Groq (Llama 3.3) · Streamlit · LangGraph · GitHub Actions

## Target Repository

Analyzed: `scikit-learn/scikit-learn`

## Results
<!-- Fill in as milestones complete -->
| Metric | Value |
| -------- | ------- |
| PRs ingested | TBD |
| Review comments analyzed | TBD |
| Classifier accuracy (n=50 hand-labeled) | TBD |
| Median time-to-first-review | TBD |
| % of PRs idle > 7 days | TBD |

## Setup
<!-- Milestone 7 -->

## Roadmap

- [x] M0 Setup
- [ ] M1 Ingestion
- [ ] M2 Metrics
- [ ] M3 LLM classifier
- [ ] M4 Dashboard
- [ ] M5 Automation
- [ ] M6 Agent layer
- [ ] M7 Polish
