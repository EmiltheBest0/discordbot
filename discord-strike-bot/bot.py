import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize bot
intents = discord.Intents.default()
intents.members = True  # Needed for member activity tracking
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store strike counts and reasons
strikes = {}

# Define the allowed channel ID
ALLOWED_CHANNEL_ID = 1314518542464323594  # Replace with your channel ID

# Allowed role IDs (REPLACE WITH YOUR ROLE IDS)
ALLOWED_ROLE_IDS = {
    1314515420606369918,  # Owner
    1322108637224767488,  # Co Owners
    1314963324978335755,  # Community Manager
    1314515420606369915,  # Head of Staff
    1322106210870104146,  # Administrator
    1314515420606369914,  # Moderator
    1317583669082194000   # Head of Developers
}

# Load strike data from file (if it exists)
def load_strikes():
    try:
        with open("strikes.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save strike data to file
def save_strikes():
    with open("strikes.json", "w") as f:
        json.dump(strikes, f, indent=4)

@bot.event
async def on_ready():
    global strikes
    strikes = load_strikes()  # Load existing strike data from file
    print(f'Logged in as {bot.user}')
    print(f'Connected to {len(bot.guilds)} guild(s)')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command.")
        return  # Silently ignore if the command is in the wrong channel

# Check if the command is used in the allowed channel
def check_channel(ctx):
    return ctx.channel.id == ALLOWED_CHANNEL_ID

# Check if the user has one of the allowed roles (using role IDs)
def check_roles(ctx):
    return any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles)

# Combined check: channel + role
def check_permissions(ctx):
    return check_channel(ctx) and check_roles(ctx)

@bot.command(name='strike')
@commands.check(check_permissions)
async def strike(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Give a user a strike with an optional reason."""
    try:
        # Prepare the strike data
        strike_data = {
            "reason": reason,
            "striked_by": ctx.author.name  # Store the username of the person issuing the strike
        }

        # Add the strike to the user's record
        if str(member.id) in strikes:
            strikes[str(member.id)].append(strike_data)  # Append the new strike
        else:
            strikes[str(member.id)] = [strike_data]  # Create a new list for the user

        save_strikes()  # Save the updated strikes
        await ctx.send(f'Striked {member.mention} for: **{reason}**. Total strikes: {len(strikes[str(member.id)])}')

    except Exception as e:
        await ctx.author.send(f"An error occurred while processing the strike: {e}")
        print(f"Error: {e}")

@bot.command(name='strikes')
@commands.check(check_permissions)
async def strikes_list(ctx):
    """List all users with their strikes and reasons."""
    try:
        if not strikes:
            await ctx.send("No strikes have been given yet.")
            return

        message = "**Strike list:**\n"
        for user_id, user_strikes in strikes.items():
            user_mention = f"<@{user_id}>"
            message += f"{user_mention} ({len(user_strikes)} strike{'s' if len(user_strikes) > 1 else ''}):\n"

            for strike in user_strikes:
                message += f" - ({strike['reason']}) **{strike['reason']}**\n   By: {strike['striked_by']}\n"

        await ctx.send(message)

    except Exception as e:
        await ctx.author.send(f"An error occurred while fetching the strikes: {e}")
        print(f"Error: {e}")

@bot.command(name='strikedelete')
@commands.check(check_permissions)
async def strikedelete(ctx, member: discord.Member, amount: int = None):
    """Delete a user's strikes (all or a specific amount)."""
    try:
        user_id = str(member.id)
        if user_id not in strikes:
            await ctx.send(f"{member.mention} has no strikes.")
            return

        if amount is None or amount >= len(strikes[user_id]):  # Delete all strikes
            del strikes[user_id]
            save_strikes()
            await ctx.send(f"All strikes for {member.mention} have been deleted.")
        else:  # Remove a specific number of strikes
            removed_strikes = strikes[user_id][:amount]  # Get the strikes being removed
            strikes[user_id] = strikes[user_id][amount:]  # Keep the remaining strikes
            save_strikes()
            removed_reasons_text = "\n".join([f"- {s['reason']} (Striked by: {s['striked_by']})" for s in removed_strikes])
            await ctx.send(f"Deleted {amount} strike(s) from {member.mention}. Remaining strikes: {len(strikes[user_id])}\nRemoved strikes:\n{removed_reasons_text}")

    except Exception as e:
        await ctx.author.send(f"An error occurred while deleting strikes: {e}")
        print(f"Error: {e}")

@bot.command(name='clearstrikes')
@commands.check(check_permissions)
async def clear_strikes(ctx):
    """Clear all strikes for all users."""
    try:
        strikes.clear()
        save_strikes()
        await ctx.send("All strikes have been cleared.")

    except Exception as e:
        await ctx.author.send(f"An error occurred while clearing strikes: {e}")
        print(f"Error: {e}")

# Run the bot using your token (REMOVE YOUR TOKEN FROM PUBLIC CODE!)
bot.run(TOKEN)
