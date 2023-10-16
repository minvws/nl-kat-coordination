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

I can confirm that I can proceed
    Click    xpath=//a[@class="button"]
    Click    "Continue"
    Click    "Continue"
    Click    "Continue with this account, onboard me!"

I want generate my first report
    Generate First DNS Report

I want to logout
    Go to    ${ROOT_URL}/crisis-room
    Logout Normally

I want to login again
    Login As User Normally    robot@localhost    robotpassword
    Click    "Skip onboarding"

Is user onboarded?
    Go to    ${ROOT_URL}/en/admin/tools/organizationmember/1/change/
    Get Checkbox State    id=id_onboarded    ==    True    user not onboarded

I am on the Crisis Room page
    Go to    ${ROOT_URL}
    Get Title    equal    OpenKAT - crisis_room

I add an object
    Go to    ${ROOT_URL}/dev/objects/add/
    Select options by    id=select_ooi_type    value    Network
    Click    xpath=//input[@type="submit"]
    Fill Text    xpath=//input[@name="name"]    Rieven
    Click    xpath=//form/button

I should have created the object
    ${object_text}    Get Text    xpath=//dl
    Should Be True    "Rieven" in """${object_text}"""    Rieven not found in object
    Should Be True    "Network" in """${object_text}"""    Network not found in object

I want to enter the Katalogus
    Click    xpath=//a[@href="/en/dev/kat-alogus/"]
    Get Title    equal    OpenKAT - katalogus

I want to see the DnsRecords page in details
    Click    xpath=//a[@href="/en/dev/kat-alogus/plugins/boefje/dns-records/"]
    Get Title    equal    OpenKAT - boefje_detail

I want to add the badssl.com hostname
    Go to    ${ROOT_URL}/en/dev/objects/add/
    Select options by    id=select_ooi_type    value    Hostname
    Click    xpath=//input[@type="submit"]
    Select options by    id=id_network    value    Network|internet
    Fill Text    id=id_name    badssl.com
    Click    xpath=//form/button
    Get Text
    ...    id=main-content
    ...    contains
    ...    badssl.com
    ...    not landed on page which contains the hostname

The DnsRecords boefje is completed
    Sleep    30s
    Set Browser Timeout    90s
    Go To    ${ROOT_URL}/en/dev/tasks
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-boefjes"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    5x
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/en/dev/tasks
    ...    ${e}
    ...    Completed

The DnsRecords boefje is normalized
    Set Browser Timeout    90s
    Go To    ${ROOT_URL}/en/dev/tasks/normalizers
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-normalizers"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    90s
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/en/dev/tasks/normalizers
    ...    ${e}
    ...    Completed

Download the mispo.es pdf report
    Go to    ${ROOT_URL}/en/dev/objects/detail/?ooi_id=Hostname%7Cinternet%7Cmispo.es
    Click    'Generate report'
    Set Browser Timeout    30s
    ${dl_promise}    Promise To Wait For Download
    Click    'Download PDF'
    ${file_obj}    Wait For    ${dl_promise}
    Set Suite Variable    ${REPORT_FILE}    ${file_obj}
    Log To Console    ${REPORT_FILE}

A valid pdf is downloaded
    File Should Exist    ${REPORT_FILE}[saveAs]    Cannot find downloaded file
    ${filesize}    Get File Size    ${REPORT_FILE}[saveAs]
    Should Be True    ${filesize} > 50000    The downloaded file is uncharacteristically small
    Should End With    ${REPORT_FILE}[suggestedFilename]    .pdf    File is not advertised as a pdf


*** Keywords ***
Create A User While Onboarding
    [Arguments]    ${name}    ${email}    ${password}
    Fill Text    xpath=//*[@id="id_name"]    ${name}
    Fill Text    xpath=//*[@id="id_email"]    ${email}
    Fill Text    xpath=//*[@id="id_password"]    ${password}
    Click    "Submit"
    # Get Text    .confirmation    contains    successfully    error account creation failed
