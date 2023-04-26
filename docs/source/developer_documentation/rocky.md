# Rocky Design

## Running a boefje

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

### Overview of child Views of the OrganizationViews

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



### Exhaustive overview of OctopoesViews

```{mermaid}
classDiagram
direction RL
    class OrganizationView
    class OctopoesView
    class BoefjeMixin

    OctopoesView <|-- OrganizationView

    BoefjeMixin <|-- OctopoesView
    PluginDetailView <|-- BoefjeMixin
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


### KATalogus Views

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

    class PluginSettingsUpdateView
    class PluginSettingsDeleteView
    class PluginDetailView

    KATalogusView  <|--  OrganizationView
    KATalogusView  <|--  FormView
    SinglePluginView  <|--  OrganizationView
    SingleSettingView  <|--  SinglePluginView
    PluginDetailView  <|--  PluginSettingsListView
    PluginDetailView  <|--  BoefjeMixin
    PluginEnableDisableView  <|--  SinglePluginView
    PluginSettingsAddView  <|--  FormView
    PluginSettingsAddView  <|--  SinglePluginView
    PluginSettingsDeleteView  <|--  SingleSettingView
    PluginSettingsUpdateView  <|--  FormView
    PluginSettingsUpdateView  <|--  SingleSettingView
    PluginSettingsListView  <|--  SinglePluginView
```
