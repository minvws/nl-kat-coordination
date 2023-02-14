*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to login as the default superuser for the first time
    Login As User For The First Time    robot@localhost    robotpassword

I want to create a report with the superuser account
    Click    xpath=//a[@class="button"]
    Click    xpath=//button[contains(text(),"Submit")]
    Click    "Continue with this account, onboard me!"
    Get Title    equal    KAT - step_introduction
    Generate First DNS Report

Is user onboarded?
    Go to    ${ROOT_URL}/admin/tools/organizationmember/1/change/
    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded
    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded

I am on the Crisis Room page
    Go to    ${ROOT_URL}
    Get Title    equal    KAT - crisis_room

I want to logout
    Logout Normally

I want to login again
    Login As User Normally    robot@localhost    robotpassword
