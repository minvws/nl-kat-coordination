*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Simple Scan Profile Inheritance
    Declare Scan Profile    ${REF_HOSTNAME}    ${4}
    ${response_data}    Get Scan Profile Inheritance    ${REF_IPADDR}
    Length Should Be    ${response_data}    3
    Should Be Equal As Strings    ${response_data[1]["reference"]}    ${REF_RESOLVEDHOSTNAME}


*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}
    Insert Normalizer Output
    Await Sync

Teardown Test
    Cleanup
    Await Sync
    Stop Monitoring

Get Scan Profile Inheritance
    [Arguments]    ${reference}
    ${response}    Get    ${OCTOPOES_URI}/scan_profiles/inheritance    params=reference=${reference}
    Should Be Equal As Integers    ${response.status_code}    200
    ${response_data}    Set Variable    ${response.json()}
    RETURN    ${response_data}
