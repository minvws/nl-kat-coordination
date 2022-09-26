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
    Login As User Normally    robot@localhost    robotpassword

I want to go to the crisis page
    Go To    ${ROOT_URL}/crisis-room
    Get Title    equal    KAT - crisis_room

I want to enter the Katalogus
    Click    xpath=//a[@href="/kat-alogus/"]
    Get Title    equal    KAT - katalogus

I want to see the DnsRecords page in details
    Click    xpath=//a[@href="/kat-alogus/plugins/boefjes/dns-records/"]
    Get Title    equal    KAT - katalogus_detail

I want to enable the DnsRecords Boefje
    Click    'Enable'
    Get Text
    ...    xpath=//div[@class="explanation"]
    ...    contains
    ...    Boefje 'dns-records' enabled
    ...    no boefje enabled confirmation message

I want to add a Network
    Go to    ${ROOT_URL}/objects/add/
    Select options by    id=select_ooi_type    value    Network
    Click    xpath=//input[@type="submit"]
    Fill Text    id=id_name    internet
    Click    xpath=//form/button
    Get Text
    ...    id=main-content
    ...    contains
    ...    internet
    ...    not landed on page which contains the network name

I want to add the mispo.es hostname
    Go to    ${ROOT_URL}/objects/add/
    Select options by    id=select_ooi_type    value    Hostname
    Click    xpath=//input[@type="submit"]
    Select options by    id=id_network    value    Network|internet
    Fill Text    id=id_name    mispo.es
    Click    xpath=//form/button
    Get Text
    ...    id=main-content
    ...    contains
    ...    mispo.es
    ...    not landed on page which contains the hostname

I want to set clearance level 2 to mispo.es
    Click    'Clearance level (L0, empty)'
    Select options by    id=id_level    value    2
    Click    xpath=//form/button
    Get Text
    ...    h1[rf-selector="clearance-header"]
    ...    contains
    ...    L2, declared
    ...    no confirmation that the clearance level has changed

I want to launch the DnsRecords boefje for mispo.es
    Go to    ${ROOT_URL}/objects
    Click    'mispo.es'
    Click    'Start Scan'
    Get Text
    ...    xpath=//div[@class="confirmation"]
    ...    contains
    ...    Your scan is running successfully in the background
    ...    no positive confirmation message

The DnsRecords boefje is completed
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-boefjes"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    60s
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/tasks
    ...    ${e}
    ...    Completed

The DnsRecords boefje is normalized
    ${e}    Get Table Cell Element
    ...    table[rf-selector="table-normalizers"]
    ...    "Status"
    ...    "Hostname|internet|mispo.es"
    Wait Until Keyword Succeeds
    ...    60s
    ...    2s
    ...    Reload The Page Until Element Contains
    ...    ${ROOT_URL}/tasks
    ...    ${e}
    ...    Completed
