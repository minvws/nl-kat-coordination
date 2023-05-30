*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Rerun bits
    Insert Observation    tests/fixtures/normalizer_output.json
    Await Sync
    ${response}    Post    ${OCTOPOES_URI}/bits/recalculate
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal As Integers    ${response.content}    19


*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}

Teardown Test
    Cleanup
    Await Sync
    Stop Monitoring
