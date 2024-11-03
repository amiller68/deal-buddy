from typing import Callable

def task(name: str):
    """Decorator to mark a function as a task (registration happens later)"""
    def decorator(func: Callable) -> Callable:
        func._task_name = name
        return func
    return decorator

from .process_om import process_om

__all__ = ['process_om']