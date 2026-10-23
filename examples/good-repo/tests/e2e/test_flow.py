from tasks.service import TaskList


def test_add_then_complete():
    tasks = TaskList()
    tasks.add("write the report")
    completed = tasks.complete(0)
    assert completed.done is True
    assert tasks.open_tasks() == []
