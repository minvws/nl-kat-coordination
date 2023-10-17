# Design for reports

Currently, there are different ways reports are implemented in Rocky.
We have the report as used in the onboarding view, the findings report (
both for the whole organization as for only a single OOI), and the PDF report in Keiko.

We have a requirements, but as a main goal we want to have one single implementation of reports that is used in OpenKAT.

## Requirements

The requirements of reports are:
- Reports have a single OOI as scope
- Reports have required and suggested plugins that have to be enabled before a report can be generated
- Reports can be downloaded as PDF
- (optional) reports are dependent on a specific version of the data model

## Flow
Front-end flow is being designed.

The backend implementation of reports is not dependent on the flow of generating reports.
In the backend a report is of one type and has one OOI as scope. When multiple reports for multiple OOIs are generated,
this is just a combination of multiple reports combined with a table of contents.


## Implementation
Keiko will be moved from being a separate service to begin a Django app. This has several advantages:
- It can access all Octopoes model information
- Communication does not have to go through APIs
- Keiko can generate HTML view of report directly

Reports will be be implemented similarly to how bits are currently implemented. Each report will have an HTML template,
a manifest/class which will include input OOI types and required plugins. Each report will have to steps of processing data:

- Collecting data
- Generating HTML with aggregates

### Collecting data
There are a few ways in which we will help developers of reports to collect data. They can either do it with a tree (with
filters etc) or using a Path query. These methods are given to the developer as helper functions but developers can also choose
to use a combination of these methods.

### Generating a report
After collecting the data (OOIs) and storing them in an OOI store, developers can calculate some aggregates like averages, traffic lights etc,
and then generating the HTML for that report.

Automatically, the table of contents should also be generated.

After generating the report, we can use some sort of HTML to PDF to let users download PDFs.

### Current Keiko

For the time being, we will not touch the existing Keiko code before completely finishing a V1 for the new reports.
