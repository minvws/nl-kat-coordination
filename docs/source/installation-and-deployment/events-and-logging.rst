==================
Events and Logging
==================

For Events we use CRUDE (create, read, update, delete, execute) as specified in the NEN7513.

Different routes have different ranges of Event Codes, the ranges are as follows:

- ooi_change: 08000* - 08001*
- plugin_change: 08002* - 08003*
- job_change: 08005*
- report_change: 08007*
- schedule_change 08008*
- report_recipe_change 08009*
- login_event: 09XXXXX, where XXXX = 1111, 2222, 3333 etc.
- file_action: 7000**
- organization_change: 90001*
- account_change: 9001**

========== ================== ==================== =========================================== =====
Event code Model              Routing key          Description                                 CRUDE
========== ================== ==================== =========================================== =====
080001     OOI                ooi_change           An OOI is created.                          C
080002     OOI                ooi_change           An OOI is edited.                           U
080003     OOI                ooi_change           An OOI is deleted.                          D
080010     Indemnification    ooi_change           An indemnification is (re)declared.         U
080011     Indemnification    ooi_change           A declared indemnification is deleted.      D
080021     Plugin             plugin_change        A plugin is enabled.                        U
080022     Plugin             plugin_change        A plugin is disabled.                       U
080023     Plugin             plugin_change        Settings of a plugin are updated.           U
080024     Plugin             plugin_change        Settings of a plugin are deleted.           D
080025     Plugin             plugin_change        A plugin is created.                        C
080026     Plugin             plugin_change        A plugin is updated.                        U
080027     Plugin             plugin_change        A plugin is deleted.                        D
080028     Plugin             plugin_change        The schema of a plugin is updated.          U
080031     Plugin             plugin_change        A plugin (version) is allowed.              U
080032     Plugin             plugin_change        A plugin (version) is disallowed.           U
080033     Plugin             plugin_change        A plugin source is added.                   C
080034     Plugin             plugin_change        A plugin source is updated.                 U
080035     Plugin             plugin_change        A plugin source is removed.                 D
080036     Plugin             plugin_change        Plugin signing key is trusted.              U
080037     Plugin             plugin_change        Plugin signing key is untrusted.            U
080051     Job                job_change           A job is manually created.                  C
080052     Job                job_change           A job is canceled.                          D
080071     Report             report_change        A report is created.                        C
080072     Report             report_change        A report is edited.                         U
080073     Report             report_change        A report is deleted.                        D
080081     Schedule           schedule_change      A schedule is created.                      C
080082     Schedule           schedule_change      A schedule is edited.                       U
080083     Schedule           schedule_change      A schedule is deleted.                      D
080091     ReportRecipe       report_recipe_change A Report Recipe is created.                 C
700001     RawData            file_action          A raw file is downloaded.                   E
090012     Organisation       organization_change  A new organization is created.              C
090013     Organisation       organization_change  Organization information changed.           U
090014     Organisation       organization_change  Organization is removed.                    D
900100     KATUser            account_change       A new user created.                         C
900101     KATUser            account_change       User data changed.                          U
900102     KATUser            account_change       A user role changed.                        U
900104     KATUser            account_change       Account status changed (Enabled/Disabled).  U
900105     KATUser            account_change       User credential reset is performed.         E
900106     OrganizationMember account_change       User organization membership changed.       U
900107     TOTPDevice         account_change       Reset 2FA.                                  C
900108     Indemnification    account_change       Set max allowed indemnification.            U
900109     Indemnification    account_change       Set max accepted indemnification.           U
900110     KATUser            account_change       A user is deleted.                          D
900111     TOTPDevice         account_change       2FA is removed.                             D
========== ================== ==================== =========================================== =====
