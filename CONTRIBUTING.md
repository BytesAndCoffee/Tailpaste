# Contributing to tailpaste

Thank you for your interest in contributing to tailpaste! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and constructive in all interactions. We're here to build something useful together.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Tailscale installed and running
- Docker (for containerized deployment)
- Git

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/yourusername/tailpaste.git
cd tailpaste
```

2. **Create a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

4. **Configure the service**

```bash
cp .env.example .env
cp config.toml.example config.toml
# Edit .env and config.toml as needed
```

5. **Run tests**

```bash
pytest
```

## Development Workflow

### Running Locally

```bash
python main.py
```

The service will start on port 8080 (or the port specified in your config).

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_storage.py

# Run property-based tests only
pytest -k "property"

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Testing Guidelines

We use both unit tests and property-based tests:

- **Unit tests**: Test specific examples and edge cases
- **Property tests**: Test universal properties across randomized inputs using Hypothesis

When adding new features:
1. Write unit tests for specific behaviors
2. Write property tests for universal correctness properties
3. Ensure all tests pass before submitting PR

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Write clear, focused commits
- Include tests for new functionality
- Update documentation as needed

3. **Test your changes**

```bash
pytest
```

4. **Commit your changes**

```bash
git add .
git commit -m "Add feature: brief description"
```

Use clear commit messages:
- `Add feature: description` for new features
- `Fix: description` for bug fixes
- `Docs: description` for documentation changes
- `Refactor: description` for code refactoring
- `Test: description` for test additions/changes

5. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

6. **Open a Pull Request**

- Provide a clear description of the changes
- Reference any related issues
- Explain why the change is needed
- Include screenshots for UI changes

### Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Respond to review feedback promptly

## Areas for Contribution

### Features

- Additional authentication methods
- Rate limiting
- Paste expiration
- Syntax highlighting
- API endpoints
- CLI tool improvements

### Documentation

- Improve README clarity
- Add more examples
- Create tutorials
- Translate documentation

### Testing

- Add more property-based tests
- Improve test coverage
- Add integration tests
- Performance testing

### Bug Fixes

Check the issue tracker for bugs that need fixing.

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
