==================
Events and Logging
==================

For Events we use CRUDE (create, read, update, delete, execute) as specified in the NEN7513.

Different routes have different ranges of Event Codes, the ranges are as follows:

- login_event: 0900** & 09XXXXX, where XXXX = 1111, 2222, 3333 etc.
- file_action: 7000**
- ooi_change: 80000* - 80001* & 10050* & 90023*
- plugin_change: 80002* - 80003*
- job_change: 80005*
- report_change: 80007*
- schedule_change 80008*
- report_recipe_change 80009*
- dashboard_change 90030*
- dashboarddata_change 90030*
- account_change: 9001**
- organization_change: 90020* 0 90021* & 9*0000
- indemnification_change: 90022*
- observation_change: 10010*
- declaration_change: 10020*
- affirmation_change: 10030*
- origin_change: 10040*

========== ================== ====================== =========================================== ===== =======
Event code Model              Routing key            Description                                 CRUDE In Code
========== ================== ====================== =========================================== ===== =======
090001     Session            login_event            A session is created.                       C     090001
090002     Session            login_event            A session updated.                          U     090002
090003     Session            login_event            A session is deleted.                       D     090003
091111     KATUser            login_event            A user logged in.                           E     No
092222     KATUser            login_event            A user logged out.                          E     No
093333     TOTPDevice         login_event            A user MFA failed.                          E     No
094444     KATUser            login_event            A user login failed.                        E     No
700001     RawData            file_action            A raw file is downloaded.                   E     No
800001     OOI                ooi_change             An OOI is created.                          C     No
800002     OOI                ooi_change             An OOI is edited.                           U     No
800003     OOI                ooi_change             An OOI is deleted.                          D     No
800010     Indemnification    ooi_change             An indemnification is (re)declared.         U     No
800011     Indemnification    ooi_change             A declared indemnification is deleted.      D     No
800021     Plugin             plugin_change          A plugin is enabled.                        U     800021
800022     Plugin             plugin_change          A plugin is disabled.                       U     800022
800023     Plugin             plugin_change          Settings of a plugin are updated.           U     800023
800024     Plugin             plugin_change          Settings of a plugin are deleted.           D     800024
800025     Plugin             plugin_change          A plugin is created.                        C     800025
800026     Plugin             plugin_change          A plugin is updated.                        U     800026
800027     Plugin             plugin_change          A plugin is deleted.                        D     No
800028     Plugin             plugin_change          The schema of a plugin is updated.          U     No
800031     Plugin             plugin_change          A plugin (version) is allowed.              U     No
800032     Plugin             plugin_change          A plugin (version) is disallowed.           U     No
800033     Plugin             plugin_change          A plugin source is added.                   C     No
800034     Plugin             plugin_change          A plugin source is updated.                 U     No
800035     Plugin             plugin_change          A plugin source is removed.                 D     No
800036     Plugin             plugin_change          Plugin signing key is trusted.              U     No
800037     Plugin             plugin_change          Plugin signing key is untrusted.            U     No
800051     Job                job_change             A job is manually created.                  C     No
800052     Job                job_change             A job is canceled.                          D     No
800071     Report             report_change          A report is created.                        C     800071
800072     Report             report_change          A report is edited.                         U     No
800073     Report             report_change          A report is deleted.                        D     800073
800081     Schedule           schedule_change        A schedule is created.                      C     800081
800082     Schedule           schedule_change        A schedule is edited.                       U     800082
800083     Schedule           schedule_change        A schedule is deleted.                      D     800083
800084     Schedule           schedule_change        A schedule is enabled.                      U     0800081*
800085     Schedule           schedule_change        A schedule is disabled.                     D     0800082*
800091     ReportRecipe       report_recipe_change   A Report Recipe is created.                 C     800091
900100     KATUser            account_change         A new user created.                         C     900101*
900101     KATUser            account_change         User data changed.                          U     900102*
900102     KATUser            account_change         An user role changed.                       U     No
900104     KATUser            account_change         Account status changed (Enabled/Disabled).  U     No
900105     KATUser            account_change         User credential reset is performed.         E     No
900106     OrganizationMember account_change         User organization membership changed.       U     900212*
900107     TOTPDevice         account_change         Reset 2FA.                                  E     No
900108     Indemnification    account_change         Set max allowed indemnification.            U     No
900109     Indemnification    account_change         Set max accepted indemnification.           U     No
900110     KATUser            account_change         A user is deleted.                          D     900103*
900111     TOTPDevice         account_change         2FA is removed.                             D     No
900112     TOTPDevice         account_change         2FA is updated.                             U     No
900201     Organization       organization_change    A new organization is created.              C     900201
900202     Organization       organization_change    Organization information changed.           U     900202
900203     Organization       organization_change    Organization is removed.                    D     900203
900211     OrganizationMember organization_change    User organization membership created.       C     900211
900212     OrganizationMember organization_change    User organization membership changed.       U     900212
900213     OrganizationMember organization_change    User organization membership removed.       D     900213
900221     Indemnification    indemnification_change An indemnification is created.              C     900221
900222     Indemnification    indemnification_change An indemnification changed.                 U     900222
900223     Indemnification    indemnification_change An indemnification is removed.              D     900223
900231     OOIInformation     ooi_change             OOI information is created.                 C     900231
900232     OOIInformation     ooi_change             OOI information changed.                    U     900232
900233     OOIInformation     ooi_change             OOI information is removed.                 D     900233
900301     Dashboard          dashboard_change       A Dashboard is created.                     C     No
900302     Dashboard          dashboard_change       A Dashboard is edited.                      U     No
900303     Dashboard          dashboard_change       A Dashboard is deleted.                     D     No
900307     DashboardData      dashboard_data_change  A Dashboard data is created.                C     No
900308     DashboardData      dashboard_data_change  A Dashboard data is edited.                 U     No
900309     DashboardData      dashboard_data_change  A Dashboard data is deleted.                D     No
900310     DashboardData      dashboard_data_change  A Dashboard data is repositioned.           U     No
910000     Organization       organization_change    An organization is cloned.                  C     910000
920000     Organization       organization_change    Recalculated bits for organizations         U     920000
100101     Observation        observation_change     An observation is created.                  C     100101
100201     Declaration        declaration_change     A declaration is created.                   C     100201
100301     Affirmation        affirmation_change     An affirmation is created.                  C     100301
100403     Origin             origin_change          An origin is deleted.                       D     100403
100503     OOI                ooi_change             An object is deleted.                       D     100503
========== ================== ====================== =========================================== ===== =======

