from typing import Literal
import discord
from discord.ui import Select
from supabase import create_client, Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

MIN_DELAY = 1

EVENT_SCHEDULER = AsyncIOScheduler()

def create_event_trigger(event_at: datetime):
    return DateTrigger(run_date=event_at)

class ChannelSelector(Select):
    global BOT, DB

    def __init__(self, channels, event_type: Literal["Prime Time", "Off Time"]):
        # Create a Select menu for each available text channel
        self.event_type: Literal["Prime Time", "Off Time"] = event_type
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels if isinstance(channel, discord.TextChannel)
        ]
        super().__init__(placeholder="Choose a channel...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Get the selected channel and send the message to it
        selected_channel = BOT.get_channel(int(self.values[0]))
        if selected_channel:
            column = "PRIME_CHANNEL" if self.event_type == "Prime Time" else "OFF_CHANNEL"
            DB.table('BOT_CONFIG').update({column: int(self.values[0])}).eq('ID', 1).execute()
            await interaction.response.send_message(f"{self.event_type} events will be sent to {selected_channel.name}.", ephemeral=True)

# HELPER FUNC TO CREATE THE ACTUAL TIMESTAMP OUT OF INPUTS
def create_datetime(time: str, day: Literal["today", "tomorrow"]) -> datetime:
    # Step 1: Parse the input time string into a datetime object for today
    time_obj = datetime.strptime(time, "%H:%M")
    
    # Step 2: Determine today's date
    today = datetime.today().date()
    
    # Step 3: Adjust the date for 'tomorrow' if specified
    if day == "tomorrow":
        day_obj = today + timedelta(days=1)
    else:
        day_obj = today
    
    # Step 4: Combine the date and time into a full datetime object
    combined_datetime = datetime.combine(day_obj, time_obj.time())
    
    return combined_datetime

def is_prime_time(event_at: datetime):
    return event_at.hour >= 17 and event_at.hour <= 22

def get_event_time(event_at: datetime) -> Literal["Prime Time", "Off Time"]:
    return "Prime Time" if is_prime_time(event_at) else "Off Time"

def get_notification_channel(event_type: Literal["Prime Time", "Off Time"]) -> int:
    column = "PRIME_CHANNEL" if event_type == "Prime Time" else "OFF_CHANNEL"
    response = DB.table('BOT_CONFIG').select(column).eq('ID', 1).execute()
    return None if len(response.data) == 0 else response.data[0][column]

def get_event_by_datetime(event_at: datetime):
    response = DB.table("SCHEDULED_EVENTS").select("*").eq('event_at', event_at.isoformat()).execute()
    return None if len(response.data) == 0 else response.data[0]

GAME_TYPES = Literal["Dynamic Event", "World Boss", "Archboss", "Boonstone", "Riftstone", "Siege"]

GAME_EV_TYPES = {
    "Dynamic Event": 5,
    "World Boss": 5,
    "Archboss": 25,
    "Boonstone": 25,
    "Riftstone": 25,
    "Siege": 100
}

def get_event_points(ev: GAME_TYPES):
    return 0 if GAME_EV_TYPES[ev] is None else GAME_EV_TYPES[ev]


BOT: discord.Client = None
BOT_TREE: discord.app_commands.CommandTree = None
DB: Client = None

def setup_bot():
    global BOT, BOT_TREE, DB

    # Your Supabase Project URL and API Key
    _URL = "https://nolllwzddzzrwiaeklvu.supabase.co"
    _KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5vbGxsd3pkZHp6cndpYWVrbHZ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIwNTUzNDIsImV4cCI6MjA0NzYzMTM0Mn0.PYrepve4ob3ficIFzA6RZexMVd_IyeWvj9wPRU70YCY"

    DB = create_client(_URL, _KEY)

    # setting up the bot
    _INTENTS = discord.Intents.all()

    # if you don't want all intents you can do discord.Intents.default()
    BOT = discord.Client(intents=_INTENTS)
    BOT_TREE = discord.app_commands.CommandTree(BOT)

setup_bot()