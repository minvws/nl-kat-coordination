*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Variables ***
${REF_HSTS_FINDING}     Finding|HTTPHeader|internet|1.1.1.1|tcp|80|http|internet|example.com|http|internet|example.com|80|/|strict-transport-security|KAT-HSTS-VULNERABILITIES


*** Test Cases ***
HSTS Header With Config
    Insert Observation    tests/fixtures/normalizer_output_http.json
    Await Sync
    Insert Observation    tests/fixtures/normalizer_output_config.json
    Await Sync
    Declare Scan Profile    ${REF_HOSTNAME}    ${4}
    Await Sync
    Recalculate Scan Profiles
    Verify Object Present    ${REF_HSTS_FINDING}

HSTS Header Without Config
    Insert Observation    tests/fixtures/normalizer_output_http.json
    Await Sync
    Declare Scan Profile    ${REF_HOSTNAME}    ${4}
    Await Sync
    Recalculate Scan Profiles
    Verify Object Not Present    ${REF_HSTS_FINDING}