\* differentiates from the suggested event code.

Proposition
-----------

The proposition is to use the event code with ``PCCCEE``, where:
- P = Project
- CCC = Category
- EE = Event

Projects (Root Folder)
----------------------

- Boefjes - scanners and normalizers = 5
- Bytes (raw data storage) = 6
- Mula (scheduler) = 7
- Octopoes (datamodel) = 8
- Rocky (Front-End) = 9

Category (Action / Sub Folder)
------------------------------

- login_event = 000
- account = 001
- organization = 002
- crisis_room = 003
- katalogus = 004

========== ================== ====================== =========================================== =====
Event code Model              Category               Description                                 CRUDE
========== ================== ====================== =========================================== =====
900001     User               login_event            A user logged in.                           E
900002     User               login_event            A user logged out.                          E
900003     AuthToken          login_event            A user MFA succeeded.                       E
900004     AuthToken          login_event            A user MFA failed.                          E
900005     User               login_event            A user login failed.                        E
900101     User               account                A user is created.                          C
900102     User               account                User data changed.                          U
900103     User               account                A user is removed.                          D
900104     KATUser            account                Account status changed (Enabled/Disabled).  U
900105     KATUser            account                User credential reset is performed.         E
900106     OrganizationMember account                User organization membership changed.       U
900107     AuthToken          account                2FA reset is performed                      E
900108     Indemnification    account                Set max allowed indemnification for user.   U
900109     Indemnification    account                Set max accepted indemnification for user.  U
900110     AuthToken          account                2FA is created.                             C
900111     AuthToken          account                2FA is updated.                             U
900112     AuthToken          account                2FA is removed.                             D
900113     KATUser            account                An user account type changed.               U
900201     Organization       organization           A new organization is created.              C
900202     Organization       organization           Organization information changed.           U
900203     Organization       organization           Organization is removed.                    D
900211     OrganizationMember organization           User organization membership created.       C
900212     OrganizationMember organization           User organization membership changed.       U
900213     OrganizationMember organization           User organization membership removed.       D
900301     Dashboard          crisis_room            A Dashboard was created.                    C
900302     Dashboard          crisis_room            A Dashboard was updated.                    U
900303     Dashboard          crisis_room            A Dashboard was deleted.                    D
900304     ReportRecipe       crisis_room            A report recipe was created.                C
900305     ReportRecipe       crisis_room            A report recipe was updated.                U
900306     ReportRecipe       crisis_room            A report recipe was deleted.                D
900307     DashboardData      crisis_room            A Dashboard data is created.                C
900308     DashboardData      crisis_room            A Dashboard data is edited.                 U
900309     DashboardData      crisis_room            A Dashboard data is deleted.                D
900310     DashboardData      crisis_room            A Dashboard data is repositioned.           U
900311     ScheduleRequest    crisis_room            A scheduled task was created.               C
900312     ScheduleRequest    crisis_room            A scheduled task was updated.               U
900313     ScheduleRequest    crisis_room            A scheduled task was deleted.               D
900401     Boefje             katalogus              A boefje was created.                       C
900402     Boefje             katalogus              A boefje was updated.                       U
900403     Boefje             katalogus              A boefje was deleted.                       D
900404     Boefje             katalogus              A KATalogus error occurred                  E
========== ================== ====================== =========================================== =====
