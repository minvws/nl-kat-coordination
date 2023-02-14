*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to login as the redteam user for the first time
    Login As User For The First Time    redteamer@localhost    P@SSw00rdRedteam!123456789

I want generate my first report
    Generate First DNS Report

I am on the Crisis Room page
    Go to    ${ROOT_URL}
    Get Title    equal    KAT - crisis_room

I add an object
    Go to    ${ROOT_URL}/objects/add/
    Select options by    id=select_ooi_type    value    Network
    Click    xpath=//input[@type="submit"]
    Fill Text    xpath=//input[@name="name"]    Rieven
    Click    xpath=//form/button

I should have created the object
    ${object_text}    Get Text    xpath=//dl
    Should Be True    "Rieven" in """${object_text}"""    Rieven not found in object
    Should Be True    "Network" in """${object_text}"""    Network not found in object

I want to logout
    Go to    ${ROOT_URL}/crisis-room
    Logout Normally

I want to login again
    Login As User Normally    redteamer@localhost    P@SSw00rdRedteam!123456789
