<!--
SYNC IMPACT REPORT
==================
Version Change: Initial → 1.0.0
Action: Initial constitution creation

Modified Principles: N/A (initial creation)
- I. Minimal Comments (NEW)
- II. Mandatory Testing (NEW)
- III. Comprehensive Error Handling (NEW)
- IV. Conventional Commits (NEW)
- V. Technology Stack Adherence (NEW)

Added Sections:
- Core Principles (5 principles)
- Quality Standards
- Development Workflow
- Governance

Removed Sections: N/A (initial creation)

Templates Requiring Updates:
- ✅ plan-template.md: Reviewed - compatible with constitution principles
- ✅ spec-template.md: Reviewed - compatible with user story requirements
- ✅ tasks-template.md: Reviewed - compatible with test-first and parallel work principles

Follow-up TODOs: None
-->

# Conference Registration System Constitution

## Core Principles

### I. Minimal Comments
Code MUST be self-documenting through clear naming and structure. Comments are ONLY required for:
- Complex business logic that is not immediately apparent
- Non-obvious algorithmic decisions
- Critical security or performance considerations

**Rationale**: Excessive comments create maintenance burden and often become outdated. Well-written code with clear variable/function names is preferred.

### II. Mandatory Testing
Every feature MUST have unit tests before being considered complete.
- Tests MUST cover core business logic
- Tests MUST validate error handling paths
- Testing framework: pytest for Python backend, standard testing tools for Streamlit frontend
- Tests MUST be executable and pass before code review

**Rationale**: Testing ensures code quality, prevents regressions, and documents expected behavior. This is NON-NEGOTIABLE.

### III. Comprehensive Error Handling
All API endpoints and user-facing functions MUST implement error handling.
- Invalid input MUST be validated and rejected with clear error messages
- External dependencies (file I/O, network) MUST have try-catch blocks
- Errors MUST be logged with sufficient context for debugging
- User-facing errors MUST be informative without exposing internal details

**Rationale**: Robust error handling prevents system crashes, improves user experience, and aids troubleshooting.

### IV. Conventional Commits
All Git commit messages MUST follow the Conventional Commits specification.
- Format: `<type>(<scope>): <description>`
- Types: feat, fix, docs, style, refactor, test, chore
- Examples:
  - `feat(registration): add session capacity validation`
  - `fix(api): handle missing speaker photo gracefully`
  - `test(sessions): add unit tests for date filtering`

**Rationale**: Structured commit messages enable automated changelog generation, easier code review, and clearer project history.

### V. Technology Stack Adherence
All development MUST use the approved technology stack:
- **Frontend**: Streamlit (for rapid UI development)
- **Backend**: Python (with Flask/FastAPI for API services)
- **Data Storage**: JSON/Properties files (no database dependency)
- **Testing**: pytest for backend, Streamlit testing utilities for frontend

Deviations require explicit justification and approval.

**Rationale**: Consistency in technology choices reduces complexity, ensures team expertise, and simplifies deployment.

## Quality Standards

### Code Quality
- Python code MUST follow PEP 8 style guidelines
- Functions MUST have clear, single responsibilities
- Code duplication MUST be minimized through appropriate abstraction
- Magic numbers and hardcoded strings MUST be replaced with named constants

### Documentation
- README.md MUST document setup, installation, and running instructions
- API contracts MUST be documented (input/output formats, error codes)
- Configuration files MUST include inline comments explaining options
- Complex features SHOULD have architecture documentation

### Performance
- Session dashboard MUST load within 2 seconds for up to 50 sessions
- API responses MUST complete within 500ms for standard operations
- File I/O operations MUST handle errors gracefully when files are missing or corrupted

## Development Workflow

### Feature Development
1. Feature specification MUST be created and approved before implementation
2. Tests MUST be written first (test-driven development encouraged)
3. Implementation MUST pass all tests
4. Code review MUST verify compliance with this constitution
5. All checks MUST pass before merge

### Code Review Requirements
- At least one approval required before merge
- Reviewer MUST verify:
  - All principles from this constitution are followed
  - Tests exist and pass
  - Error handling is present
  - Commit messages follow Conventional Commits
  - No unnecessary comments

### Testing Gates
- All unit tests MUST pass
- No test files may be skipped or disabled without documented justification
- Test coverage for new features SHOULD exceed 80%

## Governance

This constitution supersedes all other development practices. All code, reviews, and architectural decisions MUST align with these principles.

### Amendment Process
- Amendments require documented rationale and team consensus
- Version number MUST be incremented following semantic versioning:
  - MAJOR: Breaking changes to principles or removal of core requirements
  - MINOR: New principles added or significant guidance expanded
  - PATCH: Clarifications, wording improvements, non-semantic changes

### Compliance
- Pull requests MUST reference this constitution for any complexity justifications
- Violations MUST be addressed before merge
- Repeated violations require process review

### Version Control
This constitution is version controlled alongside code. Changes follow the same review process as code changes.

**Version**: 1.0.0 | **Ratified**: 2025-10-27 | **Last Amended**: 2025-10-27
