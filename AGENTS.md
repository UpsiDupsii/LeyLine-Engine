# LeyLine Project Rules and Preferences

## 1. Zero Emoji Policy
- Do not use emojis anywhere: in code, comments, documentation, commit messages, PR descriptions, or assistant responses.

## 2. SDLC and Branching Strategy
- Staging and Main branches:
  - `main` is production/release.
  - `staging` is integration.
- Every new agent, feature, fix, or chore must be developed on a dedicated branch branched off `staging`:
  - `feat/<feature-name>`
  - `fix/<fix-name>`
  - `chore/<chore-name>`
- Local Review First Policy:
  - After completing feature development and local test verification, DO NOT automatically push the branch to GitHub or prompt to open a PR.
  - Keep changes on the local feature branch first, ensure local services/scripts run correctly, and provide a comprehensive local verification guide.
  - Ask for the user's confirmation to review locally first.
  - Only after the user explicitly confirms that local testing is satisfactory, push the branch to GitHub and supply the copy-pasteable PR title and description targeting `staging`.
  - Exception: If the user explicitly grants permission to push directly in a prompt, proceed with the push.
- Explicit Branch Cleanup Reminder: Always explicitly remind the user to delete the feature branch after merging the PR on GitHub to prevent branch clutter.
- After a cohesive set of features is validated on `staging`, a release PR is prepared for `staging -> main` with release notes.

## 3. Architecture Principles
- Multi-Agent System: Each agent has a single, well-defined responsibility:
  - Vision / Perception Engine: Screen capture, region calibration, and frame downsampling (mss, OpenCV).
  - Gamer Agent: Real-time road/obstacle detection and action planning (Gemini Multimodal).
  - Controller Handler: Low-latency keyboard and game input simulation (pynput).
  - Commentator Agent: Dynamic esports shoutcaster analyzing play highlights (Gemini / Groq).
  - Audio Engine: High-fidelity asynchronous neural voice synthesis (edge-tts).
  - Stream Orchestrator: OBS virtual camera and audio layer routing for YouTube Live.
- Separation of Concerns:
  - LLMs decide (action choices, tactical plans, commentary scripts).
  - Deterministic tools execute (mss screen grabs, pynput keystrokes, edge-tts audio, OBS streams).
- Background Tasks & Asynchronous Execution: Decouple perception-action loop from commentary generation so voice synthesis never introduces steering latency.
- Prioritize Free APIs and Open Source Tools:
  - Google Gemini API: Free tier on Google AI Studio (https://aistudio.google.com) for multimodal vision and high-speed reasoning.
  - Groq Cloud: Free tier on Groq Console (https://console.groq.com) for ultra-fast text/commentary inference.
  - Open-source local tools: OpenCV, mss, pynput, edge-tts, pygame.

## 4. Change Tracking and Reporting
- Mandatory Step-by-Step Reporting: In every turn where changes are introduced, provide a clear, chronological breakdown of actions taken and logic implemented.
- Mandatory Ordered File Change Log: Provide a sequential list of all files created, modified, or removed with clickable links (file:///...) and brief explanations of what was changed in each file.

## 5. Response Structure Requirements
When presenting work to the user, structure responses as follows:
1. Executive Summary: What was accomplished in this turn.
2. Step-by-Step Execution: Numbered list detailing the exact operational steps performed.
3. Ordered File Manifest: Chronological table or list of modified/created files with paths and specific changes made.
4. Review & Verification Guide: Commands to verify the changes locally (tests, linting, running scripts/server).
5. Next Steps / Pull Request Details: Clear recommendations for the next action.

## 6. Documentation Maintenance (README.md)
- Always update `README.md` as new features, agents, and capabilities are added.
- Ensure `README.md` includes clear, step-by-step instructions on how to configure environment variables, run the engine, and verify each module.
