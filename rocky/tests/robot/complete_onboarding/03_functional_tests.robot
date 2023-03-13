*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to go to the home page
    Go To    ${ROOT_URL}/
    Get Title    equal    OpenKAT - landing_page

I want to change the language to Papiamentu
    Click    xpath=//button[@value="pap"]
    Get Text    id=KAT    contains    Kiko ta bo meta ku KAT?    this is not Papiamentu

I want to change the language to Dutch
    Click    xpath=//button[@value="nl"]
    Get Text    id=KAT    contains    Wat is KAT?    this is not Dutch

I want to change the language to English
    Click    xpath=//button[@value="en"]
    Get Text    id=KAT    contains    What is KAT?    this is not English

I want to login normally
    Login As User Normally    redteamer@localhost    P@SSw00rdRedteam!123456789

I want to go to the crisis page
    Go To    ${ROOT_URL}/crisis-room
    Get Title    equal    KAT - crisis_room
