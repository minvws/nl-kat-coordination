*** Settings ***
Library     OperatingSystem
Library     RequestsLibrary
Library     DateTime

*** Variables ***
${HOSTNAME_OOI}   Hostname|internet|example.com
${IPADDR_OOI}    IPAddressV4|internet|1.1.1.1
${RESOLVED_HOSTNAME_OOI}    ResolvedHostname|internet|example.com|internet|1.1.1.1
${TZ}    +00:00
${OCTOPOES_URI}

*** Keywords ***
Get Valid Time
    ${valid_time}   Get Current Date    time_zone=utc    result_format=%Y-%m-%dT%H:%M:%S.%f
    [return]        ${valid_time}${TZ}

Get Valid Time Params
    ${valid_time}   Get Valid Time
    ${valid_time_params}    Create Dictionary    valid_time=${valid_time}
    [return]        ${valid_time_params}


*** Test Cases ***
I want to save an origin
    ${norm_output_json}    Get File    tests/fixtures/normalizer_output.json
    ${response}    Post    ${OCTOPOES_URI}/observations    ${norm_output_json}
    Should Be Equal As Integers    ${response.status_code}    200

I want to save a scan profile on Hostname
    ${params}   Get Valid Time Params
    ${scan_profile_json}    Get File    tests/fixtures/declared_scan_profile1.json
    ${response}    Put
    ...    ${OCTOPOES_URI}/scan_profiles
    ...    ${scan_profile_json}
    ...    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200

I want to save a scan profile on IP Address
    ${params}   Get Valid Time Params
    ${scan_profile_json}    Get File    tests/fixtures/declared_scan_profile2.json
    ${response}    Put
    ...    ${OCTOPOES_URI}/scan_profiles
    ...    ${scan_profile_json}
    ...    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200

I want to trigger a scan level recalculation
    Sleep   1s
    ${params}   Get Valid Time Params
    ${response}    Get
    ...    ${OCTOPOES_URI}/scan_profiles/recalculate
    ...    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200
    Sleep   1s

I want to read the Hostname and its scan profile
    ${response}    Get    ${OCTOPOES_URI}/object    params=reference=${HOSTNAME_OOI}
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal    ${response.headers["content-type"]}    application/json
    ${response_data}    Set Variable    ${response.json()}
    Should Be Equal    ${response_data["primary_key"]}    ${HOSTNAME_OOI}
    Should Be Equal As Integers    ${response_data["scan_profile"]["level"]}    ${4}

I want to read the IPAddress and its scan profile
    ${response}    Get    ${OCTOPOES_URI}/object    params=reference=${IPADDR_OOI}
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal    ${response.headers["content-type"]}    application/json
    ${response_data}    Set Variable    ${response.json()}
    Should Be Equal    ${response_data["primary_key"]}    ${IPADDR_OOI}
    Should Be Equal As Integers    ${response_data["scan_profile"]["level"]}    ${2}

I want to reset the Hostname's scan profile
    ${params}   Get Valid Time Params
    ${scan_profile_json}    Get File    tests/fixtures/empty_scan_profile1.json
    ${response}    Put
    ...    ${OCTOPOES_URI}/scan_profiles
    ...    ${scan_profile_json}
    ...    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200

I want to retrigger a scan level recalculation
    Sleep   1s
    ${params}   Get Valid Time Params
    ${response}    Get
    ...    ${OCTOPOES_URI}/scan_profiles/recalculate
    ...    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200
    Sleep   1s

I want to read the Hostname and its (now empty) scan profile
    ${response}    Get    ${OCTOPOES_URI}/object    params=reference=${HOSTNAME_OOI}
    ${response_data}    Set Variable    ${response.json()}
    Should Be Equal    ${response_data["primary_key"]}    ${HOSTNAME_OOI}
    Should Be Equal As Integers    ${response_data["scan_profile"]["level"]}    ${0}

I want to read the ResolvedHostname and its (now empty) scan profile
    ${response}    Get    ${OCTOPOES_URI}/object    params=reference=${RESOLVED_HOSTNAME_OOI}
    ${response_data}    Set Variable    ${response.json()}
    Should Be Equal    ${response_data["primary_key"]}    ${RESOLVED_HOSTNAME_OOI}
    Should Be Equal As Integers    ${response_data["scan_profile"]["level"]}    ${0}
