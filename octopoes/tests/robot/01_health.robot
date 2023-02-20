*** Settings ***
Library     RequestsLibrary


*** Variables ***
${OCTOPOES_URI}         http://localhost:29000
${OCTOPOES_ORG_URI}     http://localhost:29000/_dev


*** Test Cases ***
Health Endpoint
    Await Healthy
    Octopoes Healthy


*** Keywords ***
Octopoes Healthy
    ${response}    Get    ${OCTOPOES_URI}/health
    Should Be Equal As Integers    ${response.status_code}    200

Await Healthy
    Wait Until Keyword Succeeds    10s    1s    Octopoes Healthy
