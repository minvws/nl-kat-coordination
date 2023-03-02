*** Settings ***
Resource        ../xxx.resource

Suite Setup     Browser Setup


*** Test Cases ***
I want to go to the home page
    Go To    ${ROOT_URL}/
    Get Title    equal    KAT - landing_page

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

I want to enter the Katalogus
    Click    xpath=//a[@href="/kat-alogus/"]
    Get Title    equal    KAT - katalogus

I want to see the DnsRecords page in details
    Click    xpath=//a[@href="/kat-alogus/plugins/boefje/dns-records/"]
    Get Title    equal    KAT - plugin_detail

I want to add the badssl.com hostname
    Go to    ${ROOT_URL}/objects/add/
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
    Go To    ${ROOT_URL}/tasks
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-boefjes"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    90s
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/tasks
    ...    ${e}
    ...    Completed

The DnsRecords boefje is normalized
    Go To    ${ROOT_URL}/tasks/normalizers
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-normalizers"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    90s
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/tasks/normalizers
    ...    ${e}
    ...    Completed

Download the mispo.es pdf report
    Go to    ${ROOT_URL}/objects/detail/?ooi_id=Hostname%7Cinternet%7Cmispo.es
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
