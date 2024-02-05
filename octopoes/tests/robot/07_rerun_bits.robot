*** Settings ***
Resource            robot.resource
Library             OperatingSystem
Library             BuiltIn

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Rerun bits
    Insert Observation    tests/fixtures/normalizer_output.json
    Await Sync

    # check that only two origins exist, one observation, and one inference
    Verify Origin Present    Hostname|internet|example.com    2

    # add the new bit to the bits folder and restart containers
    ${container_id_worker}    Run    docker ps -aqf 'name=octopoes-ci_octopoes_api_worker'
    Log    ${container_id_worker}
    Run    docker cp .ci/mock_bits/url_classification_mock ${container_id_worker}:app/octopoes/bits
    Run    docker restart ${container_id_worker}

    ${container_id_api}    Run
    ...    docker ps -aq --filter "name=octopoes-ci_octopoes" | grep -v $(docker ps -aq --filter "name=octopoes-ci_octopoes_api_worker") | awk '{print $1}'
    Log    ${container_id_api}
    Run    docker cp .ci/mock_bits/url_classification_mock ${container_id_api}:app/octopoes/bits
    Run    docker restart ${container_id_api}

    # wait until containers started up
    Sleep    3s

    # make sure that new origin still does not exist
    Await Sync
    Verify Origin Present    Hostname|internet|example.com    2

    ${response}    Post    ${OCTOPOES_URI}/bits/recalculate
    Await Sync
    Verify Origin Present    Hostname|internet|example.com    3


*** Keywords ***
Verify Origin Present
    [Arguments]    ${reference}    ${expected_amout_of_origins}
    ${response}    Get    ${OCTOPOES_URI}/origins    params=result=${reference}
    Should Be Equal As Integers    ${response.status_code}    200
    ${length}    Get Length    ${response.json()}
    Should Be Equal As Integers    ${length}    ${expected_amout_of_origins}
