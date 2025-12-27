"""Performance test package for Ink application.

This package contains performance and benchmark tests to verify the
application meets speed and memory requirements. Tests focus on:
- Startup time (< 2 seconds requirement)
- Window creation time (< 500ms target)
- Memory usage and leak detection
- Component creation benchmarks

Note: pytest-benchmark is optional. If not installed, benchmark tests
will use basic time measurements instead.
"""
