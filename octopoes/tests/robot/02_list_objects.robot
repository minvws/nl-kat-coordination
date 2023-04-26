*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
List Objects
    Insert Normalizer Output
    Await Sync
    Object List Should Contain    ${REF_HOSTNAME}
    Total Object Count Should Be    ${6}

List Objects With Filter
    Insert Normalizer Output
    Await Sync
    Verify Object List With Filter


List Random Objects With Filter
    Insert Normalizer Output
    Declare Scan Profile    ${REF_HOSTNAME}    ${1}
    Await Sync
    Length Of Random Object List With Filter Should Be   ${1}   ${5}
    Length Of Random Object List With Filter Should Be   ${0}   ${1}
    Length Of Random Object List With Filter Should Be   ${{ [1,0] }}   ${6}
    Length Of Random Object List With Filter Should Be   ${{ [2,3] }}   ${0}

*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}

Teardown Test
    Cleanup
    Await Sync
    Stop Monitoring

Verify Object List With Filter
    ${response_data}    Get Objects With ScanLevel 0
    Should Be Equal    ${response_data["count"]}    ${6}

Get Objects With ScanLevel 0
    ${response}    Get    ${OCTOPOES_URI}/objects    params=scan_level=0
    ${response_data}    Set Variable    ${response.json()}
    RETURN    ${response_data}

Length Of Random Object List With Filter Should Be
    [Arguments]    ${scan_levels}     ${expected_length}
    ${params} =    Create Dictionary    scan_level=${scan_levels}    amount=10
    ${response}    Get    ${OCTOPOES_URI}/objects/random    params=${params}
    Length Should Be    ${response.json()}    ${expected_length}
