## Rocky (nl-kat)

Rocky is part of the openKAT project, made with Django.
See [nl-kat-coordination](https://github.com/minvws/nl-kat-coordination) for more details about openKAT.

## Stack

As said, Django is the framework for this project.
To comply to government standards, use [Manon](https://github.com/minvws/nl-rdo-manon) for style and accessibility.
Yarn is used as package manager and ParcelJS is used as bundler to compile the frontend (CSS and Javascript).
You can find the Manon repository here: [https://github.com/minvws/nl-rdo-manon](https://github.com/minvws/nl-rdo-manon)

## Running Rocky

### Containerized

To run rocky from the docker container, from the parent directory `nl-kat-coordination`, just run:

```bash
$ make kat
```

and continue reading this document at "First run".

### Locally

To run rocky locally, follow these steps.

### Installation

Yarn is used to bundle CSS and Javascript.
You can build Rocky locally using:

```bash
$ make build
```

This will set up Django and compile the frontend.

### Running

You can run Rocky using:

```bash
$ make run
```

## First run

After running the first time, visit [localhost:8000](http://localhost:8000) in your browser.
Log in with credentials: admin / admin

You will be prompted to create secure your account with a One Time Password, so get your authenticator ready.

## Testing

To run all tests, run:

```bash
$ make test
```

## Database

To connect to the PostgreSQL database, set the following environment variables (e.g. "localhost", "5432" etc.):

```
ROCKY_DB_HOST=
ROCKY_DB_PORT=
ROCKY_DB=
ROCKY_DB_USER=
ROCKY_DB_PASSWORD=
```

## So... How does it flow?

### Perform scan (run boefje)

```mermaid
sequenceDiagram
    participant r as Rocky
    participant c as Scheduler
    participant q as RabbitMQ
    participant b as Boefje
    participant n as Normalizer
    participant o as Octopoes
    r->>+c: Start scan
    c-->>r: task.status = busy
    c->>q: Produce message
    q->>b: Consume message
    q->>n: Consume message
    n->>o: Add object(s)
    c->>-r: task.status = done
```

## KATalogus View Structure

This diagram shows the current view structure and what properties are set in each class for the KATalogus.

```mermaid
%%{ init : {"theme" : "base"}}%%

classDiagram
direction BT
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
    PluginEnableDisableView  <|--  SinglePluginView
    PluginSettingsAddView  <|--  FormView
    PluginSettingsAddView  <|--  SinglePluginView
    PluginSettingsDeleteView  <|--  SingleSettingView
    PluginSettingsUpdateView  <|--  FormView
    PluginSettingsUpdateView  <|--  SingleSettingView
    PluginSettingsListView  <|--  SinglePluginView
```


## Fonts license

All fonts used within Rocky remain under their own license. For example: Fredoka, Open Sans & Tabler icons.

For more information check their respective folders for extra/ more specific license (if available) or visit:

### Fredoka
https://fonts.google.com/specimen/Fredoka/about

### Open Sans
https://fonts.google.com/specimen/Open+Sans/about

### Tabler icons
https://tabler-icons.io/
