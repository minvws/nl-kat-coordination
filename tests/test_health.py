from unittest import TestCase

from rocky.health import ServiceHealth
from rocky.views import flatten_health


class TaskListTestCase(TestCase):
    def test_flatten_health_simple(self):
        mock_health = ServiceHealth(
            service="service1",
            healthy=True,
            version="1.1.1",
        )
        self.assertListEqual(
            [
                ServiceHealth(
                    service="service1",
                    healthy=True,
                    version="1.1.1",
                )
            ],
            flatten_health(mock_health),
        )

    def test_flatten_health_recursive(self):
        mock_health = ServiceHealth(
            service="service1",
            healthy=True,
            version="1.1.1",
            results=[
                ServiceHealth(
                    service="service2",
                    healthy=False,
                    version="2.2.2",
                )
            ],
        )
        self.assertListEqual(
            [
                ServiceHealth(
                    service="service1",
                    healthy=True,
                    version="1.1.1",
                ),
                ServiceHealth(
                    service="service2",
                    healthy=False,
                    version="2.2.2",
                ),
            ],
            flatten_health(mock_health),
        )
