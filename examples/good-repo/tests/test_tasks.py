from tasks.service import TaskList


def test_add_trims_the_title():
    tasks = TaskList()
    task = tasks.add("  write the report  ")
    assert task.title == "write the report"


def test_blank_title_is_rejected():
    tasks = TaskList()
    try:
        tasks.add("   ")
    except ValueError as exc:
        assert "blank" in str(exc)
    else:
        raise AssertionError("blank title was accepted")
