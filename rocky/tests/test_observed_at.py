from datetime import datetime, timezone

from rocky.views.mixins import ObservedAtMixin


def test_observed_at_no_value(mocker):
    mock_mixin_datetime = mocker.patch("rocky.views.mixins.datetime")
    mock_request = mocker.Mock()
    mock_request.GET = {}
    now = datetime(2023, 10, 24, 9, 34, 56, 316699, tzinfo=timezone.utc)
    mock_mixin_datetime.now.return_value = now

    observed_at = ObservedAtMixin()
    observed_at.request = mock_request
    assert observed_at.get_observed_at() == now


def test_observed_at_date(mocker):
    mock_request = mocker.Mock()
    mock_request.GET = {"observed_at": "2023-10-24"}

    observed_at = ObservedAtMixin()
    observed_at.request = mock_request
    assert observed_at.get_observed_at() == datetime(2023, 10, 24, 23, 59, 59, 999999, tzinfo=timezone.utc)


def test_observed_at_datetime(mocker):
    mock_request = mocker.Mock()
    mock_request.GET = {"observed_at": "2023-10-24T09:34:56"}

    observed_at = ObservedAtMixin()
    observed_at.request = mock_request
    assert observed_at.get_observed_at() == datetime(2023, 10, 24, 9, 34, 56, 0, tzinfo=timezone.utc)


def test_observed_at_datetime_with_timezone(mocker):
    mock_request = mocker.Mock()
    mock_request.GET = {"observed_at": "2023-10-24T11:34:56+02:00"}

    observed_at = ObservedAtMixin()
    observed_at.request = mock_request
    assert observed_at.get_observed_at() == datetime(2023, 10, 24, 9, 34, 56, 0, tzinfo=timezone.utc)
