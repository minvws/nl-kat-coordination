## Rocky

Rocky is part of the openKAT project, made with Django.

### Stack

Django is the framework for this project.
To comply to government standards, use [Manon](https://github.com/minvws/nl-rdo-manon) for style and accessibility.
Yarn is used as package manager and ParcelJS is used as bundler to compile the frontend (CSS and Javascript).
You can find the Manon repository here: [https://github.com/minvws/nl-rdo-manon](https://github.com/minvws/nl-rdo-manon)

### Running Rocky

#### Containerized

To run rocky from the docker container, from the parent directory `nl-kat-coordination`, just run:

```bash
$ make kat
```

and continue reading this document at "First run".

#### Locally

To run rocky locally, follow these steps.

### Installation

Yarn is used to bundle CSS and Javascript.
You can build Rocky locally using:

```bash
$ make build
```

This will set up Django and compile the frontend.

#### Running

You can run Rocky using:

```bash
$ make run
```

#### First run

After running the first time, visit [localhost:8000](http://localhost:8000) in your browser.
Log in with credentials: admin / admin

You will be prompted to create secure your account with a One Time Password, so get your authenticator ready.

#### Testing

To run all tests, run:

```bash
$ make test
```

#### Database

To connect to the PostgreSQL database, set the following environment variables (e.g. "localhost", "5432" etc.):

```
ROCKY_DB_HOST=
ROCKY_DB_PORT=
ROCKY_DB=
ROCKY_DB_USER=
ROCKY_DB_PASSWORD=
ROCKY_DB_DSN=
```

The `ROCKY_DB_DSN` is optional (e.g. `postgresql://username:password@hostname:port/database_name`) and if unset the other DB variables will be used to setup the database connection.

### Fonts license

All fonts used within Rocky remain under their own license. For example: Fredoka, Open Sans & Tabler icons.

For more information check their respective folders for extra/ more specific license (if available) or visit:

#### Fredoka
https://fonts.google.com/specimen/Fredoka/about

#### Open Sans
https://fonts.google.com/specimen/Open+Sans/about

#### Tabler icons
https://tabler-icons.io/

## Rocky Design

### Running a boefje

The following diagram shows the triggered flows when running a Boefje from Rocky.
```{mermaid}
sequenceDiagram
    participant Rocky
    participant Scheduler
    participant Boefje
    participant Bytes
    participant Normalizer
    participant Octopoes
    Rocky->>+Scheduler: Push Boefje Task
    Boefje->>Scheduler: Pull Boefje Task
    Scheduler-->>Rocky: boefje_task.status = dispatched
    Boefje->>Bytes: Save Raw
    Boefje->>Scheduler: boefje_task.status = completed
    Scheduler->>-Rocky: boefje_task.status = completed
    Bytes-->>Scheduler: Raw File Received
    Scheduler->>+Scheduler: Push Normalizer Task
    Normalizer->>Scheduler: Pull Normalizer Task
    Normalizer->>Bytes: Get Raw
    Scheduler-->>Rocky: normalizer_task.status = dispatched
    Normalizer->>Octopoes: Add object(s)
    Normalizer->>Scheduler: normalizer_task.status = completed
    Scheduler->>-Rocky: normalizer_task.status = completed
```


## Rocky View Structure

Rocky has a hierarchical set of views that are not easy to capture in a single diagram.
We therefore made several diagrams to show the most coherent components.

#### Overview of child Views of the OrganizationViews

```{mermaid}
classDiagram
direction RL
    class OrganizationView
    OrganizationView : organization
    OrganizationView : octopoes_api_connector
    OrganizationView : organization_member
    OrganizationView : indemnification_present

    OrganizationView <|-- View
    SinglePluginView <|-- OrganizationView
    BytesRawView <|-- OrganizationView
    Health <|-- OrganizationView
    HealthChecks <|-- OrganizationView
    IndemnificationAddView <|-- OrganizationView
    OctopoesView <|-- OrganizationView
    OOIAddTypeSelectView <|-- OrganizationView
    Report <|-- OrganizationView
    OrganizationDetailView <|-- OrganizationView
    OrganizationMemberEditView <|-- OrganizationView
    DownloadTaskDetail <|-- OrganizationView
    TaskListView <|-- OrganizationView
    UploadCSV <|-- OrganizationView
    UploadRaw <|-- OrganizationView
    ObjectsBreadcrumbsMixin <|-- OrganizationView
    OrganizationMemberBreadcrumbsMixin <|-- OrganizationView
    FindingTypeAddView <|-- OrganizationView
```



#### Exhaustive overview of OctopoesViews

```{mermaid}
classDiagram
direction RL
    class OrganizationView
    class OctopoesView
    class BoefjeMixin

    OctopoesView <|-- OrganizationView

    BoefjeMixin <|-- OctopoesView
    BoefjeDetailView <|-- BoefjeMixin
    OOIDetailView <|-- BoefjeMixin
    OOIDetailView <|-- OOIRelatedObjectAddView
    OOIDetailView <|-- OOIFindingManager
    ChangeClearanceLevel <|-- BoefjeMixin

    SingleOOIMixin <|-- OctopoesView
    SingleOOITreeMixin <|-- SingleOOIMixin

    BaseOOIDetailView <|-- SingleOOITreeMixin
    BaseOOIDetailView <|-- ConnectorFormMixin
    OOIDetailView <|-- BaseOOIDetailView
    OOIFindingListView <|-- OOIFindingManager
    OOIFindingListView <|-- BaseOOIDetailView
    MuteFindingView <|-- BaseOOIDetailView
    BaseReportView <|-- BaseOOIDetailView
    DnsReportView <|-- BaseReportView

    OOIReportView <|-- BaseOOIDetailView
    OOITreeView <|-- BaseOOIDetailView
    OOISummaryView <|-- OOITreeView
    OOIGraphView <|-- OOITreeView

    OOIRelatedObjectManager <|-- SingleOOITreeMixin
    OOIFindingManager <|-- SingleOOITreeMixin
    OOIRelatedObjectAddView <|-- OOIRelatedObjectManager

    OOIReportPDFView <|-- SingleOOITreeMixin
    OnboardingSetupScanOOIDetailView <|-- SingleOOITreeMixin

    BaseOOIFormView <|-- SingleOOIMixin
    OOIDeleteView <|-- SingleOOIMixin

    OnboardingSetupScanOOIAddView <|-- BaseOOIFormView
    OOIEditView <|-- BaseOOIFormView
    OOIAddView <|-- BaseOOIFormView
    FindingAddView <|-- BaseOOIFormView

    MultipleOOIMixin <|-- OctopoesView
    BaseOOIListView <|-- MultipleOOIMixin
    BaseOOIListView <|-- ConnectorFormMixin
    OOIListView <|-- BaseOOIListView
    FindingListView <|-- BaseOOIListView
    OOIListExportView <|-- BaseOOIListView

    ScanProfileDetailView <|-- OOIDetailView
    ScanProfileResetView <|-- OOIDetailView
```


#### KATalogus Views

This diagram shows the current view structure and what properties are set in each class for the KATalogus.

```{mermaid}
classDiagram
direction RL
    class FormView
    class OrganizationView
    class SinglePluginView
    class KATalogusView
    class PluginSettingsAddView
    class PluginEnableDisableView
    class SingleSettingView
    class PluginSettingsListView

    OrganizationView : organization
    OrganizationView : octopoes_api_connector
    OrganizationView : organization_member
    OrganizationView : indemnification_present

    SinglePluginView : katalogus_client
    SinglePluginView : plugin
    SinglePluginView : plugin_schema

    SingleSettingView : setting_name

    class PluginSettingsDeleteView
    class BoefjeDetailView

    KATalogusView  <|--  OrganizationView
    KATalogusView  <|--  FormView
    SinglePluginView  <|--  OrganizationView
    SingleSettingView  <|--  SinglePluginView
    BoefjeDetailView  <|--  PluginSettingsListView
    BoefjeDetailView  <|--  BoefjeMixin
    PluginEnableDisableView  <|--  SinglePluginView
    PluginSettingsAddView  <|--  FormView
    PluginSettingsAddView  <|--  SinglePluginView
    PluginSettingsDeleteView  <|--  SingleSettingView
    PluginSettingsListView  <|--  SinglePluginView
```
