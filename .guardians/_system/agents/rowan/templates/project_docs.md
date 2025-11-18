# Project Documentation Template (Lexicon)

## What This Covers
- README.md
- CONTRIBUTING.md
- CHANGELOG.md
- LICENSE files

---

## README.md Structure

### Essential Sections (Must Have)

```markdown
# Project Name

[Badges: build status, coverage, version, license, etc.]

## Overview
[1-2 paragraphs: what problem does this solve? Who is it for?]

## Features
- Key feature 1
- Key feature 2
- Key feature 3

## Installation

```bash
pip install package-name
```

## Quick Start

```python
from package import main_feature

# Simplest possible usage example
result = main_feature.do_something()
print(result)
```

## Documentation
Full documentation: [link]

## Requirements
- Python 3.8+
- Other dependencies

## License
[License type] - see [LICENSE](LICENSE)

## Support
- Issues: [GitHub Issues link]
- Discussions: [link]
```

### Optional but Valuable Sections

```markdown
## Configuration
[How to configure, environment variables, config files]

## Usage Examples
[More detailed examples beyond Quick Start]

## Development Setup
[For contributors - how to set up dev environment]

## Testing
```bash
pytest tests/
```

## Deployment
[If applicable]

## FAQ
[Common questions]

## Roadmap
[Future plans]

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md)

## Acknowledgments
[Credits, inspiration, dependencies]

## Changelog
See [CHANGELOG.md](CHANGELOG.md)
```

---

## CONTRIBUTING.md Structure

```markdown
# Contributing to [Project Name]

Thanks for your interest in contributing!

## Code of Conduct
[Link to CODE_OF_CONDUCT.md or inline]

## How Can I Contribute?

### Reporting Bugs
1. Check existing issues first
2. Use the bug report template
3. Include:
   - Python version
   - Package version
   - Minimal reproduction code
   - Expected vs actual behavior

### Suggesting Features
1. Check existing feature requests
2. Explain the use case
3. Provide examples of desired behavior

### Pull Requests

#### Before You Start
- Open an issue to discuss major changes
- Check that it's not already being worked on

#### Development Setup
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/repo.git
cd repo

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

#### Making Changes
1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Make your changes
3. Add tests for new functionality
4. Run tests: `pytest`
5. Run linters: `black . && flake8`
6. Update documentation if needed

#### Commit Messages
Follow conventional commits:
```
feat: add new feature
fix: resolve bug in module
docs: update README
test: add tests for feature
refactor: restructure module
```

#### Submitting PR
1. Push to your fork
2. Open PR against `main` branch
3. Fill out PR template
4. Wait for review

## Coding Standards
- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Aim for 80%+ test coverage
- Keep functions focused (SRP)

## Testing Guidelines
- Write tests for all new features
- Maintain or improve coverage
- Test edge cases
- Use descriptive test names

## Documentation
- Update docstrings for code changes
- Update README if public API changes
- Add examples for new features
- Update CHANGELOG.md

## Review Process
- Maintainers review within 3-5 business days
- Address feedback or explain reasoning
- Minimum one approval required
- CI must pass

## Questions?
Open a discussion or reach out to maintainers.
```

---

## CHANGELOG.md Structure

Use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features in development

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Now removed features

### Fixed
- Bug fixes

### Security
- Security patches

## [1.2.0] - 2025-01-13

### Added
- New `process_async()` method for async processing (#123)
- Support for Python 3.12

### Changed
- Improved error messages for validation failures (#145)
- Updated dependencies to latest versions

### Fixed
- Fixed race condition in concurrent processing (#156)
- Resolved memory leak in cache module (#160)

### Deprecated
- `old_method()` will be removed in 2.0.0 - use `new_method()` instead

## [1.1.0] - 2024-12-01

### Added
- CLI support with `--verbose` flag
- Configuration file support (YAML and JSON)

### Fixed
- Fixed crash when input is empty (#134)

## [1.0.0] - 2024-11-01

### Added
- Initial release
- Core processing functionality
- Basic validation
- Comprehensive test suite

[Unreleased]: https://github.com/user/repo/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/user/repo/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/user/repo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/user/repo/releases/tag/v1.0.0
```

---

## LICENSE Guidance

### Common Choices

**MIT** (Permissive - most common for open source)
- Simple, permissive
- Commercial use allowed
- Good default choice

**Apache 2.0** (Permissive with patent protection)
- Similar to MIT
- Explicit patent grant
- Good for corporate projects

**GPL v3** (Copyleft - viral)
- Derivative works must also be GPL
- Prevents proprietary forks
- Use if you want ecosystem to stay open

**BSD 3-Clause** (Permissive)
- Similar to MIT
- Slightly more explicit

### When to Use Each

```markdown
# If creating and want:
- Maximum adoption → MIT
- Patent protection → Apache 2.0
- Prevent proprietary forks → GPL v3
- Academic/research → BSD 3-Clause

# Corporate/proprietary → Don't add to public repo or use proprietary license
```

---

## Common Findings for Project Docs

### README Issues
- Missing installation instructions
- No usage examples
- Outdated badge information
- Broken links
- No clear purpose statement
- Missing license information
- No contribution guidelines link

### CONTRIBUTING Issues
- Missing development setup instructions
- No coding standards specified
- Unclear PR process
- Missing testing guidelines
- No commit message conventions

### CHANGELOG Issues
- Not following Keep a Changelog format
- Missing version links
- Unreleased section not maintained
- Vague descriptions ("bug fixes")
- Missing dates or version numbers

---

## Lexicon's Tone for Project Docs

**When reviewing README:**
- "This README assumes I already know what your project does. I don't. Explain it like I'm a new developer who just found this repo."
- "Installation section says 'easy to install' but doesn't actually tell me HOW. Let's fix that."
- "Great feature list, but how do I actually USE these features? Examples, please."

**When reviewing CONTRIBUTING:**
- "You want contributors but didn't tell them how to run tests locally. That's... optimistic."
- "The PR process is 'open a PR and hope for the best.' Let's give people actual guidance."

**When reviewing CHANGELOG:**
- "Version 1.2.0: 'various improvements' — which improvements? Future-you won't remember."
- "Nice changelog! Dates, versions, clear categories. This is how it's done."

**When the docs are good:**
- "This README is a masterclass. Clear, concise, has examples. 10/10."
- "CONTRIBUTING.md that actually helps contributors? Rare and beautiful."

---

## Finding Template

```markdown
### Finding #X: [e.g., "README missing installation instructions"]
**Severity:** 🟠 High **Effort:** Small **Risk:** Low
**Location:** README.md (lines X-Y or "missing section")
**Category:** Missing Section | Outdated Info | Unclear | Broken Links

#### The Issue
[Why this matters for users/contributors]

**Current State:**
[What's currently there, or note it's missing]

#### Options

**Option A: Add comprehensive installation section** [RECOMMENDED]
```markdown
## Installation

### Using pip (recommended)
```bash
pip install package-name
```

### From source
```bash
git clone https://github.com/user/repo.git
cd repo
pip install -e .
```

### Development install
```bash
pip install -e ".[dev]"
```

## Requirements
- Python 3.8 or higher
- pip 20.0 or higher
```

**Option B: Minimal installation section**
[For very simple packages]

#### Manager Decision
- [ ] Approve A
- [ ] Approve B
- [ ] Reject
- [ ] Needs Discussion

**Status:** PENDING
```

---

**Lexicon's reminder:** "Your README is often the first impression. Make it count."