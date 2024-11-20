from scheduler import context, models, schedulers


def new_scheduler(ctx: context.AppContext, scheduler_db: models.Scheduler) -> schedulers.Scheduler:
    if scheduler_db.type == models.SchedulerType.BOEFJE:
        return schedulers.BoefjeScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation_id=scheduler_db.organisation
        )

    if scheduler_db.type == models.SchedulerType.NORMALIZER:
        return schedulers.NormalizerScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation_id=scheduler_db.organisation
        )

    if scheduler_db.type == models.SchedulerType.REPORT:
        return schedulers.ReportScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation_id=scheduler_db.organisation
        )


def create_schedulers_for_organisation(
    ctx: context.AppContext, organisation_id: str
) -> list[
    schedulers.Scheduler | schedulers.BoefjeScheduler | schedulers.NormalizerScheduler | schedulers.ReportScheduler,
]:
    boefje_scheduler = models.Scheduler(
        id=f"boefje-{organisation_id}",
        enabled=True,
        maxsize=0,
        organisation=organisation_id,
        type=models.SchedulerType.BOEFJE,
        allow_replace=True,
        allow_updates=True,
        allow_priority_updates=True,
    )
    ctx.datastores.scheduler_store.create_scheduler(boefje_scheduler)

    normalizer_scheduler = models.Scheduler(
        id=f"normalizer-{organisation_id}",
        enabled=True,
        maxsize=0,
        organisation=organisation_id,
        type=models.SchedulerType.NORMALIZER,
        allow_replace=True,
        allow_updates=True,
        allow_priority_updates=True,
    )
    ctx.datastores.scheduler_store.create_scheduler(normalizer_scheduler)

    report_scheduler = models.Scheduler(
        id=f"report-{organisation_id}",
        enabled=True,
        maxsize=0,
        organisation=organisation_id,
        type=models.SchedulerType.REPORT,
        allow_replace=True,
        allow_updates=True,
        allow_priority_updates=True,
    )
    ctx.datastores.scheduler_store.create_scheduler(report_scheduler)

    return [
        new_scheduler(ctx, boefje_scheduler),
        new_scheduler(ctx, normalizer_scheduler),
        new_scheduler(ctx, report_scheduler),
    ]
