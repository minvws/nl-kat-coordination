*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
List Objects
    Insert Normalizer Output
    Await Sync
    Object List Should Contain Reported Items

List Objects With Filter
    Insert Normalizer Output
    Await Sync
    Verify Object List With Filter


*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}

Teardown Test
    Cleanup
    Await Sync
    Stop Monitoring

Object List Should Contain Reported Items
    ${response_data}    Get Objects
    # 6, because 2 objects are created by bits
    Should Be Equal    ${response_data["count"]}    ${6}
    Should Be Equal    ${response_data["items"][0]["primary_key"]}    ${REF_HOSTNAME}

Verify Object List With Filter
    ${response_data}    Get Objects With ScanLevel 0
    Should Be Equal    ${response_data["count"]}    ${6}

Get Objects With ScanLevel 0
    ${response}    Get    ${OCTOPOES_URI}/objects    params=scan_level=0
    ${response_data}    Set Variable    ${response.json()}
    RETURN    ${response_data}
