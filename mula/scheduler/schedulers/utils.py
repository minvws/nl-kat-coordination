from scheduler import context, models, schedulers


def new_scheduler(ctx: context.AppContext, scheduler_db: models.Scheduler) -> schedulers.Scheduler:
    if scheduler_db.item_type == models.SchedulerType.BOEFJE:
        return schedulers.BoefjeScheduler(ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation)

    if scheduler_db.item_type == models.SchedulerType.NORMALIZER:
        return schedulers.NormalizerScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation
        )

    if scheduler_db.item_type == models.SchedulerType.REPORT:
        return schedulers.ReportScheduler(ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation)
