from typing import List, Optional
from rocky.settings import (
    MIAUW_BASE_URL,
    MIAUW_USERNAME,
    MIAUW_PASSWORD,
    MIAUW_API_ENABLED,
)
from tools.miauw import MiauwAPIClient, SignalGroupResponse
from tools.models import Organization


client = MiauwAPIClient(MIAUW_BASE_URL, MIAUW_USERNAME, MIAUW_PASSWORD)


def create_signal_group_for_organization(
    organization: Organization,
) -> SignalGroupResponse:
    return client.create_group(
        organization.signal_username,
        organization.name + " KAT Notifications",
    )


def get_signal_group_for_organization(
    organization: Organization,
) -> SignalGroupResponse:
    if not organization.has_signal_group() or not MIAUW_API_ENABLED:
        return None

    return client.get_group(organization.signal_username, organization.signal_group_id)


def add_member_to_signal_group_for_organization(
    organization: Organization, member_signal_username: str
) -> SignalGroupResponse:
    return client.group_add_members(
        organization.signal_username,
        organization.signal_group_id,
        [member_signal_username],
    )


def send_message_to_signal_group_for_organization(
    organization: Organization, message: str
) -> None:
    client.message_send(
        organization.signal_username,
        organization.signal_group_id,
        message,
    )


def receive_last_messages(signal_username: str) -> None:
    client.receive(signal_username)


def get_registered_usernames() -> Optional[List[str]]:
    return client.get_all_registered_usernames()


def get_signal_linking_qr() -> str:
    response = client.get_linking_qr("kwetsbaarheden-analyse-tool")

    return response.json()[0]
