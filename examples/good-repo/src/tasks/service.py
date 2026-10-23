from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Task:
    title: str
    done: bool = False


@dataclass
class TaskList:
    tasks: list[Task] = field(default_factory=list)

    def add(self, title: str) -> Task:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("task title must not be blank")
        task = Task(title=cleaned)
        self.tasks.append(task)
        return task

    def complete(self, index: int) -> Task:
        task = self.tasks[index]
        updated = Task(title=task.title, done=True)
        self.tasks[index] = updated
        return updated

    def open_tasks(self) -> list[Task]:
        return [task for task in self.tasks if not task.done]
