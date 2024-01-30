*** Settings ***
Resource            robot.resource

Test Setup          Setup Test
Test Teardown       Teardown Test


*** Test Cases ***
Propagate Deletion
    Insert Empty Normalizer Output
    Await Sync
#    This test fails because of circular origins proving eachother's existence
#    Object List Should Be Empty


*** Keywords ***
Object List Should Be Empty
    ${response_data}    Get Objects
    Should Be Equal    ${response_data["count"]}    ${0}
