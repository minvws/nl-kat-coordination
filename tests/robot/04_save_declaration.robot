*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Add Several Append Origins
    Insert Calvin Outputs
    Verify Object Present    Hostname|internet|calvinnormalizer.com
    Verify Origin Present    Hostname|internet|calvinnormalizer.com.    4321

    Verify Object Present    Hostname|internet|calvinnormalizer.org
    Verify Origin Present    Hostname|internet|calvinnormalizer.org.    43210


*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}

Teardown Test
    Stop Monitoring
    Cleanup

Verify Object Present
    [Arguments]    ${reference}
    ${response}    Get    ${OCTOPOES_URI}/object    params=reference=${reference}
    Should Be Equal As Integers    ${response.status_code}    200

Verify Origin Present
    [Arguments]    ${reference}    ${origin_task_id}
    ${response}    Get    ${OCTOPOES_URI}/origins    params=reference=${reference}
    Should Be Equal As Integers    ${response.status_code}    200
    ${length}    Get Length    ${response.json()}
    Should Be Equal As Integers    ${length}    1
    Should Be Equal    ${response.json()[0]["task_id"]}    ${origin_task_id}
