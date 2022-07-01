from typing import Union, Text, List

import requests
from pydantic import BaseModel
from requests import HTTPError, Response
from requests.auth import HTTPBasicAuth

from rocky.settings import MIAUW_REQUEST_VALIDATE

MIAUW_PATH_GROUPS_INDEX = "/groups"
MIAUW_PATH_GROUPS_SHOW = "/groups/show"
MIAUW_PATH_GROUPS_CREATE = "/groups/create"
MIAUW_PATH_GROUPS_ADD_MEMBER = "/groups/add_member"

MIAUW_PATH_LINKING_QR = "/linking/qrcodelink"
MIAUW_PATH_REGISTERED_USERNAMES = "/linking/registered_usernames"

MIAUW_PATH_MESSAGES_SEND = "/messages/send"
MIAUW_PATH_RECEIVE = "/receive"


class SignalGroupResponse(BaseModel):
    blocked: bool
    name: str
    id: str
    internal_id: str
    invite_link: str
    members: List[str]


class SignalGroupListResponse(BaseModel):
    __root__: List[SignalGroupResponse]


class MiauwAPISession(requests.Session):
    def __init__(self, base_url: str, username: str, password: str):
        super().__init__()

        self._base_url = base_url
        self._username = username
        self._password = password

    def request(self, method: str, path: Union[str, bytes, Text], **kwargs) -> Response:
        url = self._base_url + path

        headers = {"Accept": "*/json"}

        return super().request(
            method,
            url,
            auth=HTTPBasicAuth(self._username, self._password),
            headers=headers,
            verify=MIAUW_REQUEST_VALIDATE,
            **kwargs
        )


class MiauwAPIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self._session = MiauwAPISession(base_url, username, password)

    def _verify_response(self, response) -> None:
        response.raise_for_status()

        if response.text and "error" in response.json():
            result = response.json()
            response.status_code = result.get("error")["code"]
            raise HTTPError(result.get("error")["message"], response=response)

    def get_linking_qr(self, device_name: str) -> Response:
        """Link signal account with a QRcode"""
        response = self._session.get(
            MIAUW_PATH_LINKING_QR, data={"device_name": device_name}
        )
        self._verify_response(response)

        return response

    def get_all_registered_usernames(self) -> List[str]:
        """Get a list of all registered signal usernames"""
        response = self._session.get(MIAUW_PATH_REGISTERED_USERNAMES)
        self._verify_response(response)

        return response.json()

    def get_all_groups(self, signal_username: str) -> List[SignalGroupResponse]:
        """Get a list of all groups from user"""
        response = self._session.get(
            MIAUW_PATH_GROUPS_INDEX, params={"username": signal_username}
        )
        self._verify_response(response)

        return SignalGroupListResponse.parse_obj(response.json()).__root__

    def get_group(
        self, signal_username: str, signal_group_id: str
    ) -> SignalGroupResponse:
        """Get information from a specified signal group"""
        response = self._session.get(
            MIAUW_PATH_GROUPS_SHOW,
            params={"username": signal_username, "group_id": signal_group_id},
        )
        self._verify_response(response)

        return SignalGroupResponse.parse_obj(response.json())

    def create_group(
        self, signal_username: str, group_name: str
    ) -> SignalGroupResponse:
        """Create a new group for organization"""

        params = {
            "username": signal_username,
            "name": group_name,
            "description": "Group used for automatically generated KAT-notifications.",
            "group_link": True,
            "permissions": {"add_members": "only-admins", "edit_groups": "only-admins"},
        }

        response = self._session.put(MIAUW_PATH_GROUPS_CREATE, data=params)
        self._verify_response(response)

        return SignalGroupResponse.parse_obj(response.json())

    def group_add_members(
        self, signal_username: str, group_id: str, members: list
    ) -> SignalGroupResponse:
        """
        Add (a) member(s) to a group
        When adding a member to a group, make sure you have the correct permissions for the group
        """

        params = {"username": signal_username, "group_id": group_id, "members": members}

        response = self._session.post(MIAUW_PATH_GROUPS_ADD_MEMBER, data=params)
        self._verify_response(response)

        return SignalGroupResponse.parse_obj(response.json())

    def message_send(
        self, member_signal_username: str, recipient: str, message: str
    ) -> None:
        """Send a message to single recipient (group ID)"""
        params = {
            "username": member_signal_username,
            "message": message,
            "recipients": [recipient],
            "attachments": [],
        }

        response = self._session.post(MIAUW_PATH_MESSAGES_SEND, data=params)
        self._verify_response(response)

    def receive(self, signal_username: str) -> None:
        """Receiving data is required in regular intervals"""
        response = self._session.get(
            MIAUW_PATH_RECEIVE, params={"username": signal_username}
        )
        self._verify_response(response)
