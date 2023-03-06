*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to login as the default superuser for the first time
    Login As User For The First Time    robot@localhost    robotpassword

I want to add indemnifications
    Click    xpath=//a[@class="button"]
    Fill Text    xpath=//*[@id="id_name"]    Dev Org
    Fill Text    xpath=//*[@id="id_code"]    dev
    Click    "Submit"
    #Click    xpath=//button[contains(text(),"Submit")]
    Check Checkbox    css=#id_may_scan
    Check Checkbox    css=#id_am_authorized
    Click    "Submit"
    Get Title    equal    OpenKAT - step_account_setup_intro

I want to onboard and create all optional users
    Click    "Create separate accounts"
    Click    "Let's add accounts"
    Get Title    equal    OpenKAT - step_account_setup_admin

I want to create a secondary admin account
    Create A User While Onboarding    Admin    admin@localhost    P@SSw00rdAdmin!123456789

I want to create a redteamer account
    Create A User While Onboarding    Redteamer    redteamer@localhost    P@SSw00rdRedteam!123456789

I want to create a client account
    Create A User While Onboarding    Client    client@localhost    P@SSw00rdClient!123456789

I can confirm that I can proceed
    #Debug
    Click    "Let's get started"
    Click    "Let's get started"
    Click    "Continue"
    Click    "Continue"
    Click    "Continue with this account, onboard me!"

I want generate my first report
    Generate First DNS Report

I am on the Crisis Room page
    #Debug
    Get Title    equal    OpenKAT - step_report

#Is user onboarded?
#    Go to    ${ROOT_URL}/admin/tools/organizationmember/1/change/
#    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded

I want to logout
    Go to    ${ROOT_URL}/crisis-room
    Logout Normally

I want to login again
    Login As User Normally    robot@localhost    robotpassword


*** Keywords ***
Create A User While Onboarding
    [Arguments]    ${name}    ${email}    ${password}
    Fill Text    xpath=//*[@id="id_name"]    ${name}
    Fill Text    xpath=//*[@id="id_email"]    ${email}
    Fill Text    xpath=//*[@id="id_password"]    ${password}
    Click    "Submit"
    #Get Text    .confirmation    contains    succesfully    error account creation failed
