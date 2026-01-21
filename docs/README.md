# Tailpaste Documentation

Comprehensive documentation for Tailpaste - a minimalist paste-sharing service with Tailscale integration.

## 📚 Documentation Index

### Core Documentation

- **[Main README](../README.md)** - Project overview, installation, and usage
- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to the project

### Technical Documentation

- **[CI/CD Pipeline](CI_CD.md)** - Complete CI/CD documentation
  - GitHub Actions workflows
  - Monitoring scripts
  - Deployment procedures
  - Security scanning (Trivy, dependencies)
  - Docker label strategy
  - Best practices and troubleshooting

- **[Service Inspector Guide](INSPECTOR_GUIDE.md)** - SSH access and debugging
  - Connecting via Tailscale SSH
  - Available debugging tools
  - Common inspection tasks
  - Security considerations

### Workflow Documentation

- **[Workflows README](../.github/workflows/README.md)** - GitHub Actions overview
  - Runner configuration
  - Workflow architecture
  - Trigger conditions

### Scripts Documentation

- **[Scripts README](../scripts/README.md)** - Monitoring and development tools
  - Health check script
  - Log analyzer
  - Monitoring tools
  - Git hooks

## 🚀 Quick Links

### Getting Started
- [Installation Guide](../README.md#installation)
- [Docker Deployment](../README.md#docker-deployment)
- [Configuration](../README.md#configuration)

### Development
- [Development Setup](CI_CD.md#development-tools)
- [Pre-commit Hooks](CI_CD.md#pre-commit-hooks)
- [Testing](CI_CD.md#troubleshooting)

### Operations
- [Deployment](CI_CD.md#deployment-workflow)
- [Monitoring](CI_CD.md#monitoring-scripts)
- [Troubleshooting](CI_CD.md#troubleshooting)
- [Rollback Procedures](CI_CD.md#rollback-procedures)

### Debugging
- [Service Inspection](INSPECTOR_GUIDE.md)
- [Health Checks](CI_CD.md#health-check-script)
- [Log Analysis](CI_CD.md#log-analyzer-script)

## 📖 Documentation Structure

```
Tailpaste/
├── README.md                    # Main project documentation
├── CONTRIBUTING.md              # Contribution guidelines
├── docs/
│   ├── README.md               # This file - documentation index
│   ├── CI_CD.md                # Complete CI/CD documentation
│   └── INSPECTOR_GUIDE.md      # Service debugging guide
├── .github/workflows/
│   └── README.md               # Workflows overview
└── scripts/
    └── README.md               # Scripts documentation
```

## 🔄 Documentation Updates

This documentation is maintained alongside the codebase. When making changes:

1. Update relevant documentation files
2. Keep examples current with actual code
3. Update the changelog for significant changes
4. Test all code examples and commands

**Last Updated**: January 20, 2026 | **Version**: 1.0.0
