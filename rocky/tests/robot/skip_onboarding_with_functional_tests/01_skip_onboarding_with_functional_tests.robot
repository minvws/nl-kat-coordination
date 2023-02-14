*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to login as the default superuser for the first time
    Login As User For The First Time    robot@localhost    robotpassword

I want to skip onboarding altogether
    Click    xpath=//a[@class="button"]
    Click    xpath=//button[contains(text(),"Submit")]
    Click    "Continue with this account, onboard me!"
    Click    "Skip onboarding"
    Get Title    equal    KAT - crisis_room

Is user onboarded?
    Go To    ${ROOT_URL}/admin/tools/organizationmember/1/change/
    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded
    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded
    Go to    ${ROOT_URL}/crisis-room

I want to logout
    Logout Normally
