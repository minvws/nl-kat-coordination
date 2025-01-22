---
authors: Donny Peeters (@donnype)
state: { draft }
discussion: http://github.com/nl-kat-coordination/rfd/pull/{number}
labels: reporting, performance, architecture
---

# RFD 0004: Reporting

## Introduction

More than a year ago we were rewriting our reporting service (Keiko) as a more flexible service in Rocky
[
    https://github.com/minvws/nl-kat-coordination/issues/492,
    https://github.com/minvws/nl-kat-coordination/issues/1623,
    https://github.com/minvws/nl-kat-coordination/issues/1713,
    https://github.com/minvws/nl-kat-coordination/issues/1735,
    https://github.com/minvws/nl-kat-coordination/issues/2034
].
There was quite some pressure to deliver this feature,
so we knowingly cut some corners in terms of both documentation, technical design and implementation.
Especially aggregate reports were quite cumbersome
[
    https://github.com/minvws/nl-kat-coordination/issues/2081,
    https://github.com/minvws/nl-kat-coordination/issues/2172
].

Nevertheless, we haven't put much new thought in the foundational data models and architecture of our reporting.
I think we still have to perform a significant cleanup here to understand what's happening better and make it more maintainable.
A few of those considerations are:
- Replace all dictionary-parsing magic with a dataframe-like API.
95% of the reporting data is based on the data type "Finding + OOI".
Most dictionary logic could probably be replaced using a dataframe-like API,
meaning writing `findings_df.groub_by("object_type")` instead of a doubly nested loop.
- Have a better data type for the return value of reports. We should be able to do better than `dict[str, dict[str, Any]]`.

---

Fast-forward a few months and we are designing a new feature on top of our reports: saving reports
[
    https://github.com/minvws/nl-kat-coordination/issues/2397
].
Since we designed a flow in which users can select both oois and report types independently,
we reserved a special place for reports with just one report type and one OOI in our data model.
I believe this was not a good idea, because:
- I see no significant use-case
- It adds a generous amount of complexity.
- It forces us to talk to Octopoes a lot and duplicate a lot of report data.
- It made us special-case everywhere for these "subreports"/"asset_reports" (being fixed as we speak).


---

Fast-forward to now and we have decided to reuse Report OOIs [https://github.com/minvws/nl-kat-coordination/issues/3729].
Although I disagreed with the plan due to the possible consequences,
I'm at peace with the idea that we will change the way we save the Reports,
but feel that I am working on a feature that others will have difficulty understanding and will need a _third_ rewrite in the future.

## The Issue at Hand

The two biggest challenges in reporting are usually: _defining the right metrics_ and _performance_.
I think the current design makes both challenges unreasonably hard.

**Performance** will become challenging because:
- We are saving duplicate data
- We are doing a lot of extra API calls to save the data
- We are aggregating in python-time instead of database-time, and no one understand that code properly anymore.
- We have to fetch "len(input_oois) x len(asset_report_types)" amount of raw files just to show a concatenated report.

**Defining the right metrics** will become challenging because, again, most don't understand the logic.
Those who do will tell you changing an aggregated metric will take a week.

The design is still unintuitive since:
- Report.input_oois does not give us the original oois because we have an asset report per ooi per report type.
- Because of report reusing subreports change independently, hence input data of concatenated reports changes over time.
- Some reports pull from the database (I should say API though), some use a Report, some process AssetReports

In short, it's too difficult to properly iterate on the value of the contents of a report
when all our efforts have to go into making them not break in the first place. 

## Proposal

My proposal is to start prioritizing simplicity.
In my experience, reporting at its simplest is about creating a sophisticated yet static export of (part of) your data.
Also, all reports are somewhat aggregated, so in my eyes an aggregated reports not a special case and should do its own queries.

More concretely, I propose to:
- Drop the notion of "subreports"/"asset reports" now that we are putting a lot of effort into refactoring it.
This will save us at least one future refactor.
- As a consequence we simplify the refactoring scope to reusing reports.
- If there are feature requests for the aggregate report, use it as an excuse to rewrite the aggregate report while we still can.

I thoroughly believe the use-cases we might lose with this change are worth sacrificing for the time saved on future work on reporting,
let alone the performance challenges it will save us when we will have to report on thousands of organisations.
