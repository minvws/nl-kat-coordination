*** Settings ***
Library     OperatingSystem
Library     RequestsLibrary


*** Test Cases ***
I want to generate a report
    # read sample.json
    ${data}    Get File    templates/bevindingenrapport/sample.json

    # post sample
    ${response}    Post    http://localhost:29005/reports    ${data}
    ${report_id}    Set variable    ${response.json()["report_id"]}

    # timeout 20 sec
    Sleep    10s

    # get report
    ${response}    Get    http://localhost:29005/reports/${report_id}.keiko.pdf

    # check if 200, response is not empty and content-type is application/pdf
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal    ${response.headers["content-type"]}    application/pdf
    Should Be True    ${response.headers["content-length"]} > 1000

    # debug mode on, get .tex file
    ${response}    Get    http://localhost:29005/reports/${report_id}.keiko.tex

    # check if 200, response is not empty and content-type is application/pdf
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be Equal    ${response.headers["content-type"]}    text/x-tex; charset=utf-8
    Should Be True    ${response.headers["content-length"]} > 1000
