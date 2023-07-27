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
    # Click    xpath=//button[contains(text(),"Submit")]
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

I want to land on crisis room after adding optional users
    Get Title    equal    OpenKAT - crisis_room

# Note: the CI should be extended when the error 500 is properly debugged


*** Keywords ***
Create A User While Onboarding
    [Arguments]    ${name}    ${email}    ${password}
    Fill Text    xpath=//*[@id="id_name"]    ${name}
    Fill Text    xpath=//*[@id="id_email"]    ${email}
    Fill Text    xpath=//*[@id="id_password"]    ${password}
    Click    "Submit"
    # Get Text    .confirmation    contains    successfully    error account creation failed
