from shared import BOT, BOT_TREE, DB, EVENT_SCHEDULER, create_event_trigger, MIN_DELAY
import get_points # needed to register points commands
import events # needed to register events commands
from events import on_event_started
from datetime import datetime, timedelta

def schedule_events_timers():
    now = datetime.now()
    start_at = now - timedelta(minutes=1)
    response = DB.table("SCHEDULED_EVENTS").select("*").gte("event_at", start_at.isoformat()).execute()
    events = response.data

    for event in events:
        event_at = datetime.fromisoformat(event["event_at"])
        dt_notification = event_at - timedelta(minutes=MIN_DELAY)
        if dt_notification > now:
            dt_notification = now + timedelta(minutes=1)

        trigger = create_event_trigger(dt_notification)
        EVENT_SCHEDULER.add_job(on_event_started, trigger, args=[event_at])

    EVENT_SCHEDULER.start()

@BOT.event
async def on_ready():
    await BOT_TREE.sync()
    schedule_events_timers()
    print("Bot up and running!")

BOT.run('MTMwODUxOTIxMzQ1NDk4NzMzNg.GRb-oO.TqA5FkZuRuLl9L5-5eGDsIP3HOKZff-98Vagzc')
