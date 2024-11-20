from shared import BOT_TREE, DB, ChannelSelector
import discord
from typing import Literal
from discord import app_commands
from discord.ui import View

@BOT_TREE.command(
    name="setup_channel",
    description="Setup prime time and off time channels",
)
@app_commands.describe(
    channel_type='Is it for prime time or off time?',
)
async def setupChannel(interaction: discord.Interaction, channel_type: Literal["Prime Time", "Off Time"]):
    """Send a message to a channel chosen by the user"""
    # Get all text channels in the guild
    channels = interaction.guild.text_channels
    
    # Create the ChannelSelector select menu and view
    select_menu = ChannelSelector(channels, channel_type)
    view = View(timeout=None)
    view.add_item(select_menu)
    
    # Send a message with the dropdown menu
    await interaction.response.send_message("Choose a channel to send the message:", view=view, ephemeral=True)

################

# LET THE USER PICK THEIR GUILD
@BOT_TREE.command(
    name="choose_guild",
    description="Choose your guild",
)
async def chooseGuild(interaction: discord.Interaction, guild: Literal["Apes", "Dragon", "Rat"]):
    DB.table("PLAYERS_POINTS").upsert({"id": interaction.user.id, "discord_nick": interaction.user.display_name, "guild": guild}).execute()
    await interaction.response.send_message(f"Your guild is now {guild}", ephemeral=True)

################

# SHOW MY POINTS DKP
@BOT_TREE.command(
    name="my_points",
    description="DKP points of mine",
)
async def myPoints(interaction: discord.Interaction):
    response = DB.table("PLAYERS_POINTS").select("total_points").eq("id", interaction.user.id).execute()
    points = 0 if len(response.data) == 0 else response.data[0]["total_points"]

    await interaction.response.send_message(f"You have {points} points", ephemeral=True)

################

# SHOW ALL PLAYERS DKP
@BOT_TREE.command(
    name="global_points",
    description="DKP points of mine",
)
async def globalPoints(interaction: discord.Interaction, guild: Literal["Apes", "Dragon", "Rat", "All"] = "All"):
    query = DB.table("PLAYERS_POINTS").select("discord_nick", "total_points", "guild").order("total_points", desc=True)
    if guild != "All":
        query.eq("guild", guild)

    response = query.execute()

    msg = ""
    for point in response.data:
        msg += f"**{point['discord_nick']}** ({point['guild']}): {point['total_points']}\n"

    if msg == '':
        await interaction.response.send_message("No one has points yet", ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)