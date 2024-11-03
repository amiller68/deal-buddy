from typing import Callable, Any
from enum import Enum
import celery
from celery.signals import task_prerun

class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2

class TaskManager:
    def __init__(self, redis_url: str, app_state: Any):
        self.app = celery.Celery(
            'tasks',
            broker=redis_url,
            backend=redis_url
        )
        self.app_state = app_state
        
        # Inject app_state into all tasks using task_prerun signal
        @task_prerun.connect
        def init_task(task, **kwargs):
            task.request.app_state = self.app_state

    def register_task(self, task_func: Callable):
        """Register a task with Celery"""
        name = task_func._task_name
        return self.app.task(name=name)(task_func)

    def execute_task(self, task_name: str, *args, priority: TaskPriority = TaskPriority.MEDIUM, **kwargs):
        """Execute a registered task"""
        task = self.app.tasks.get(task_name)
        if not task:
            raise ValueError(f"Task {task_name} not registered")
            
        return task.apply_async(
            args=args,
            kwargs=kwargs,
            priority=priority.value
        )