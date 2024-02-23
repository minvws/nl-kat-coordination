*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Add Several Append Origins
    Insert Calvin Outputs
    Verify Object Present    Hostname|internet|calvinnormalizer.com
    Verify Origin Present    Hostname|internet|calvinnormalizer.com    824cfb63-1a46-4446-9941-d36e9550bee5

    Verify Object Present    Hostname|internet|calvinnormalizer.org
    Verify Origin Present    Hostname|internet|calvinnormalizer.org    9bcc478d-00a2-4cae-976b-c7f4beea0375

    Insert Regular Declarations


*** Keywords ***
Verify Origin Present
    [Arguments]    ${reference}    ${origin_task_id}
    ${params}    Create Dictionary    result=${reference}    valid_time=${VALID_TIME}
    ${response}    Get    ${OCTOPOES_URI}/origins    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200
    ${length}    Get Length    ${response.json()}
    Should Be Equal As Integers    ${length}    1
    Should Be Equal    ${response.json()[0]["task_id"]}    ${origin_task_id}
