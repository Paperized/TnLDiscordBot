from shared import BOT, BOT_TREE, DB, get_event_points, GAME_TYPES, get_event_by_datetime, get_notification_channel, get_event_time, create_event_trigger, EVENT_SCHEDULER, create_datetime, MIN_DELAY
import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import Literal

# BOT SHARE ALL THE EVENTS FOR THE DAY
@BOT_TREE.command(
    name="share_events",
    description="Share all events for the day",
)
async def shareEvents(interaction: discord.Interaction):
    # Define the time range for the filter (6 AM to 1 AM)
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)  # Today's midnight UTC

    # Define the start and end time ranges (6 AM to 1 AM)
    start_time = start_of_day + timedelta(hours=6)  # 6 AM today
    end_time = start_of_day + timedelta(days=1, hours=5, minutes=59)  # 1 AM the next day
    
    # Fetch events between 6 AM today and 1 AM the next day (adjusted for UTC or your local timezone)
    response = DB.table("SCHEDULED_EVENTS").select("*").gte("event_at", start_time.isoformat()).lte("event_at", end_time.isoformat()).order("event_at").execute()
    events = response.data

    if len(events) == 0:
        await interaction.response.send_message('No events for the day yet!')
        return
    
    share_text = "@everyone Here are the events for today:\n\n"
    for event in events:
        dt = datetime.fromisoformat(event["event_at"])
        event_time = get_event_time(dt)
        ev_type = event["event_type"]
        
        if event_time == "Prime Time":
            message = f"**{dt.hour:02}:{dt.minute:02} UTC (<t:{int(dt.timestamp())}:R>) `{ev_type}` | {event['description']} >> {get_event_points(ev_type)} DKP**\n\n"
        else:
            message = f"**{dt.hour:02}:{dt.minute:02} UTC** (**<t:{int(dt.timestamp())}:R>**) `{ev_type}` | {event['description']} >> {get_event_points(ev_type)} DKP\n\n"

        share_text += message

    await interaction.response.send_message(share_text)

################

# CREATE NEW INGAME EVENT
@BOT_TREE.command(
    name="event",
    description="Create a new event",
)
@app_commands.describe(
    event_name='Event type',
    description='Any useful info about this event',
    time='What is the time of the event? HH:mm',
    day='Today or Tomorrow (for example night events past midnight)?'
)
async def newEvent(interaction: discord.Interaction, event_name: GAME_TYPES, description: str, time: str, day: Literal["today", "tomorrow"]):
    """Create a new event for the guild"""
    await interaction.response.defer(ephemeral=True)

    dt = create_datetime(time, day)
    if dt < datetime.now():
        await interaction.followup.send('Time and date already passed, the date should be in the future!', ephemeral=True)
        return
    
    event_message_obj = await interaction.original_response()
    event_details = {
        "event_at": dt.isoformat(),
        "event_type": event_name,
        "description": description,
        "created_by": event_message_obj.author.name
    }

    try:
        DB.table('SCHEDULED_EVENTS').insert(event_details).execute()
    except Exception as e:
        # Catch any exception and check if it is related to unique constraint violation
        if 'unique' in str(e).lower():
            await interaction.followup.send('An even already exists for this date and time!', ephemeral=True)

        return

    await interaction.followup.send('Event created!', ephemeral=True)

    dt_notification = dt - timedelta(minutes=MIN_DELAY)
    if dt_notification > datetime.now():
        dt_notification = datetime.now() + timedelta(minutes=1)

    trigger = create_event_trigger(dt)
    EVENT_SCHEDULER.add_job(on_event_started, trigger, args=[dt])

################

async def on_event_started(event_at: datetime):
    event = get_event_by_datetime(event_at)
    if event is None:
        print("Event does not exists")
        return
    
    print("Event started")
    event_time = get_event_time(event_at)
    channel_id = get_notification_channel(event_time)
    channel = BOT.get_channel(channel_id)

    ev_type = event["event_type"]
    if event_time == "Prime Time":
        message = f"**@everyone {ev_type} | {event['description']} >> will start in <t:{int(event_at.timestamp())}:R>, react to this message to receive {get_event_points(ev_type)} DKP after the event!**"
    else:
        message = f"@everyone {ev_type} | {event['description']} >> will start in **<t:{int(event_at.timestamp())}:R>**, react to this message to receive {get_event_points(ev_type)} DKP after the event!"

    sent_message = await channel.send(message)

    DB.table('SCHEDULED_EVENTS').update({'channel_id': channel_id, 'message_id': sent_message.id}).eq('event_at', event_at.isoformat()).execute()

    time_to_dkp = event_at + timedelta(minutes=MIN_DELAY)
    trigger = create_event_trigger(time_to_dkp)
    
    EVENT_SCHEDULER.add_job(on_dkp_given, trigger, args=[event_at])

################

async def on_dkp_given(event_at: datetime):
    event = get_event_by_datetime(event_at)
    if event is None:
        print("Event does not exists")
        return
    
    if event["channel_id"] is None:
        return
    
    channel = BOT.get_channel(event['channel_id'])
    if not channel:
        print("Channel not found")
        return

    try:
        message = await channel.fetch_message(event["message_id"])
    except discord.NotFound:
        print("Message not found")
        return
    
    print("Assigning DKP points")

    users = []
    # Fetch all reactions and users
    for reaction in message.reactions:
        users.extend([{
            "id": user.id,
            "display": user.display_name
        } async for user in reaction.users()])

    if len(users) > 0:
        event_logs = [{
            "id": user["id"],  # Assuming user is a discord.User object
            "discord_nick": user["display"],  # Assuming user is a discord.User object
            "event_at": event_at.isoformat()  # Ensure `event_at` is a datetime object
        } for user in users]

        DB.table('EVENTS_REACTIONS').insert(event_logs).execute()
    
        for user in users:
            update_or_insert_points(user, get_event_points(event["event_type"]))

    await channel.send(f'@everyone Points has been given out!')

################

# HELPER METHOD TO INCREASE PLAYER POINTS
def update_or_insert_points(user, points: int):
    """
    Update points if the user exists; insert a new record if not.
    """
    # Check if the record exists
    existing_user = DB.table("PLAYERS_POINTS").select("total_points").eq("id", user["id"]).execute()
    
    if existing_user.data:
        # If the user exists, update their points
        new_points = existing_user.data[0]['total_points'] + points
        DB.table("PLAYERS_POINTS").update({"total_points": new_points}).eq("id", user["id"]).execute()
    else:
        # If the user does not exist, insert a new record
        DB.table("PLAYERS_POINTS").insert({"id": user["id"], "discord_nick": user["display"], "total_points": points}).execute()
