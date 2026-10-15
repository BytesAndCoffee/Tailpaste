"""Shared pytest configuration."""

import os

from hypothesis import settings

# GitHub-hosted runners are slow and noisy enough to blow Hypothesis'
# default 200ms per-example deadline, which fails runs as Flaky.
settings.register_profile("ci", deadline=None)

if os.environ.get("CI"):
    settings.load_profile("ci")
