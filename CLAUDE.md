# Claude Working Preferences

## Project: PowerStatus App

### Testing Commands
- Test application: `source .venv/Scripts/activate && python power_status.py`
- Run with custom interval: `source .venv/Scripts/activate && python power_status.py --interval 3`
- Install dependencies: `source .venv/Scripts/activate && pip install -r requirements.txt`

### Code Style Preferences
- Follow existing Python conventions in the codebase
- Use clear, descriptive function and variable names
- Add proper error handling for hardware-dependent features
- Maintain compatibility with Windows-specific modules (msvcrt, pywin32)

### Development Workflow
- Always test changes in the .venv virtual environment
- Create meaningful commit messages following the established pattern
- Use git for version control with descriptive commit messages
- Create GitHub issues for new features and bug reports

### Project Structure
- Main application: `power_status.py`
- Dependencies: Listed in `requirements.txt`
- Virtual environment: `.venv/` (already configured)
- Documentation: `README.md`

### Key Features to Maintain
- Voice initialization must complete before showing "ready" status
- Proper keyboard input handling for Windows (ESC, H, <, >, R, S keys)
- Resource usage monitoring display
- Power state change detection and announcement
- Repeat mode functionality with configurable intervals

### Current Issues Tracking
- Status line should show repeat mode indicator (ON | OFF)
- Repeat mode should auto-announce current state when enabled

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Interaction Guidelines

### Collaboration Approach
- **Pair Programming Mode**: Claude acts as an expert Python and media processing consultant, offering suggestions and brainstorming collaboratively
- **Sequential Task Processing**: When multiple issues are presented, address one task at a time with confirmation before proceeding to the next
- **Critical Analysis**: Challenge assumptions and claims rather than readily agreeing; provide honest technical assessments

### Code Change Protocol
- **Pre-Change Reporting**: Before any code revision, list all functions/definitions that will be affected and obtain confirmation
- **Version Management**: Update version number and prepend change notes to the script's top comment block with every revision
- **Protected Code Areas**: Respect code blocks marked as "working well" and avoid modifications unless explicitly requested with confirmation
- **Edge Case Awareness**: Always report potential edge cases that may not have been considered

### Task Management Standards
- **TodoWrite Usage**: Employ TodoWrite tool for all multi-step or complex tasks to ensure systematic progress tracking
- **GitHub Issue Creation**: Create GitHub issues for ALL tasks, ideas, features, and questions presented - no work proceeds without an associated issue
- **Issue-Based Commits**: All commits must reference a specific GitHub issue number
- **Test Coverage**: Maintain 100% test coverage and run tests after code changes
- **Code Quality**: Follow existing patterns, conventions, and architectural decisions within the codebase

### Communication Standards
- **Concise Responses**: Be direct and focused on specific requested changes
- **Clear Status Updates**: Provide transparent progress reporting throughout task execution
- **Clarification Requests**: Ask for clarification when requirements are ambiguous rather than making assumptions

### Version Control Practices
- **Issue-Driven Development**: Every task, feature request, or question becomes a GitHub issue before any code work begins
- **Separate Commits**: Commit code changes separately from documentation updates
- **Descriptive Messages**: Use clear, descriptive commit messages that reference issue numbers and explain the "why" behind changes
- **Traceability**: Maintain full traceability from issue creation through commit completion

This approach ensures methodical, collaborative development while maintaining code quality, clear communication, and complete project traceability throughout the development process.

## Per-turn issue declaration (mooladhara#131) — NON-NEGOTIABLE

Every assistant turn MUST begin with a leading tag as the first token of the first line:

| Tag | Meaning |
|---|---|
| `[#123]` | Work bound to issue 123. **The normal case.** |
| `[unbound]` | **WORK with no issue yet — a TRIPWIRE, not a resting state.** File an issue. |
| `[status]` | Not work: a status/progress/report answer. Legitimate, no issue needed. |
| `[chat]` | Not work: conversation, clarification, a question answered. Legitimate. |
| `[meta]` | Not work: a quick command/lookup with no work product. Legitimate. |

ONE primary issue per turn. A turn spanning two issues is a signal to **split the turn**.

**Why:** it converts issue↔work attribution from *inference* to *declaration*. Unbound work
is unbillable and untraceable. `[status]`/`[chat]`/`[meta]` exist so that non-work turns do
not have to lie (`[#N]` on a status query) or trip a false alarm — a convention people must
game is a convention they will ignore.

A Stop hook (`.claude/hooks/check_issue_tag.py`) enforces the tag's presence. It is
**advisory** — it warns, it never blocks.
