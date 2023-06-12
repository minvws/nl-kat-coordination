*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Bit With Scan Level 1
    Insert Observation    tests/fixtures/normalizer_output_nxdomain.json
    Object List Should Not Contain    KATFindingType|KAT-NXDOMAIN
    Object List Should Not Contain    Finding|Hostname|internet|example.com|KAT-NXDOMAIN
    Declare Scan Profile    Hostname|internet|example.com    1
    Await Sync
    Object List Should Contain    KATFindingType|KAT-NXDOMAIN
    Object List Should Contain    Finding|Hostname|internet|example.com|KAT-NXDOMAIN
    Declare Scan Profile    Hostname|internet|example.com    0
    Await Sync
    Object List Should Not Contain    Finding|Hostname|internet|example.com|KAT-NXDOMAIN


*** Keywords ***
Setup Test
    Start Monitoring    ${QUEUE_URI}

Teardown Test
    Stop Monitoring
    Cleanup
