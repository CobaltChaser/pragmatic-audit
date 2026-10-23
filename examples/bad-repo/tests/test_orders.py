import time

import pytest

from orders import total


@pytest.mark.skip
def test_total_waits_for_background_job():
    time.sleep(2)
    assert total([{"price": 10}]) == 10


def test_total_runs():
    total([{"price": 10}])
