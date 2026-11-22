"""Evaluation bounded context Taskiq tasks.

Kept as an importable worker/scheduler module referenced by supervisord.conf.
Overdue task sweeping is owned exclusively by `src.execution.presentation.tasks`.
"""
