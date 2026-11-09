---
name: leyline-workflow
description: Enforces LeyLine development standards, SDLC branching, multi-agent gaming architecture, and PR workflows without emojis.
---

# LeyLine Development Skill

This skill guides the implementation of the LeyLine multi-agent AI game-playing and live commentary engine.

## General Guidelines
- Strict zero-emoji policy across all responses, commits, documentation, and code.
- Always branch off `staging` using `feat/<agent-or-feature-name>`, `fix/<fix-name>`, or `chore/<chore-name>`.
- Always verify Ruff linting (`python -m ruff check .`, `python -m ruff format --check .`) and pytest tests before presenting changes.
- Local Review First Policy:
  - Do NOT automatically push feature branches to GitHub or prompt to open a PR immediately upon implementation.
  - Keep changes on the local feature branch first, ensure local scripts and services execute cleanly, and give the user clear verification steps for local testing.
  - Ask the user for confirmation to review locally.
  - Only after the user confirms that local testing looks good, push the branch to GitHub and provide the ready-to-use PR title and description for merging into `staging`.
  - Exception: If the user explicitly grants permission to push directly in a prompt, proceed with the push.
- Explicit Branch Cleanup Reminder: Always explicitly remind the user to delete the feature branch on GitHub after merging the PR to keep the repository clean.
- Mandatory Step-by-Step Reporting: In every turn where changes are introduced, provide a clear, chronological breakdown of actions taken and logic implemented.
- Mandatory Ordered File Change Log: Provide an ordered list of all files created, modified, or deleted with clickable links (`file:///...`) and a brief explanation of changes in each file.
- Mandatory README Maintenance: Keep `README.md` continuously updated as new features, agents, and capabilities are added.

## Response Structure Requirements
When presenting work to the user, structure responses as follows:
1. Executive Summary: What was accomplished in this turn.
2. Step-by-Step Execution: Numbered list detailing the exact operational steps performed.
3. Ordered File Manifest: Chronological table or list of modified/created files with paths and specific changes made.
4. Review & Verification Guide: Commands to verify the changes locally (tests, linting, running scripts).
5. Next Steps / Pull Request Details: Clear recommendations for the next action.

## Agent System Overview
1. Screen Perception Engine: High-speed window grabber and region calibration (`mss`, `OpenCV`).
2. Gamer Agent: Visual decision loop that perceives obstacle patterns and outputs optimal actions (`Gemini 2.0 Flash`).
3. Controller Handler: Low-latency OS keystroke simulation (`pynput`).
4. Commentator Agent: Dynamic play-by-play esports caster analyzing highlights (`Gemini 2.0 Flash` / `Groq`).
5. Audio Voice Engine: Natural voice commentary playback (`edge-tts`).
6. Stream Orchestrator: OBS virtual camera and audio layer routing for YouTube Live.

## Execution Principle
- LLMs decide (action choices, tactical plans, commentary scripts).
- Deterministic tools execute (mss screen grabs, pynput keystrokes, edge-tts audio, OBS streams).

## Free API References
- Gemini API: Free tier on Google AI Studio (https://aistudio.google.com) - large context window, multimodal vision comprehension.
- Groq Cloud: Free tier on Groq Console (https://console.groq.com) - high-speed text and commentary inference.
- edge-tts: Free Microsoft neural speech synthesis with zero API keys required.
- OpenCV & mss: 100% free, local screen capture and image processing.
