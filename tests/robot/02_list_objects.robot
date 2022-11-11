*** Settings ***
Library     OperatingSystem
Library     RequestsLibrary
Library     DateTime

*** Variables ***
${HOSTNAME_OOI}   Hostname|internet|example.com
${OCTOPOES_URI}

*** Test Cases ***
I want to save an origin
    ${norm_output_json}    Get File    tests/fixtures/normalizer_output.json
    ${response}    Post    ${OCTOPOES_URI}/observations    ${norm_output_json}
    Should Be Equal As Integers    ${response.status_code}    200

I want to list objects
    ${response}    Get    ${OCTOPOES_URI}/objects
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal    ${response.headers["content-type"]}    application/json
    ${response_data}    Set Variable    ${response.json()}
    Should Be Equal    ${response_data["items"][0]["primary_key"]}    ${HOSTNAME_OOI}
