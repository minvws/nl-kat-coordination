from collections.abc import Callable

from scheduler import context, models, schedulers


def new_scheduler(ctx: context.AppContext, scheduler_db: models.Scheduler) -> schedulers.Scheduler | None:
    if scheduler_db.item_type == "boefje":  # FIXME enum
        return schedulers.BoefjeScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation, callback=callback
        )

    if scheduler_db.item_type == "normalizer":  # FIXME enum
        return schedulers.NormalizerScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation, callback=callback
        )

    if scheduler_db.item_type == "report":
        return schedulers.ReportScheduler(
            ctx=ctx, scheduler_id=scheduler_db.id, organisation=scheduler_db.organisation, callback=callback
        )
