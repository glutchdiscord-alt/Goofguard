import discord
from discord import app_commands
from discord.ext import tasks
import os
import random
import asyncio
import json
import logging
import time
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask
import threading
from werkzeug.serving import WSGIRequestHandler

# Load environment variables
load_dotenv()

# Configure logging for better hosting monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler()  # Output to console for Render logs
    ]
)
logger = logging.getLogger(__name__)

# Suppress Flask development server warnings
logging.getLogger('werkzeug').setLevel(logging.WARNING)
WSGIRequestHandler.log_request = lambda self, code='-', size='-': None

# Bot setup with all necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True

class GoofyMod(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.start_time = time.time()
        self.reconnect_count = 0
        
    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info(f"🤪 {self.user} is getting ready to be goofy!")
        self.update_status.start()
        
    async def on_ready(self):
        """Called when bot is ready"""
        await self.wait_until_ready()
        if not self.synced:
            try:
                await tree.sync()
                self.synced = True
                logger.info("🔄 Slash commands synced successfully!")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
        
        logger.info(f"🎭 Goofy Mod is online and watching over {len(self.guilds)} goofy servers!")
        await self.update_server_status()
        
        # Log hosting stats
        uptime = time.time() - self.start_time
        logger.info(f"✅ Bot fully ready! Uptime: {uptime:.1f}s | Reconnects: {self.reconnect_count}")
        
    async def on_connect(self):
        """Called when bot connects to Discord"""
        logger.info("🔗 Connected to Discord gateway")
        
    async def on_disconnect(self):
        """Called when bot disconnects from Discord"""
        logger.warning("⚠️ Disconnected from Discord gateway")
        
    async def on_resumed(self):
        """Called when bot resumes connection"""
        self.reconnect_count += 1
        logger.info(f"🔄 Resumed connection (reconnect #{self.reconnect_count})")
        
    async def on_error(self, event, *args, **kwargs):
        """Global error handler for bot events"""
        logger.error(f"🚨 Bot error in {event}: {args[0] if args else 'Unknown error'}")
        # Don't let errors crash the bot

    async def update_server_status(self):
        """Update the bot's status to show server count"""
        server_count = len(self.guilds)
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"over {server_count} goofy servers 🤡"
        )
        await self.change_presence(activity=activity)

    @tasks.loop(minutes=10)
    async def update_status(self):
        """Update status every 10 minutes"""
        if self.is_ready():
            await self.update_server_status()

    async def on_guild_join(self, guild):
        """Update status when joining a new server"""
        await self.update_server_status()
        logger.info(f"🎪 Joined a new goofy server: {guild.name}")
        
    async def on_guild_remove(self, guild):
        """Update status when leaving a server"""
        await self.update_server_status()
        logger.info(f"😢 Left server: {guild.name}")


    async def on_member_join(self, member):
        """Handle new member joins with goofy welcome messages"""
        if member.bot:
            return  # Skip bots
        
        welcome_config = load_welcome_config()
        guild_config = welcome_config.get(str(member.guild.id), {})
        
        if not guild_config.get("enabled", False):
            return  # Welcome messages disabled
        
        welcome_channel_id = guild_config.get("channel_id")
        if not welcome_channel_id:
            return  # No welcome channel set
        
        welcome_channel = member.guild.get_channel(welcome_channel_id)
        if not welcome_channel:
            return  # Channel not found
        
        try:
            # Get custom message or use random default
            custom_message = guild_config.get("custom_message")
            if custom_message:
                message = custom_message.format(user=member.mention, username=member.name, server=member.guild.name)
            else:
                message = random.choice(WELCOME_MESSAGES).format(user=member.mention)
            
            embed = discord.Embed(
                title="🎉 New Goofy Human Detected! 🎉",
                description=message,
                color=random.randint(0, 0xFFFFFF)
            )
            
            embed.add_field(
                name="📊 Member Count", 
                value=f"You're member #{member.guild.member_count}!", 
                inline=True
            )
            embed.add_field(
                name="📅 Join Date", 
                value=member.joined_at.strftime("%B %d, %Y"), 
                inline=True
            )
            
            # Add user avatar if available
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            # Random footer messages
            footers = [
                "Welcome to peak brainrot territory!",
                "Remember to touch grass occasionally!",
                "Your vibes will be checked regularly!",
                "Ohio residents get 10% off everything!",
                "Sigma grindset officially activated!",
                "Prepare for maximum chaos energy!"
            ]
            embed.set_footer(text=random.choice(footers))
            
            await welcome_channel.send(embed=embed)
            logger.info(f"🎪 Welcomed {member.name} to {member.guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

# Initialize bot and command tree
bot = GoofyMod()
tree = app_commands.CommandTree(bot)

# Copypasta responses
COPYPASTAS = {
    "navy seal": "What the sigma did you just say about me, you little beta? I'll have you know I graduated top of my class in the Ohio Navy Seals, and I've been involved in numerous secret raids on cringe TikTokers, and I have over 300 confirmed ratios. I am trained in skibidi warfare and I'm the top sniper in the entire US armed forces of brainrot...",
    "rick and morty": "To be fair, you have to have a very high IQ to understand skibidi toilet. The humor is extremely subtle, and without a solid grasp of Ohio physics most of the jokes will go over a typical viewer's head. There's also Rick's nihilistic outlook, which is deftly woven into his characterisation - his personal philosophy draws heavily from sigma male literature, for instance...",
    "among us": "STOP POSTING ABOUT AMONG US! I'M TIRED OF SEEING IT! My friends on TikTok send me memes, on Discord it's memes! I was in a server, right? And ALL the channels are just Among Us stuff. I showed my champion underwear to my girlfriend and the logo I flipped it and said 'Hey babe, when the underwear sus!' HAHA! Ding ding ding ding ding ding ding! Ding ding ding!",
    "is this": "Is this loss? No bestie, this is your L + ratio + you fell off + no rizz + touch grass + Ohio energy + cringe behavior + NPC mindset + beta male + cope + seethe + mald + basic + skill issue"
}

# Daily brainrot facts
BRAINROT_FACTS = [
    "Did you know? Ohio has 47% more brainrot per capita than any other state! 🌽",
    "Fun fact: The average person says 'sus' 23 times per day without realizing it! 📮",
    "Scientific discovery: Skibidi toilet was actually invented by ancient Romans! 🚽",
    "Breaking: Local scientists confirm that touching grass increases rizz by 200%! 🌱",
    "Research shows: People who say 'no cap' are 73% more likely to be capping! 🧢",
    "Studies indicate: Sigma males are just beta males with better marketing! 🐺",
    "Archaeological evidence suggests: Fanum tax existed in ancient Egypt! 🏺",
    "New data reveals: Yapping is actually a form of verbal meditation! 🗣️",
    "Scientists discover: The Ohio dimension is only accessible through Discord! 🌌",
    "Breaking news: Being zesty is now considered an official personality trait! 💅"
]

# Welcome message templates
WELCOME_MESSAGES = [
    "🎪 Welcome to the circus, {user}! Hope you brought your clown nose! 🤡",
    "🚨 ALERT: New human detected! {user} has entered the Ohio dimension! 🌽",
    "📮 {user} looking kinda sus joining at this time... but we vibe with it! 👀",
    "🎭 Ladies and gentlemen, {user} has entered the building! *crowd goes mild* 📢",
    "⚡ BREAKING: {user} discovered this server exists and decided to join! Wild! 🤪",
    "🔥 {user} just spawned in! Welcome to peak brainrot territory bestie! 🧠",
    "🚽 Skibidi welcome to {user}! Your rizz levels will be tested shortly... 💀",
    "🐺 A new challenger approaches! {user} has entered the sigma grindset zone! 💪",
    "👑 {user} really said 'let me join the most chaotic server' and honestly? Respect! ✨",
    "🎮 {user} has joined the game! Current objective: Survive the brainrot! 🎯",
    "💫 {user} is giving main character energy already! Welcome to your new home! 🏠",
    "🌪️ Chaos levels increased by 47%! {user} has joined the mayhem! Welcome! 🔥"
]

# Simple JSON storage for welcome settings and warnings
WELCOME_CONFIG_FILE = "welcome_config.json"
WARNINGS_FILE = "warnings.json"

def load_warnings():
    """Load warnings from JSON file"""
    try:
        if os.path.exists(WARNINGS_FILE):
            with open(WARNINGS_FILE, 'r') as f:
                return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading warnings: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading warnings: {e}")
    return {}

def save_warnings(warnings):
    """Save warnings to JSON file"""
    try:
        with open(WARNINGS_FILE, 'w') as f:
            json.dump(warnings, f, indent=2)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error saving warnings: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving warnings: {e}")

def add_warning(guild_id, user_id, reason, moderator):
    """Add a warning to a user and return warning count"""
    warnings = load_warnings()
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    if guild_str not in warnings:
        warnings[guild_str] = {}
    if user_str not in warnings[guild_str]:
        warnings[guild_str][user_str] = []
    
    warning_data = {
        'reason': reason,
        'moderator': str(moderator),
        'timestamp': time.time()
    }
    
    warnings[guild_str][user_str].append(warning_data)
    save_warnings(warnings)
    
    return len(warnings[guild_str][user_str])

def get_user_warnings(guild_id, user_id):
    """Get warnings for a specific user"""
    warnings = load_warnings()
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    return warnings.get(guild_str, {}).get(user_str, [])

def clear_user_warnings(guild_id, user_id, count=None):
    """Clear warnings for a user (all or specific count)"""
    warnings = load_warnings()
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    if guild_str in warnings and user_str in warnings[guild_str]:
        if count is None:
            warnings[guild_str][user_str] = []
        else:
            # Remove the most recent warnings
            warnings[guild_str][user_str] = warnings[guild_str][user_str][:-count]
        save_warnings(warnings)
        return True
    return False

async def handle_warning_escalation(interaction, member, warning_count):
    """Handle automatic escalation based on warning count"""
    automod_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    # Check if warning escalation is enabled
    warning_config = automod_config.get(guild_id, {}).get('automod', {}).get('warnings', {})
    if not warning_config.get('enabled', False):
        return
    
    max_warnings = warning_config.get('max_warnings', 3)
    action = warning_config.get('action', 'mute')
    
    if warning_count >= max_warnings:
        escalation_messages = [
            f"Bro got {warning_count} warnings and thought they were untouchable! 😂",
            f"That's {warning_count} strikes - you're OUT! ⚾",
            f"Warning overload detected! Time for the consequences! 🚨",
            f"{warning_count} warnings?? Your vibes are NOT it chief! 💯",
            f"Bruh collected warnings like Pokémon cards - gotta punish 'em all! 🃏"
        ]
        
        embed = discord.Embed(
            title="⚠️ Auto-Escalation Triggered!",
            description=random.choice(escalation_messages),
            color=0xFF4500
        )
        
        try:
            if action == 'mute':
                mute_duration = discord.utils.utcnow() + timedelta(minutes=30)  # 30 min auto-mute
                await member.edit(timed_out_until=mute_duration, reason=f"Auto-mute: {warning_count} warnings reached")
                embed.add_field(name="🎤 Action Taken", value="Muted for 30 minutes", inline=True)
            elif action == 'kick':
                await member.kick(reason=f"Auto-kick: {warning_count} warnings reached")
                embed.add_field(name="🦶 Action Taken", value="Kicked from server", inline=True)
            elif action == 'ban':
                await member.ban(reason=f"Auto-ban: {warning_count} warnings reached")
                embed.add_field(name="🔨 Action Taken", value="Banned from server", inline=True)
            
            embed.add_field(name="📈 Warning Count", value=f"{warning_count}/{max_warnings}", inline=True)
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send("Tried to auto-escalate but I don't have permission! 😭", ephemeral=True)
        except Exception as e:
            logger.error(f"Auto-escalation error: {e}")

def load_welcome_config():
    """Load welcome configuration from JSON file"""
    try:
        if os.path.exists(WELCOME_CONFIG_FILE):
            with open(WELCOME_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading welcome config: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
    return {}

def save_welcome_config(config):
    """Save welcome configuration to JSON file"""
    try:
        with open(WELCOME_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error saving welcome config: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving config: {e}")

# Goofy responses for different situations
GOOFY_RESPONSES = {
    'ban': [
        "🔨 *bonk* They've been yeeted to the shadow realm! 👻",
        "🚪 And they said 'I must go, my planet needs me' *banned*",
        "⚡ ZAP! They got Thanos snapped! 🫰",
        "🎪 Ladies and gentlemen, they have left the building! 📢",
        "🌪️ They got swept away by the ban hammer tornado!",
        "💀 Bro really thought they could be zesty in here and get away with it",
        "🚫 That's not very skibidi of you, now you're banned fr fr",
        "⚰️ RIP bozo, got absolutely ratioed by the ban hammer",
        "🤡 Imagine getting banned, couldn't be me... oh wait it's literally you",
        "🧻 Your vibes were NOT it chief, time to touch grass permanently"
    ],
    'kick': [
        "🦶 *kick* They've been punted like a football! 🏈",
        "🚀 Houston, we have a problem... they're in orbit now! 🛸",
        "👋 They said 'see ya later alligator' but we said 'bye bye!' 🐊",
        "🎈 Whoosh! They floated away like a balloon! 🎈",
        "⚽ GOOOOOAL! They've been kicked out of bounds!",
        "🎪 Bro got absolutely YOINKED out of existence",
        "💨 They said 'it's giving main character energy' but got kicked instead",
        "🏃‍♂️ Time to touch grass buddy, you've been EJECTED",
        "🎭 That was lowkey sus behavior, now they're highkey gone",
        "⭐ No cap, they got sent to the backrooms fr"
    ],
    'mute': [
        "🤐 Shhhh! They're in quiet time now! 🤫",
        "🔇 They've entered the silent treatment zone! 🙊",
        "🤐 Their vocal cords have been temporarily yeeted! 🎤❌",
        "🕳️ They fell into the quiet hole! *muffled screams*",
        "🧙‍♂️ *waves magic wand* SILENCIO! ✨",
        "🗣️ Bro was yapping too much, now it's silent hours",
        "🤫 Your Ohio energy was too powerful, time for a break",
        "💀 Stop the cap! Muted for being too zesty",
        "📵 Skibidi toilet broke so now you can't speak either",
        "🧠 Brainrot levels were off the charts, cooling down required"
    ],
    'warn': [
        "⚠️ That's a yellow card! ⚠️ One more and you're outta here! 🟨",
        "📢 *blows whistle* FOUL! That's a warning! 🏈",
        "👮‍♂️ This is your friendly neighborhood warning! 🕷️",
        "⚠️ Beep beep! Warning truck coming through! 🚛",
        "🚨 Alert! Alert! Someone's being a little too spicy! 🌶️",
        "🤨 That was sus behavior ngl, this is your warning",
        "💅 Bestie that wasn't very demure or mindful of you",
        "🧠 Your vibes are giving negative aura points rn",
        "⚡ Bro thinks they're the main character but this is their warning arc",
        "🎪 That energy was NOT it, consider this your reality check"
    ],
    'purge': [
        "🧹 *whoosh* Messages go brrrr and disappear! 💨",
        "🗑️ Taking out the trash! 🚮",
        "🌪️ Message tornado activated! Everything's gone! 🌀",
        "✨ *snaps fingers* Perfectly balanced, as all things should be 🫰",
        "🧽 Scrub-a-dub-dub, cleaning the chat tub! 🛁",
        "💀 Chat got absolutely obliterated, no cap",
        "🌊 Skibidi toilet flush activated, everything's gone",
        "⚡ Those messages were NOT giving what they were supposed to give",
        "🗑️ Taking out the brainrot, one message at a time",
        "🎪 Chat just got sent to the shadow realm fr"
    ]
}

RANDOM_GOOFY_RESPONSES = [
    "That's more sus than a lime green crewmate! 🟢",
    "Bruh that's bussin fr fr no cap! 💯",
    "That hits different though ngl 😤",
    "Sir this is a Wendy's 🍔",
    "No thoughts, head empty 🗿",
    "It's giving main character energy ✨",
    "I'm deceased 💀💀💀",
    "That's not very cash money of you 💸",
    "Periodt! 💅",
    "And I took that personally 😤",
    "Skibidi bop bop yes yes! 🚽",
    "That's giving Ohio energy fr 🌽",
    "Bro is absolutely YAPPING right now 🗣️",
    "You're lowkey being zesty rn bestie 💅",
    "This ain't it chief, negative aura points 📉",
    "Bro thinks they're sigma but they're actually beta 🐺",
    "That's cap and you know it 🧢",
    "Stop the yap session bestie 🤐",
    "Your rizz levels are in the negatives 📊",
    "Bro got that NPC behavior 🤖",
    "That's absolutely sending me to orbit 🚀",
    "Gyatt dayum that's crazy 😳",
    "Bro is NOT the chosen one 👑❌",
    "Your vibes are giving basement dweller 🏠",
    "That's more mid than room temperature water 🌡️"
]

# Slash Commands
@tree.command(name='ban', description='Ban a member with goofy flair 🔨')
@app_commands.describe(
    member='The member to ban',
    reason='The reason for the ban (default: Being too serious in a goofy server)'
)
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "Being too serious in a goofy server"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    try:
        await member.ban(reason=f"Banned by {interaction.user}: {reason}")
        response = random.choice(GOOFY_RESPONSES['ban'])
        embed = discord.Embed(
            title="🔨 BONK! Ban Hammer Activated!",
            description=f"{response}\n\n**Banned:** {member.mention}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("Oop! I don't have permission to ban that person! 😅", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Something went wrong! Error: {str(e)} 🤪", ephemeral=True)

@tree.command(name='kick', description='Kick a member with style 🦶')
@app_commands.describe(
    member='The member to kick',
    reason='The reason for the kick (default: Needs a time-out)'
)
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "Needs a time-out"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    try:
        await member.kick(reason=f"Kicked by {interaction.user}: {reason}")
        response = random.choice(GOOFY_RESPONSES['kick'])
        embed = discord.Embed(
            title="🦶 YEET! Kick Activated!",
            description=f"{response}\n\n**Kicked:** {member.mention}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("I can't kick that person! They're too powerful! 💪", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Oopsie doopsie! Error: {str(e)} 🙃", ephemeral=True)

def parse_duration(duration_str):
    """Parse duration string like '5m', '2h', '1d' into minutes. Returns None for permanent mute."""
    if not duration_str or duration_str.lower() in ['perm', 'permanent', 'forever', 'inf', 'infinite']:
        return None  # Permanent mute
    
    duration_str = duration_str.lower().strip()
    
    try:
        if duration_str.endswith('m'):
            return int(duration_str[:-1])  # minutes
        elif duration_str.endswith('h'):
            return int(duration_str[:-1]) * 60  # hours to minutes
        elif duration_str.endswith('d'):
            return int(duration_str[:-1]) * 60 * 24  # days to minutes
        elif duration_str.isdigit():
            return int(duration_str)  # assume minutes if just number
        else:
            return None  # Invalid format = permanent
    except ValueError:
        return None  # Invalid format = permanent

@tree.command(name='mute', description='Mute a member (permanent by default) 🤐')
@app_commands.describe(
    member='The member to mute',
    duration='Duration (5m, 2h, 1d) or leave empty for permanent',
    reason='The reason for the mute (default: Being too loud)'
)
async def mute_slash(interaction: discord.Interaction, member: discord.Member, duration: str = "", reason: str = "Being too loud"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    try:
        # Parse duration
        duration_minutes = parse_duration(duration)
        
        if duration_minutes is None:
            # Permanent mute (Discord max timeout is 28 days, so we use that)
            mute_duration = discord.utils.utcnow() + timedelta(days=28)
            duration_display = "PERMANENT (until unmuted) ♾️"
        else:
            mute_duration = discord.utils.utcnow() + timedelta(minutes=duration_minutes)
            if duration_minutes >= 1440:  # 1 day or more
                days = duration_minutes // 1440
                hours = (duration_minutes % 1440) // 60
                duration_display = f"{days}d {hours}h" if hours > 0 else f"{days}d"
            elif duration_minutes >= 60:  # 1 hour or more
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                duration_display = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            else:
                duration_display = f"{duration_minutes}m"
        
        await member.edit(timed_out_until=mute_duration, reason=f"Muted by {interaction.user}: {reason}")
        
        response = random.choice(GOOFY_RESPONSES['mute'])
        embed = discord.Embed(
            title="🤐 Shhh! Mute Activated!",
            description=f"{response}\n\n**Muted:** {member.mention}\n**Duration:** {duration_display}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            color=0x808080
        )
        embed.add_field(
            name="💡 Pro Tip",
            value="Use formats like `5m`, `2h`, `1d` or leave empty for permanent!",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("I can't mute that person! They have super hearing! 👂", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Mute machine broke! Error: {str(e)} 🔇", ephemeral=True)

@tree.command(name='unmute', description='Unmute a member 🔊')
@app_commands.describe(member='The member to unmute')
async def unmute_slash(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    try:
        await member.edit(timed_out_until=None, reason=f"Unmuted by {interaction.user}")
        embed = discord.Embed(
            title="🔊 Freedom! Unmute Activated!",
            description=f"🎉 {member.mention} can speak again! Their vocal cords have been restored! 🗣️",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Unmute machine is jammed! Error: {str(e)} 🔧", ephemeral=True)

@tree.command(name='warn', description='Give a member a goofy warning ⚠️')
@app_commands.describe(
    member='The member to warn',
    reason='The reason for the warning (default: General goofiness)'
)
async def warn_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "General goofiness"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    # Add warning to database
    warning_count = add_warning(interaction.guild.id, member.id, reason, interaction.user.id)
    
    response = random.choice(GOOFY_RESPONSES['warn'])
    embed = discord.Embed(
        title="⚠️ Warning Issued!",
        description=f"{response}\n\n**Warned:** {member.mention}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
        color=0xFFFF00
    )
    embed.add_field(
        name="📈 Warning Count",
        value=f"{warning_count} warning{'s' if warning_count != 1 else ''}",
        inline=True
    )
    
    # Add warning level indicator
    if warning_count == 1:
        embed.add_field(name="🔥 Status", value="First strike!", inline=True)
    elif warning_count == 2:
        embed.add_field(name="🔥 Status", value="Getting spicy! 🌶️", inline=True)
    elif warning_count >= 3:
        embed.add_field(name="🔥 Status", value="DANGER ZONE! 🚨", inline=True)
    
    await interaction.response.send_message(embed=embed)
    
    # Check for auto-escalation
    await handle_warning_escalation(interaction, member, warning_count)

@tree.command(name='unwarn', description='Remove warnings from a member ✨')
@app_commands.describe(
    member='The member to unwarn',
    count='Number of warnings to remove (default: 1)',
    reason='The reason for removing the warnings (default: They learned their lesson)'
)
async def unwarn_slash(interaction: discord.Interaction, member: discord.Member, count: int = 1, reason: str = "They learned their lesson"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    # Get current warnings
    current_warnings = get_user_warnings(interaction.guild.id, member.id)
    if not current_warnings:
        await interaction.response.send_message(f"{member.mention} has no warnings to remove! They're already an angel! 😇", ephemeral=True)
        return
    
    # Remove warnings
    warnings_to_remove = min(count, len(current_warnings))
    clear_user_warnings(interaction.guild.id, member.id, warnings_to_remove)
    
    # Get new warning count
    remaining_warnings = len(current_warnings) - warnings_to_remove
    
    unwarn_responses = [
        "✨ Warning yeeted into the void! They're clean now! 🧽",
        "🎆 *POOF* Warning disappeared like their common sense! ✨",
        "🔄 Plot twist: They were never warned! Reality has been altered! 🌌",
        "🧙‍♂️ *waves magic wand* FORGIVENESS ACTIVATED! ✨",
        "🎈 Warning balloon has been popped! Clean slate bestie! 🎉",
        "🛡️ Warning shield has been removed! They're vulnerable again! 😬",
        "🚫 Warning.exe has stopped working! Fresh start loaded! 🔄"
    ]
    
    response = random.choice(unwarn_responses)
    embed = discord.Embed(
        title="✨ Warning Removed!",
        description=f"{response}\n\n**Unwarned:** {member.mention}\n**Removed:** {warnings_to_remove} warning{'s' if warnings_to_remove != 1 else ''}\n**Remaining:** {remaining_warnings} warning{'s' if remaining_warnings != 1 else ''}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
        color=0x00FF88
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='warnings', description='View warnings for a member 📄')
@app_commands.describe(member='The member to check warnings for')
async def warnings_slash(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    warnings = get_user_warnings(interaction.guild.id, member.id)
    
    if not warnings:
        clean_messages = [
            f"{member.mention} is cleaner than Ohio tap water! No warnings found! 💧",
            f"{member.mention} has zero warnings - they're giving angel energy! 😇",
            f"Warning count: 0. {member.mention} is more innocent than a newborn! 👶",
            f"{member.mention} has no warnings - they're built different! 💯",
            f"This user is warning-free - absolute chad behavior! 👑"
        ]
        await interaction.response.send_message(random.choice(clean_messages), ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📄 Warning History for {member.display_name}",
        color=0xFFAA00
    )
    
    embed.add_field(
        name="📊 Total Warnings",
        value=f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''}",
        inline=True
    )
    
    # Warning level indicator
    if len(warnings) == 1:
        status = "🔥 First offense"
    elif len(warnings) == 2:
        status = "🌶️ Getting spicy"
    elif len(warnings) >= 3:
        status = "🚨 DANGER ZONE"
    else:
        status = "✅ Clean slate"
    
    embed.add_field(name="🏷️ Status", value=status, inline=True)
    
    # Show recent warnings (last 5)
    recent_warnings = warnings[-5:]
    warning_text = ""
    
    for i, warning in enumerate(reversed(recent_warnings), 1):
        timestamp = warning.get('timestamp', time.time())
        date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))
        warning_text += f"**{i}.** {warning['reason']}\n*{date_str}*\n\n"
    
    if warning_text:
        embed.add_field(
            name=f"📋 Recent Warnings (Last {len(recent_warnings)})",
            value=warning_text[:1024],  # Discord field limit
            inline=False
        )
    
    if len(warnings) > 5:
        embed.set_footer(text=f"Showing last 5 of {len(warnings)} total warnings")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name='clearwarnings', description='Clear all warnings for a member 🧹')
@app_commands.describe(member='The member to clear warnings for')
async def clearwarnings_slash(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    warnings = get_user_warnings(interaction.guild.id, member.id)
    if not warnings:
        await interaction.response.send_message(f"{member.mention} already has zero warnings! Can't clear what doesn't exist bestie! 🤷‍♂️", ephemeral=True)
        return
    
    clear_user_warnings(interaction.guild.id, member.id)
    
    clear_messages = [
        f"🧹 Wiped {member.mention}'s slate cleaner than my search history!",
        f"✨ {member.mention} got the factory reset treatment - all warnings GONE!",
        f"💨 *POOF* {len(warnings)} warnings vanished into thin air!",
        f"🎆 Warning database has been YOINKED clean for {member.mention}!",
        f"🔄 {member.mention} just got a fresh start - warnings = 0!"
    ]
    
    embed = discord.Embed(
        title="🧹 All Warnings Cleared!",
        description=random.choice(clear_messages),
        color=0x00FF00
    )
    embed.add_field(
        name="📊 Warnings Removed",
        value=f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''}",
        inline=True
    )
    embed.add_field(
        name="👮 Moderator",
        value=interaction.user.mention,
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='purge', description='Delete messages from chat 🧹')
@app_commands.describe(amount='Number of messages to delete (max 100, default 10)')
async def purge_slash(interaction: discord.Interaction, amount: int = 10):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    if amount > 100:
        await interaction.response.send_message("Whoa there! That's too many messages! Max is 100! 🛑", ephemeral=True)
        return
    
    try:
        # Defer response since purging might take time
        await interaction.response.defer()
        
        deleted = await interaction.channel.purge(limit=amount)
        response = random.choice(GOOFY_RESPONSES['purge'])
        
        embed = discord.Embed(
            title="🧹 Cleanup Complete!",
            description=f"{response}\n\n**Messages deleted:** {len(deleted)}\n**Janitor:** {interaction.user.mention}",
            color=0x00FFFF
        )
        
        msg = await interaction.followup.send(embed=embed)
        await asyncio.sleep(5)  # Auto-delete after 5 seconds
        await msg.delete()
        
    except discord.Forbidden:
        await interaction.followup.send("I can't delete messages! My broom is broken! 🧹💔", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Cleaning machine broke! Error: {str(e)} 🤖", ephemeral=True)

# Auto-Moderation Commands
@tree.command(name='automod', description='Configure auto-moderation settings 🤖')
@app_commands.describe(
    feature='Auto-mod feature to configure',
    enabled='Enable or disable the feature',
    action='Action to take when triggered',
    max_warnings='Max warnings before auto-action (for warning-based features)'
)
@app_commands.choices(
    feature=[
        app_commands.Choice(name='Spam Detection', value='spam'),
        app_commands.Choice(name='Excessive Caps', value='caps'),
        app_commands.Choice(name='Mass Mentions', value='mentions'),
        app_commands.Choice(name='Repeated Messages', value='repeat'),
        app_commands.Choice(name='Warning Escalation', value='warnings')
    ],
    action=[
        app_commands.Choice(name='Warn Only', value='warn'),
        app_commands.Choice(name='Mute (10m)', value='mute'),
        app_commands.Choice(name='Kick', value='kick'),
        app_commands.Choice(name='Ban', value='ban')
    ]
)
async def automod_slash(interaction: discord.Interaction, feature: str, enabled: bool, action: str = 'warn', max_warnings: int = 3):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    # Load or create automod config
    automod_config = load_welcome_config()  # Reuse the same JSON storage
    guild_id = str(interaction.guild.id)
    
    if guild_id not in automod_config:
        automod_config[guild_id] = {}
    if 'automod' not in automod_config[guild_id]:
        automod_config[guild_id]['automod'] = {}
    
    # Store both enabled status and action
    automod_config[guild_id]['automod'][feature] = {
        'enabled': enabled,
        'action': action,
        'max_warnings': max_warnings
    }
    save_welcome_config(automod_config)
    
    feature_names = {
        'spam': 'Spam Detection 📧',
        'caps': 'Excessive Caps 🔠',
        'mentions': 'Mass Mentions 📢',
        'repeat': 'Repeated Messages 🔁',
        'warnings': 'Warning Escalation ⚠️'
    }
    
    action_names = {
        'warn': 'Warn Only ⚠️',
        'mute': 'Mute (10m) 🤐',
        'kick': 'Kick 🦶',
        'ban': 'Ban 🔨'
    }
    
    status = "enabled" if enabled else "disabled"
    emoji = "✅" if enabled else "❌"
    
    embed = discord.Embed(
        title=f"{emoji} Auto-Mod Updated!",
        description=f"**{feature_names[feature]}** is now **{status}**!",
        color=0x00FF00 if enabled else 0xFF0000
    )
    
    if enabled:
        embed.add_field(
            name="🎯 Action",
            value=action_names[action],
            inline=True
        )
        if feature == 'warnings':
            embed.add_field(
                name="📊 Max Warnings",
                value=f"{max_warnings} strikes",
                inline=True
            )
        
    goofy_messages = [
        "Time to unleash the chaos police! 😈",
        "Bro thinks they can break rules? Not on my watch! 👀",
        "About to serve some digital justice with extra salt! 🧂",
        "Rule breakers getting ratio'd by the bot police! 💯",
        "Your server's about to be cleaner than Ohio tap water! 💧"
    ]
    
    embed.add_field(
        name="🤖 GoofGuard Auto-Mod", 
        value=random.choice(goofy_messages), 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='automodstatus', description='Check auto-moderation configuration 📋')
async def automodstatus_slash(interaction: discord.Interaction):
    automod_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    guild_automod = automod_config.get(guild_id, {}).get('automod', {})
    
    embed = discord.Embed(
        title="🤖 GoofGuard Auto-Mod Status",
        description="Here's what I'm watching for!",
        color=0x7289DA
    )
    
    features = {
        'spam': 'Spam Detection 📧',
        'caps': 'Excessive Caps 🔠',
        'mentions': 'Mass Mentions 📢',
        'repeat': 'Repeated Messages 🔁'
    }
    
    for key, name in features.items():
        status = guild_automod.get(key, False)
        emoji = "✅" if status else "❌"
        embed.add_field(
            name=name,
            value=f"{emoji} {'Enabled' if status else 'Disabled'}",
            inline=True
        )
    
    embed.set_footer(text="Use /automod to configure these settings!")
    await interaction.response.send_message(embed=embed)

@tree.command(name='serverinfo', description='Show server information with goofy flair 📊')
async def serverinfo_slash(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server! 🏠", ephemeral=True)
        return
    embed = discord.Embed(
        title=f"📊 {guild.name} - The Goofy Stats!",
        color=0x7289DA
    )
    embed.add_field(name="👥 Total Humans", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Server Birthday", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="👑 Server Overlord", value=guild.owner.mention, inline=True)
    embed.add_field(name="🌟 Boost Level", value=guild.premium_tier, inline=True)
    embed.add_field(name="💎 Boosters", value=guild.premium_subscription_count, inline=True)
    embed.add_field(name="📝 Channels", value=len(guild.channels), inline=True)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

# Additional moderation commands
@tree.command(name='slowmode', description='Set channel slowmode with goofy flair ⏰')
@app_commands.describe(seconds='Seconds between messages (0 to disable)')
async def slowmode_slash(interaction: discord.Interaction, seconds: int = 0):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            embed = discord.Embed(
                title="⚡ Slowmode Disabled!",
                description="🚀 Chat speed: MAXIMUM OVERDRIVE activated!",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="⏰ Slowmode Activated!",
                description=f"🐌 Chat is now moving at {seconds} second intervals\nTime to think before you yap! 🤔",
                color=0xFFAA00
            )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Slowmode machine broke! {str(e)} 🔧", ephemeral=True)

@tree.command(name='userinfo', description='Get info about a user with style 👤')
@app_commands.describe(user='The user to get info about (defaults to yourself)')
async def userinfo_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    
    embed = discord.Embed(
        title=f"👤 {target.display_name} - The Dossier!",
        color=target.color if target.color != discord.Color.default() else 0x7289DA
    )
    
    embed.add_field(name="🏷️ Username", value=f"{target.name}#{target.discriminator}", inline=True)
    embed.add_field(name="📅 Joined Server", value=target.joined_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="🎂 Account Created", value=target.created_at.strftime("%B %d, %Y"), inline=True)
    
    if target.roles[1:]:  # Skip @everyone role
        roles = ", ".join([role.mention for role in target.roles[1:][:10]])  # Limit to 10 roles
        if len(target.roles) > 11:
            roles += f" and {len(target.roles) - 11} more"
        embed.add_field(name="🎭 Roles", value=roles, inline=False)
    
    # Fun status based on user
    if target.bot:
        embed.add_field(name="🤖 Status", value="Fellow robot, respect ✊", inline=True)
    elif target.premium_since:
        embed.add_field(name="💎 Status", value="Server booster = gigachad energy", inline=True)
    else:
        statuses = [
            "Certified human (probably)",
            "Vibes: Immaculate ✨",
            "Aura level: Unconfirmed",
            "Main character energy detected",
            "Ohio resident (unverified)"
        ]
        embed.add_field(name="🎯 Status", value=random.choice(statuses), inline=True)
    
    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)
    
    await interaction.response.send_message(embed=embed)

# Fun interactive commands
@tree.command(name='8ball', description='Ask the magic 8-ball (but make it brainrot) 🎱')
@app_commands.describe(question='Your question for the mystical sphere')
async def eightball_slash(interaction: discord.Interaction, question: str):
    responses = [
        "💯 Fr fr no cap",
        "💀 Absolutely not bestie",
        "🚫 That's cap and you know it",
        "✨ Slay queen, it's gonna happen",
        "🤔 Ask again when you touch grass",
        "🗿 The answer is as clear as your nonexistent rizz",
        "🚽 Skibidi says... maybe?",
        "⚡ Only in Ohio would that be possible",
        "🧠 My brainrot sensors say yes",
        "💅 Bestie that's giving delusional energy",
        "🎪 The circus called, they want their question back",
        "🔥 That's gonna be a sigma yes from me",
        "📉 Negative aura points for that question",
        "👑 You're the main character, make it happen",
        "🌟 The stars align... and they're laughing"
    ]
    
    response = random.choice(responses)
    embed = discord.Embed(
        title="🎱 The Brainrot 8-Ball Has Spoken!",
        description=f"**Question:** {question}\n**Answer:** {response}",
        color=0x8B00FF
    )
    embed.set_footer(text="The 8-ball is not responsible for any Ohio-level consequences")
    await interaction.response.send_message(embed=embed)

@tree.command(name='roast', description='Roast someone (playfully) 🔥')
@app_commands.describe(user='The user to roast (all in good fun!)')
async def roast_slash(interaction: discord.Interaction, user: discord.Member):
    roasts = [
        f"{user.mention} has the energy of a Windows 95 computer trying to run Cyberpunk 2077",
        f"{user.mention} is built like a Roblox character but with worse fashion sense",
        f"{user.mention}'s rizz is in negative numbers, they're giving anti-charisma",
        f"{user.mention} has the personality of unbuttered toast",
        f"{user.mention} is the reason aliens won't visit Earth",
        f"{user.mention} puts pineapple on pizza and thinks it's a personality trait",
        f"{user.mention} has the conversational skills of a Windows error message",
        f"{user.mention} is the human equivalent of a participation trophy",
        f"{user.mention} texts 'k' and wonders why people think they're dry",
        f"{user.mention} is giving NPC energy in the main character server",
        f"{user.mention} has the same energy as a dead Discord server",
        f"{user.mention} collects NFTs of grass because they'll never touch the real thing"
    ]
    
    embed = discord.Embed(
        title="🔥 ROAST ACTIVATED! 🔥",
        description=random.choice(roasts),
        color=0xFF4500
    )
    embed.set_footer(text="This roast was made with 100% organic, free-range sarcasm")
    await interaction.response.send_message(embed=embed)

@tree.command(name='compliment', description='Give someone a backhanded compliment ✨')
@app_commands.describe(user='The user to compliment (sort of)')
async def compliment_slash(interaction: discord.Interaction, user: discord.Member):
    compliments = [
        f"{user.mention} has the confidence of someone who thinks they can sing... and I respect that delusion",
        f"{user.mention} is proof that everyone is unique and special in their own... interesting way",
        f"{user.mention} has main character energy, even if the story is a tragedy",
        f"{user.mention} is the most tolerable person in this server (this week)",
        f"{user.mention} has the rizz of someone who definitely exists",
        f"{user.mention} brings such unique energy to conversations... we're still figuring out what kind",
        f"{user.mention} is absolutely one of the Discord users of all time",
        f"{user.mention} has the best vibes for someone with those vibes",
        f"{user.mention} is serving looks... we just can't identify the cuisine",
        f"{user.mention} has sigma energy... if sigma stood for 'Silly Individual Generally Making Attempts'",
        f"{user.mention} is the most {user.mention}-like person I know, and that's beautiful",
        f"{user.mention} has audacity, and honestly? We stan a confident legend"
    ]
    
    embed = discord.Embed(
        title="✨ BACKHANDED COMPLIMENT DELIVERED! ✨",
        description=random.choice(compliments),
        color=0xFF69B4
    )
    embed.set_footer(text="Compliments so backhanded they're doing backflips")
    await interaction.response.send_message(embed=embed)

@tree.command(name='random', description='Pick a random server member 🎲')
async def random_slash(interaction: discord.Interaction):
    members = [member for member in interaction.guild.members if not member.bot]
    if not members:
        await interaction.response.send_message("No humans detected in this server! 🤖", ephemeral=True)
        return
    
    chosen = random.choice(members)
    reasons = [
        "They have main character energy today",
        "The Ohio algorithm chose them",
        "Their aura levels are off the charts",
        "They won the genetic lottery (today only)",
        "The brainrot gods have spoken",
        "They're giving chosen one vibes",
        "Random.org said so and who are we to argue",
        "They have sigma energy radiating from their profile",
        "The universe has aligned in their favor",
        "They're the least sus person here (allegedly)"
    ]
    
    embed = discord.Embed(
        title="🎲 Random Selection Complete!",
        description=f"🎯 **Chosen One:** {chosen.mention}\n\n**Why them?** {random.choice(reasons)}",
        color=0x00FF88
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='help', description='Show all available goofy commands 🤪')
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤪 Goofy Mod Ultimate Command List!",
        description="Here are all my chaotic powers using `/` commands!",
        color=0xFF69B4
    )
    
    embed.add_field(
        name="🔨 Moderation Commands",
        value="`/ban` - Ban someone to the shadow realm\n"
              "`/kick` - Yeet someone out\n"
              "`/mute [duration] [reason]` - Silence the chaos (5m, 2h, 1d or permanent)\n"
              "`/unmute` - Restore their voice\n"
              "`/warn` - Give a friendly warning (auto-tracks count)\n"
              "`/unwarn [count]` - Remove specific number of warnings\n"
              "`/warnings @user` - View user's warning history\n"
              "`/clearwarnings @user` - Clear all warnings for user\n"
              "`/purge [amount]` - Clean up the mess\n"
              "`/slowmode [seconds]` - Control the yapping speed",
        inline=False
    )
    
    embed.add_field(
        name="🤖 Auto-Moderation",
        value="`/automod [feature] [enabled] [action] [max_warnings]` - Configure auto-mod with actions\n"
              "• **Features:** Spam, Caps, Mentions, Repeat Messages, Warning Escalation\n" 
              "• **Actions:** Warn, Mute, Kick, Ban\n"
              "`/automodstatus` - Check auto-mod settings",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Fun & Interactive",
        value="`/8ball [question]` - Brainrot magic 8-ball\n"
              "`/roast @user` - Playful roasting session\n"
              "`/compliment @user` - Backhanded compliments\n"
              "`/random` - Pick a random server member\n"
              "`/fact` - Get random brainrot facts\n"
              "`/chaos` - Unleash pure chaos energy\n"
              "`/vibe [@user]` - Check vibe status\n"
              "`/ratio @user` - Ratio someone (playfully)",
        inline=False
    )
    
    embed.add_field(
        name="🎪 Games & Entertainment",
        value="`/coinflip` - Chaotic coin flipping\n"
              "`/dice [sides] [count]` - Roll dice with reactions\n"
              "`/ship @user1 [@user2]` - Ship compatibility checker\n"
              "`/meme [topic]` - Generate fresh memes\n"
              "`/quote` - Inspirational quotes (chaotic edition)\n"
              "`/pickup [@user]` - Terrible pickup lines\n"
              "`/challenge` - Get random goofy challenges\n"
              "`/poll [question] [options]` - Brainrot democracy in action",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Info Commands",
        value="`/serverinfo` - Server stats with style\n"
              "`/userinfo [@user]` - User profile with flair\n"
              "`/help` - This chaotic help message",
        inline=False
    )
    
    embed.add_field(
        name="🎪 Welcome System",
        value="`/configwelcomechannel #channel` - Set welcome channel\n"
              "`/configwelcomemessage [message]` - Custom message\n"
              "`/togglewelcome` - Enable/disable welcomes\n"
              "`/welcomestatus` - Check configuration\n"
              "`/resetwelcome` - Reset to defaults",
        inline=False
    )
    
    embed.add_field(
        name="🎭 About Me",
        value="I'm your friendly neighborhood goofy moderator! "
              "I keep servers fun while maintaining order with maximum brainrot energy! 🤡\n\n"
              "✨ **Features:** Auto-responses, spam detection, and pure chaos!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Additional fun commands
@tree.command(name='fact', description='Get a random brainrot fact 🧠')
async def fact_slash(interaction: discord.Interaction):
    fact = random.choice(BRAINROT_FACTS)
    embed = discord.Embed(
        title="📰 Breaking Brainrot News!",
        description=fact,
        color=0x00BFFF
    )
    embed.set_footer(text="Fact-checked by the Ohio Department of Brainrot Studies")
    await interaction.response.send_message(embed=embed)

@tree.command(name='chaos', description='Unleash random chaos energy 🌪️')
async def chaos_slash(interaction: discord.Interaction):
    chaos_events = [
        "🚨 BREAKING: Local user discovers what grass feels like!",
        "📢 ALERT: Someone in this server actually has rizz!",
        "⚡ EMERGENCY: The Ohio portal has been temporarily closed for maintenance!",
        "🎪 NEWS FLASH: The circus called, they want their entire server back!",
        "🚽 URGENT: Skibidi toilet has achieved sentience!",
        "💀 REPORT: Local brainrot levels exceed maximum capacity!",
        "🌽 BREAKING: Ohio corn has begun communicating in morse code!",
        "📮 ALERT: Sus activity detected in sector 7-G!",
        "🤡 NEWS: Professional clown loses job to Discord user!",
        "🧠 STUDY: Scientists confirm this server contains 0% brain cells!"
    ]
    
    event = random.choice(chaos_events)
    embed = discord.Embed(
        title="🌪️ CHAOS MODE ACTIVATED! 🌪️",
        description=event,
        color=0xFF0080
    )
    embed.set_footer(text="This message was brought to you by pure unfiltered chaos")
    await interaction.response.send_message(embed=embed)

# ULTIMATE ENTERTAINMENT COMMANDS FOR MAXIMUM CATCHINESS! 🔥

@tree.command(name='coinflip', description='Flip a coin but make it chaotic 🪙')
async def coinflip_slash(interaction: discord.Interaction):
    outcomes = [
        ("Heads", "🪙 It's heads! You win... at being basic! 😏"),
        ("Tails", "🪙 Tails! The universe said 'nah bestie' 💅"),
        ("The coin landed on its side", "🪙 Bro really broke physics... Ohio moment fr 🌽"),
        ("The coin disappeared", "🪙 Coin got yeeted to the shadow realm 👻"),
        ("The coin started floating", "🪙 Anti-gravity activated! Someone call NASA! 🚀"),
        ("The coin exploded", "🪙 BOOM! Coin.exe has stopped working 💥")
    ]
    
    result, description = random.choice(outcomes)
    
    embed = discord.Embed(
        title=f"🪙 Coin Flip Results: **{result}**!",
        description=description,
        color=random.randint(0, 0xFFFFFF)
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='dice', description='Roll dice with maximum chaos energy 🎲')
@app_commands.describe(sides='Number of sides (default: 6)', count='Number of dice (default: 1)')
async def dice_slash(interaction: discord.Interaction, sides: int = 6, count: int = 1):
    if count > 20:
        await interaction.response.send_message("Whoa there! Max 20 dice or my brain will explode! 🤯", ephemeral=True)
        return
    if sides > 1000:
        await interaction.response.send_message("That's not a dice, that's a sphere! Max 1000 sides! 🌍", ephemeral=True)
        return
    
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    
    # Goofy reactions based on rolls
    reactions = {
        1: "💀 Oof! That's rough buddy!",
        sides: f"🔥 CRITICAL HIT! {sides} is absolutely sending it!",
        69: "😏 Nice... very nice indeed",
        420: "🌿 Blaze it! That's the magic number!",
        666: "😈 Demonic energy detected!",
        777: "🍀 Lucky sevens! Buy a lottery ticket!"
    }
    
    reaction = ""
    for roll in rolls:
        if roll in reactions:
            reaction = f"\n{reactions[roll]}"
            break
    
    if total == count:  # All 1s
        reaction = "\n💀 All ones?! The dice are absolutely roasting you!"
    elif total == sides * count:  # All max
        reaction = "\n🎆 ALL MAX ROLLS! You've broken the matrix!"
    
    dice_display = " + ".join(map(str, rolls)) if count > 1 else str(rolls[0])
    
    embed = discord.Embed(
        title=f"🎲 Dice Roll Results!",
        description=f"**Rolled {count}d{sides}:**\n{dice_display} = **{total}**{reaction}",
        color=random.randint(0, 0xFFFFFF)
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='ship', description='Ship two users and see their compatibility 💕')
@app_commands.describe(user1='First person', user2='Second person (optional - will pick random if not provided)')
async def ship_slash(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None):
    if not user2:
        members = [m for m in interaction.guild.members if not m.bot and m != user1]
        if not members:
            await interaction.response.send_message("No one else to ship with! Forever alone! 💀", ephemeral=True)
            return
        user2 = random.choice(members)
    
    # Create ship name
    name1 = user1.display_name
    name2 = user2.display_name
    ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]
    
    compatibility = random.randint(0, 100)
    
    # Compatibility reactions
    if compatibility >= 95:
        reaction = "💖 SOULMATES! Someone call the wedding planner! 💒"
        color = 0xFF1493
    elif compatibility >= 80:
        reaction = "💕 Perfect match! Netflix and chill vibes! 🍿"
        color = 0xFF69B4
    elif compatibility >= 60:
        reaction = "💛 Could work! Give it a shot bestie! ✨"
        color = 0xFFD700
    elif compatibility >= 40:
        reaction = "🧡 Mid energy... maybe as friends? 🤷‍♀️"
        color = 0xFF8C00
    elif compatibility >= 20:
        reaction = "💔 Yikes... this ain't it chief 😬"
        color = 0xFF4500
    else:
        reaction = "💀 Absolutely not! Oil and water vibes! 🚫"
        color = 0x800080
    
    embed = discord.Embed(
        title=f"💕 Ship Analysis: {ship_name}",
        description=f"**{user1.mention} + {user2.mention}**\n\n**Compatibility:** {compatibility}%\n{reaction}",
        color=color
    )
    
    # Add compatibility bar
    filled = "💖" * (compatibility // 10)
    empty = "🖤" * (10 - (compatibility // 10))
    embed.add_field(name="Compatibility Meter", value=f"{filled}{empty}", inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='meme', description='Generate memes with maximum brainrot energy 😂')
@app_commands.describe(
    type='Choose meme type',
    topic='What do you want a meme about? (optional)'
)
@app_commands.choices(type=[
    app_commands.Choice(name='Text Meme', value='text'),
    app_commands.Choice(name='GIF Meme', value='gif')
])
async def meme_slash(interaction: discord.Interaction, type: str = 'text', topic: str = None):
    if type == 'gif':
        # Send brainrot GIF memes
        await interaction.response.defer()
        
        # Updated working brainrot GIF collection with verified URLs
        brainrot_gifs = [
            {
                "url": "https://media.tenor.com/fYg91qBpzcgAAAAM/skull-emoji.gif",
                "description": "💀 When someone says Ohio isn't that chaotic"
            },
            {
                "url": "https://media.tenor.com/x8v1oNUOmg4AAAAC/pbg-peanutbuttergamer.gif", 
                "description": "🤯 Me discovering new brainrot content at 3AM"
            },
            {
                "url": "https://media.tenor.com/2A_N2B4Lr-4AAAAC/vine-boom.gif",
                "description": "📢 When someone drops the hardest brainrot take"
            },
            {
                "url": "https://media.tenor.com/ZbF1OLgon5sAAAAC/sussy-among-us.gif",
                "description": "📮 POV: You're acting sus but trying to be sigma"
            },
            {
                "url": "https://media.tenor.com/1lzy4K4MpUUAAAAC/sigma-male.gif",
                "description": "🗿 Sigma male energy activated"
            },
            {
                "url": "https://media.tenor.com/3C8teY_HDwEAAAAC/screaming-crying.gif",
                "description": "😭 When the Ohio energy hits different"
            },
            {
                "url": "https://media.tenor.com/YxDR9-hSL1oAAAAC/ohio-only-in-ohio.gif",
                "description": "🌽 Only in Ohio moments be like"
            },
            {
                "url": "https://media.tenor.com/kHcmsz8-DvgAAAAC/spinning-rat.gif",
                "description": "🐭 My brain processing all this brainrot"
            },
            {
                "url": "https://media.tenor.com/6-KnyPtq_UIAAAAC/dies-death.gif",
                "description": "💀 Me after consuming too much skibidi content"
            },
            {
                "url": "https://media.tenor.com/THljy3hBZ6QAAAAC/rick-roll-rick-rolled.gif",
                "description": "🎵 Get brainrotted (instead of rickrolled)"
            },
            {
                "url": "https://media.tenor.com/4mGbBWK3CKAAAAAC/despicable-me-gru.gif",
                "description": "🦹‍♂️ When you successfully spread the brainrot"
            },
            {
                "url": "https://media.tenor.com/Qul3leyVTkEAAAAC/friday-night-funkin.gif",
                "description": "🎤 Vibing to the brainrot beats"
            }
        ]
        
        # Topic-specific GIF selection (simplified for now)
        if topic:
            selected_gif = random.choice(brainrot_gifs)
            description = f"🎬 {topic} energy: {selected_gif['description']}"
        else:
            selected_gif = random.choice(brainrot_gifs)
            description = selected_gif['description']
        
        embed = discord.Embed(
            title="🎬 Brainrot GIF Meme Delivered!",
            description=description,
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_image(url=selected_gif['url'])
        embed.add_field(
            name="📊 Brainrot Stats",
            value=f"**Topic:** {topic if topic else 'Pure chaos'}\n**Viral Level:** Maximum 📈\n**Ohio Energy:** Detected 🌽",
            inline=False
        )
        embed.set_footer(text="GIF quality: Absolutely sending it | Brainrot level: Over 9000")
        
        await interaction.followup.send(embed=embed)
    
    if type == 'text':
        if topic:
            # Topic-specific memes with MAXIMUM BRAINROT
            memes = [
                f"POV: {topic} just hit different at 3am in Ohio 💀🌽",
                f"Nobody:\nAbsolutely nobody:\n{topic}: 'I'm about to be so skibidi' 🚽",
                f"{topic} really said 'I'm the main character' and honestly? No cap fr 📢",
                f"Me explaining {topic} to my sleep paralysis demon:\n'Bro it's giving sigma energy' 👻",
                f"*{topic} happens*\nMe: 'That's absolutely sending me to the shadow realm' 😤",
                f"When someone mentions {topic}:\n'Finally, some good brainrot content' ⚔️",
                f"Mom: 'We have {topic} at home'\n{topic} at home: *pure Ohio energy* 💀",
                f"Teacher: 'This {topic} test will be easy'\nThe test: *Maximum skibidi difficulty* 🪖",
                f"{topic} got me acting unwise... this is not very sigma of me 🗿",
                f"Breaking: Local person discovers {topic}, immediately becomes based 📰"
            ]
        else:
            # PURE BRAINROT MEMES - Maximum chaos energy
            brainrot_memes = [
                "POV: You're sigma but the alpha is lowkey mid 💀",
                "Ohio final boss when you're just trying to exist normally: 🌽👹",
                "When someone says 'skibidi' unironically:\n*Respect has left the chat* 🚽",
                "Sigma male grindset: Step 1) Touch grass\nMe: 'Instructions unclear' 🌱",
                "Brain: 'Be productive'\nAlso brain: 'But have you considered... more brainrot?' 🧠",
                "POV: You're trying to be normal but your Ohio energy is showing 🌽✨",
                "When the rizz is bussin but you're still maidenless:\n*Confused sigma noises* 🗿",
                "Me: 'I'll be mature today'\n*30 seconds later*\n'SKIBIDI BOP BOP YES YES' 🎵",
                "Life really said 'You're going to Ohio whether you like it or not' 🌽💀",
                "When you're based but also cringe simultaneously:\n*Perfectly balanced, as all things should be* ⚖️",
                "POV: Someone asks if you're okay and you realize you've been yapping about brainrot for 3 hours 💬",
                "Trying to explain Gen Alpha humor to millennials:\n*Vietnam flashbacks intensify* 🪖",
                "When the imposter is sus but also lowkey sigma:\n*Confused Among Us noises* 📮",
                "Me at 3AM watching skibidi toilet for the 47th time:\n'This is fine' 🔥🚽",
                "Ohio energy meter: ████████████ 100%\nSanity meter: ▌ 3% 💀"
            ]
            
            # Combine general chaotic memes with pure brainrot
            general_memes = [
                "POV: You're the main character but the plot is absolutely unhinged 🎭",
                "When someone says 'it could be worse':\nOhio: 'Allow me to introduce myself' 🌽",
                "*Exists peacefully*\nResponsibilities: 'We're about to end this whole person's career' 👔",
                "My sleep schedule looking at me at 4AM:\n'You're not very sigma, are you?' ✨",
                "Bank account: -$5\nStarbucks: 'Bonjour bestie' ☕💸",
                "Me: 'I'll touch grass today'\nAlso me: *Discovers new brainrot content* 🌱➡️📱",
                "Brain at 3AM: 'Remember every cringe thing you've ever done?'\nMe: 'Why are you like this?' 🧠💭"
            ]
            
            # Combine all meme types
            all_memes = brainrot_memes + general_memes
            memes = all_memes
        
        meme = random.choice(memes)
        
        embed = discord.Embed(
            title="😂 Fresh Brainrot Meme Generated!",
            description=meme,
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_footer(text="Brainrot level: Maximum | Ohio energy: Detected 🌽")
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

@tree.command(name='quote', description='Get an inspirational quote but make it chaotic ✨')
async def quote_slash(interaction: discord.Interaction):
    quotes = [
        "\"Be yourself, everyone else is already taken.\" - Except in Ohio, there you become corn 🌽",
        "\"Life is what happens when you're busy making other plans.\" - And plans are what happen when you're busy living in delusion ✨",
        "\"The only way to do great work is to love what you do.\" - Unless what you do is watching TikTok for 8 hours straight 📱",
        "\"In the end, we only regret the chances we didn't take.\" - And the ones we did take. Regret is universal bestie 💀",
        "\"Be the change you wish to see in the world.\" - World: 'Actually, we're good thanks' 🌍",
        "\"Success is not final, failure is not fatal.\" - But embarrassment? That's forever 😭",
        "\"The future belongs to those who believe in their dreams.\" - Dreams: 'Actually, I'm seeing other people now' 💔",
        "\"You miss 100% of the shots you don't take.\" - You also miss 99% of the ones you do take 🏀",
        "\"Believe you can and you're halfway there.\" - The other half is still absolutely impossible though 🤷‍♀️",
        "\"Life is like a box of chocolates.\" - Mostly nuts and nobody wants the coconut ones 🍫"
    ]
    
    quote = random.choice(quotes)
    
    embed = discord.Embed(
        title="✨ Daily Dose of Questionable Wisdom",
        description=quote,
        color=random.randint(0, 0xFFFFFF)
    )
    embed.set_footer(text="Inspiration level: Maximum | Accuracy: Debatable")
    await interaction.response.send_message(embed=embed)

@tree.command(name='pickup', description='Generate pickup lines that definitely won\'t work 💘')
@app_commands.describe(user='Who to generate a pickup line for (optional)')
async def pickup_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user.mention if user else "someone special"
    
    lines = [
        f"Are you Ohio? Because you make everything weird but I can't look away 🌽",
        f"Hey {target}, are you a Discord notification? Because you never leave me alone 🔔",
        f"Are you skibidi toilet? Because you're absolutely flushing away my sanity 🚽",
        f"Hey {target}, are you my sleep schedule? Because you're completely messed up but I still want you 😴",
        f"Are you a loading screen? Because I've been waiting for you my whole life... and you're taking forever 💀",
        f"Hey {target}, are you my browser history? Because I really don't want anyone else to see you 🔒",
        f"Are you a Discord mod? Because you have absolute power over my server... I mean heart 👑",
        f"Hey {target}, are you Wi-Fi? Because I'm not connecting but I'll keep trying 📶",
        f"Are you my phone battery? Because you drain me but I can't function without you 🔋",
        f"Hey {target}, are you a meme? Because you're funny but I don't want to share you 😂"
    ]
    
    line = random.choice(lines)
    
    embed = discord.Embed(
        title="💘 Pickup Line Generator",
        description=f"{line}\n\n*Success rate: 0% | Cringe level: Maximum*",
        color=0xFF69B4
    )
    embed.set_footer(text="GoofGuard is not responsible for any restraining orders")
    await interaction.response.send_message(embed=embed)

@tree.command(name='challenge', description='Get a random goofy challenge to complete 🎯')
async def challenge_slash(interaction: discord.Interaction):
    challenges = [
        "Text your last message but replace every vowel with 'uh' 📱",
        "Speak in questions for the next 10 minutes ❓",
        "End every sentence with 'in Ohio' for 5 minutes 🌽",
        "Pretend you're a sports commentator for everything you do 📺",
        "Only communicate through song lyrics for the next 3 messages 🎵",
        "Act like you're a time traveler from 2005 who just discovered modern technology ⏰",
        "Replace all your adjectives with 'sussy' or 'bussin' for the next hour 📮",
        "Pretend every message is a breaking news report 📰",
        "Talk like a pirate but replace 'arr' with 'skibidi' 🏴‍☠️",
        "Act like you're giving a TED talk about the most mundane thing you can see 🎤",
        "Pretend you're narrating your life like a nature documentary 🦁",
        "End every message with a random emoji and act like it's profound 🗿"
    ]
    
    challenge = random.choice(challenges)
    difficulty = random.choice(["Easy", "Medium", "Hard", "Impossible", "Ohio Level"])
    
    embed = discord.Embed(
        title="🎯 Random Challenge Accepted!",
        description=f"**Your Mission:** {challenge}\n\n**Difficulty:** {difficulty}",
        color=random.randint(0, 0xFFFFFF)
    )
    embed.add_field(name="Reward", value="Bragging rights and questionable looks from others", inline=False)
    embed.set_footer(text="GoofGuard challenges are legally binding in Ohio")
    await interaction.response.send_message(embed=embed)

@tree.command(name='poll', description='Create goofy brainrot polls that spark chaos 📊')
@app_commands.describe(
    question='The poll question (will be made brainrot if not already)',
    option1='First option (optional - will generate if not provided)',
    option2='Second option (optional - will generate if not provided)',
    option3='Third option (optional)',
    option4='Fourth option (optional)',
    option5='Fifth option (optional)'
)
async def poll_slash(interaction: discord.Interaction, question: str, 
                    option1: str = None, option2: str = None, option3: str = None, 
                    option4: str = None, option5: str = None):
    
    # Make the question more brainrot if it's too normal
    if not any(term in question.lower() for term in ['ohio', 'skibidi', 'sigma', 'sus', 'brainrot', 'rizz', 'bussin', 'yapping', 'zesty']):
        brainrot_prefixes = [
            "Ohio citizens be like:",
            "Sigma males when they see",
            "POV: You're in Ohio and",
            "Skibidi question time:",
            "Sus or not sus:",
            "Brainrot poll incoming:",
            "Only real sigmas can answer:",
            "This question is absolutely sending me:"
        ]
        question = f"{random.choice(brainrot_prefixes)} {question}"
    
    # Collect provided options
    provided_options = []
    if option1: provided_options.append(option1)
    if option2: provided_options.append(option2)
    if option3: provided_options.append(option3)
    if option4: provided_options.append(option4)
    if option5: provided_options.append(option5)
    
    # If less than 2 options provided, generate brainrot options
    if len(provided_options) < 2:
        brainrot_options = [
            "Absolutely based 💯",
            "Mid energy, not gonna lie 😐",
            "This is giving Ohio vibes 🌽",
            "Skibidi level chaos 🚽",
            "Sigma male approved ✅",
            "Sus behavior detected 📮",
            "Rizz level: Maximum 😎",
            "Bussin fr fr 🔥",
            "Absolutely not bestie ❌",
            "Touch grass immediately 🌱",
            "Brainrot certified ✨",
            "Only in Ohio 🏙️",
            "This ain't it chief 💀",
            "Certified hood classic 🏘️",
            "Lowkey fire though 🔥",
            "Sending me to the shadow realm 👻",
            "Cringe but in a good way 😬",
            "Unhinged behavior 🤪",
            "Peak comedy achieved 🎭",
            "Absolutely sending it 🚀"
        ]
        
        # Fill missing options with random brainrot choices
        while len(provided_options) < 2:
            random_option = random.choice(brainrot_options)
            if random_option not in provided_options:
                provided_options.append(random_option)
        
        # Add more options if user didn't provide many
        while len(provided_options) < 4 and len(provided_options) < 5:
            random_option = random.choice(brainrot_options)
            if random_option not in provided_options:
                provided_options.append(random_option)
                if len(provided_options) >= 4:
                    break
    
    # Limit to 5 options maximum
    options = provided_options[:5]
    
    # Emoji reactions for voting
    reaction_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    
    # Create the poll embed
    embed = discord.Embed(
        title="📊 BRAINROT POLL ACTIVATED! 📊",
        description=f"**{question}**\n\n",
        color=random.randint(0, 0xFFFFFF)
    )
    
    # Add poll options
    poll_description = ""
    for i, option in enumerate(options):
        poll_description += f"{reaction_emojis[i]} {option}\n"
    
    embed.description += poll_description
    
    # Add some chaos
    poll_footers = [
        "Vote now or get yeeted to Ohio 🌽",
        "Results will be absolutely chaotic 💀",
        "This poll is certified brainrot ✨",
        "Democracy but make it sus 📮",
        "Your vote matters (in Ohio) 🏙️",
        "Sigma males vote twice 😤",
        "Poll closes when the chaos ends 🔥",
        "Results may cause existential crisis 🤯"
    ]
    
    embed.add_field(
        name="🎪 Poll Rules",
        value="React to vote! Multiple votes = extra chaos energy! 🔥",
        inline=False
    )
    
    embed.set_footer(text=random.choice(poll_footers))
    
    # Send the poll
    await interaction.response.send_message(embed=embed)
    
    # Add reaction emojis for voting
    message = await interaction.original_response()
    for i in range(len(options)):
        await message.add_reaction(reaction_emojis[i])
    
    # Add some extra chaotic reactions
    chaos_reactions = ['💀', '🔥', '🌽', '📮', '🗿']
    for emoji in chaos_reactions[:2]:  # Add 2 random chaos emojis
        try:
            await message.add_reaction(emoji)
        except:
            pass  # In case emoji fails

@tree.command(name='vibe', description='Check your current vibe status ✨')
@app_commands.describe(user='Check someone else\'s vibes (optional)')
async def vibe_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    
    vibes = [
        "Immaculate ✨",
        "Sus but we vibe with it 📮",
        "Giving main character energy 👑",
        "Ohio resident confirmed 🌽",
        "Brainrot levels: Maximum 💀",
        "Sigma grindset detected 🐺",
        "Zesty energy radiating 💅",
        "NPC behavior identified 🤖",
        "Absolutely sending it 🚀",
        "Cringe but endearing 😬",
        "Chaotic neutral vibes 🎭",
        "Built different (literally) 🏗️",
        "Serving looks and attitude 💫",
        "Questionable but iconic 🤔",
        "Unhinged in the best way 🌪️"
    ]
    
    vibe_score = random.randint(1, 100)
    vibe_status = random.choice(vibes)
    
    embed = discord.Embed(
        title=f"✨ Vibe Check Results for {target.display_name}!",
        description=f"**Vibe Score:** {vibe_score}/100\n**Current Status:** {vibe_status}",
        color=0x9932CC
    )
    
    if vibe_score >= 90:
        embed.add_field(name="🏆 Verdict", value="Absolutely iconic behavior!", inline=False)
    elif vibe_score >= 70:
        embed.add_field(name="👍 Verdict", value="Solid vibes, keep it up!", inline=False)
    elif vibe_score >= 50:
        embed.add_field(name="😐 Verdict", value="Mid vibes, room for improvement", inline=False)
    elif vibe_score >= 30:
        embed.add_field(name="📉 Verdict", value="Questionable energy detected", inline=False)
    else:
        embed.add_field(name="💀 Verdict", value="Vibes are NOT it chief", inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='ratio', description='Attempt to ratio someone (for fun) 📊')
@app_commands.describe(user='The user to ratio')
async def ratio_slash(interaction: discord.Interaction, user: discord.Member):
    ratio_attempts = [
        f"Ratio + L + {user.mention} fell off + no rizz + touch grass + Ohio energy 📉",
        f"Imagine being {user.mention} and thinking you wouldn't get ratioed 💀",
        f"This is a certified {user.mention} L moment + ratio + cope 📊",
        f"{user.mention} just got absolutely demolished + ratio + no cap 🔥",
        f"Breaking: {user.mention} discovers what a ratio looks like (it's this tweet) 📈",
        f"{user.mention} ratio speedrun any% world record (GONE WRONG) 🏃‍♂️",
        f"POV: {user.mention} thought they were the main character but got ratioed 🎭",
        f"{user.mention} just experienced what we call a 'professional ratio' 💼"
    ]
    
    embed = discord.Embed(
        title="📊 RATIO ATTEMPT ACTIVATED!",
        description=random.choice(ratio_attempts),
        color=0xFF6B35
    )
    embed.set_footer(text="This ratio was sponsored by pure chaos energy")
    await interaction.response.send_message(embed=embed)

# Welcome Configuration Commands
@tree.command(name='configwelcomechannel', description='Set the welcome channel for new members 🎪')
@app_commands.describe(channel='The channel for welcome messages')
async def config_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_config:
        welcome_config[guild_id] = {}
    
    welcome_config[guild_id]["channel_id"] = channel.id
    welcome_config[guild_id]["enabled"] = True  # Enable by default when setting channel
    save_welcome_config(welcome_config)
    
    embed = discord.Embed(
        title="🎪 Welcome Channel Configured!",
        description=f"New members will be welcomed in {channel.mention} with maximum goofy energy! 🤡",
        color=0x00FF88
    )
    embed.add_field(name="💡 Pro Tip", value="Use `/configwelcomemessage` to set a custom welcome message!", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name='configwelcomemessage', description='Set a custom welcome message 💬')
@app_commands.describe(message='Custom message (use {user} for mention, {username} for name, {server} for server name)')
async def config_welcome_message(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_config:
        await interaction.response.send_message("❌ Set a welcome channel first using `/configwelcomechannel`!", ephemeral=True)
        return
    
    welcome_config[guild_id]["custom_message"] = message
    save_welcome_config(welcome_config)
    
    # Preview the message
    preview = message.format(user="@NewUser", username="NewUser", server=interaction.guild.name)
    
    embed = discord.Embed(
        title="💬 Custom Welcome Message Set!",
        description="Your custom welcome message has been saved! Here's a preview:",
        color=0xFF69B4
    )
    embed.add_field(name="📝 Preview", value=preview, inline=False)
    embed.add_field(
        name="🔧 Variables Available", 
        value="`{user}` - User mention\n`{username}` - Username\n`{server}` - Server name", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='togglewelcome', description='Enable or disable welcome messages 🔄')
async def toggle_welcome(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_config:
        await interaction.response.send_message("❌ Set a welcome channel first using `/configwelcomechannel`!", ephemeral=True)
        return
    
    current_status = welcome_config[guild_id].get("enabled", False)
    welcome_config[guild_id]["enabled"] = not current_status
    save_welcome_config(welcome_config)
    
    new_status = "enabled" if not current_status else "disabled"
    emoji = "✅" if not current_status else "❌"
    
    embed = discord.Embed(
        title=f"{emoji} Welcome Messages {new_status.title()}!",
        description=f"Welcome messages are now **{new_status}** for this server!",
        color=0x00FF00 if not current_status else 0xFF0000
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name='welcomestatus', description='Check current welcome configuration 📊')
async def welcome_status(interaction: discord.Interaction):
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    guild_config = welcome_config.get(guild_id, {})
    
    if not guild_config:
        embed = discord.Embed(
            title="❌ Welcome System Not Configured",
            description="Use `/configwelcomechannel` to set up welcome messages!",
            color=0xFF0000
        )
    else:
        enabled = guild_config.get("enabled", False)
        channel_id = guild_config.get("channel_id")
        custom_message = guild_config.get("custom_message")
        
        channel_mention = f"<#{channel_id}>" if channel_id else "Not set"
        status_emoji = "✅" if enabled else "❌"
        
        embed = discord.Embed(
            title="📊 Welcome System Configuration",
            color=0x00FF88 if enabled else 0xFFAA00
        )
        embed.add_field(name="Status", value=f"{status_emoji} {'Enabled' if enabled else 'Disabled'}", inline=True)
        embed.add_field(name="Channel", value=channel_mention, inline=True)
        embed.add_field(name="Custom Message", value="✅ Set" if custom_message else "❌ Using defaults", inline=True)
        
        if custom_message:
            preview = custom_message.format(user="@NewUser", username="NewUser", server=interaction.guild.name)
            embed.add_field(name="📝 Custom Message Preview", value=preview[:1000], inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='resetwelcome', description='Reset welcome configuration to defaults 🔄')
async def reset_welcome(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id in welcome_config:
        # Remove custom message but keep channel and enabled status
        if "custom_message" in welcome_config[guild_id]:
            del welcome_config[guild_id]["custom_message"]
        save_welcome_config(welcome_config)
    
    embed = discord.Embed(
        title="🔄 Welcome Configuration Reset!",
        description="Custom welcome message removed! Now using random goofy default messages! 🤡",
        color=0x00BFFF
    )
    await interaction.response.send_message(embed=embed)

# Fun response to certain messages
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Random goofy responses to certain phrases
    content = message.content.lower()
    
    # Sus/Among Us responses
    if any(word in content for word in ['sus', 'amogus', 'among us', 'impostor', 'imposter']):
        responses = [
            "📮 Red looking kinda sus ngl 👀",
            "🚨 That's sus behavior bestie",
            "👀 Bro is acting like the impostor fr",
            "📮 Among us in real life (sus, sus)"
        ]
        if random.randint(1, 8) == 1:  # 12.5% chance
            await message.reply(random.choice(responses))
    
    # Skibidi responses
    elif any(word in content for word in ['skibidi', 'toilet', 'ohio']):
        responses = [
            "🚽 Skibidi bop bop yes yes!",
            "💀 Only in Ohio fr fr",
            "🚽 Skibidi toilet moment",
            "🌽 Ohio energy detected",
            "🚽 Bro really said skibidi unironically"
        ]
        if random.randint(1, 6) == 1:  # ~17% chance
            await message.reply(random.choice(responses))
    
    # Yapping responses
    elif any(word in content for word in ['yap', 'yapping', 'yappin', 'chat']):
        responses = [
            "🗣️ Stop the yap session bestie",
            "💬 Bro is absolutely YAPPING",
            "🤐 The yapping needs to stop",
            "🗣️ Yap yap yap that's all you do",
            "💭 Least talkative Discord user"
        ]
        if random.randint(1, 10) == 1:  # 10% chance
            await message.reply(random.choice(responses))
    
    # Zesty/Slay responses  
    elif any(word in content for word in ['zesty', 'slay', 'queen', 'king', 'bestie']):
        responses = [
            "💅 You're being a little too zesty rn",
            "✨ Slay queen but make it less zesty",
            "👑 That's giving zesty energy",
            "💫 Bestie is serving looks AND attitude",
            "🌟 Zesty but we stan"
        ]
        if random.randint(1, 8) == 1:  # 12.5% chance
            await message.reply(random.choice(responses))
    
    # Brainrot/Sigma responses
    elif any(word in content for word in ['sigma', 'alpha', 'beta', 'rizz', 'gyatt', 'fanum']):
        responses = [
            "🐺 Sigma grindset activated",
            "💪 That's alpha behavior fr",
            "📉 Your rizz levels are concerning",
            "🔥 Gyatt dayum that's crazy",
            "🍽️ Fanum tax moment",
            "🐺 Bro thinks they're sigma but...",
            "💀 Negative aura points detected"
        ]
        if random.randint(1, 7) == 1:  # ~14% chance
            await message.reply(random.choice(responses))
    
    # Ratio responses
    elif 'ratio' in content:
        responses = [
            "📉 Ratio + L + no bitches + touch grass 🌱",
            "📊 Imagine getting ratioed, couldn't be me",
            "💀 That's a ratio if I've ever seen one",
            "📉 L + ratio + you fell off + no cap"
        ]
        if random.randint(1, 12) == 1:  # ~8% chance
            await message.reply(random.choice(responses))
    
    # Cap/No Cap responses
    elif any(word in content for word in ['cap', 'no cap', 'nocap']):
        responses = [
            "🧢 That's cap and you know it",
            "💯 No cap fr fr",
            "🎓 Stop the cap bestie",
            "🧢 Cap detected, opinion rejected"
        ]
        if random.randint(1, 15) == 1:  # ~7% chance
            await message.reply(random.choice(responses))
    
    # Cringe responses
    elif any(word in content for word in ['cringe', 'crimg', 'ick']):
        responses = [
            "😬 That's not very poggers of you",
            "💀 Cringe behavior detected",
            "😬 That gave me the ick ngl",
            "🤢 Cringe levels: maximum"
        ]
        if random.randint(1, 18) == 1:  # ~6% chance
            await message.reply(random.choice(responses))
    
    # F responses
    elif content == 'f':
        responses = [
            "😔 F in the chat",
            "⚰️ F to pay respects",
            "💀 Big F energy",
            "😭 F moment fr"
        ]
        if random.randint(1, 20) == 1:  # 5% chance
            await message.reply(random.choice(responses))
    
    # Spam word detection
    elif any(word in content for word in ['spam', 'spamming', 'spammer']):
        responses = [
            "🥫 Spam? I prefer premium ham actually",
            "📧 Bro really said the S word... that's illegal here",
            "🚫 Spam is not very demure or mindful bestie",
            "🥓 Spam is for breakfast, not Discord chat",
            "💀 Imagine typing spam unironically",
            "🤖 Spam detected, deploying anti-spam energy",
            "⚡ That word is giving NPC behavior",
            "🚨 Spam alert! This is not it chief"
        ]
        if random.randint(1, 3) == 1:  # 33% chance
            await message.reply(random.choice(responses))
    
    # Bot ping responses
    elif bot.user.mentioned_in(message) and not message.mention_everyone:
        responses = [
            "👀 Did someone summon the chaos demon?",
            "🤪 You called? I was busy being goofy elsewhere",
            "💀 Bro really pinged me like I'm their personal assistant",
            "🎭 *materializes from the shadow realm* You rang?",
            "⚡ BEEP BEEP here comes the goofy truck",
            "🚨 Alert! Someone needs maximum goofy energy deployed",
            "👻 I have been summoned from the Ohio dimension",
            "🤖 Processing request... Error 404: Seriousness not found",
            "💫 *teleports behind you* Nothing personnel kid",
            "🎪 The circus has arrived, what can I do for you?",
            "🔥 You've awakened the brainrot lord, speak your wish",
            "💅 Bestie you could've just said hello instead of pinging",
            "🗿 Why have you disturbed my sigma meditation?",
            "🚽 Skibidi bot activated! How may I serve you today?"
        ]
        await message.reply(random.choice(responses))
    
    # Auto-react to certain messages
    # React to sus messages
    if any(word in content for word in ['sus', 'impostor', 'amogus']):
        if random.randint(1, 4) == 1:  # 25% chance
            try:
                await message.add_reaction('📮')
            except:
                pass
    
    # React to sigma/alpha messages
    elif any(word in content for word in ['sigma', 'alpha', 'chad']):
        if random.randint(1, 5) == 1:  # 20% chance
            try:
                await message.add_reaction('🐺')
            except:
                pass
    
    # React to brainrot terms
    elif any(word in content for word in ['skibidi', 'ohio', 'gyatt']):
        reactions = ['💀', '🚽', '🌽', '🤡']
        if random.randint(1, 6) == 1:  # ~17% chance
            try:
                await message.add_reaction(random.choice(reactions))
            except:
                pass
    
    # React to cringe
    elif any(word in content for word in ['cringe', 'ick']):
        if random.randint(1, 8) == 1:  # 12.5% chance
            try:
                await message.add_reaction('😬')
            except:
                pass
    
    # Copypasta detection and response
    if len(content) > 200:  # Long messages might be copypastas
        for trigger, pasta in COPYPASTAS.items():
            if trigger in content:
                if random.randint(1, 3) == 1:  # 33% chance
                    await message.reply(f"Nice copypasta bestie, but have you considered this instead:\n\n{pasta[:500]}...")
                break
    
    # Random very rare goofy responses for any message
    elif random.randint(1, 250) == 1:  # ~0.4% chance for any message
        response = random.choice(RANDOM_GOOFY_RESPONSES)
        await message.reply(response)

# Error handling for slash commands
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Enhanced error handling for slash commands"""
    try:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("🚫 You don't have the power! Ask an admin! 👮‍♂️", ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏰ Slow down there! Try again in {error.retry_after:.1f} seconds!", ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message("🤖 I don't have the required permissions for this command!", ephemeral=True)
        else:
            logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
            await interaction.response.send_message(f"Something went wonky! 🤪 Error: {str(error)}", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        # Last resort - try to send a basic message
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went really wonky! 😵", ephemeral=True)
        except:
            pass  # Give up if we can't even send an error message

# Simple Flask web server for Render Web Service compatibility
app = Flask(__name__)

@app.route('/')
def home():
    try:
        uptime = time.time() - bot.start_time if hasattr(bot, 'start_time') else 0
        return {
            "status": "online",
            "bot_name": "Goofy Mod Bot",
            "message": "🤪 Bot is running! This endpoint keeps the web service alive on Render.",
            "servers": len(bot.guilds) if bot.is_ready() else 0,
            "uptime_seconds": round(uptime, 1),
            "bot_ready": bot.is_ready(),
            "reconnects": getattr(bot, 'reconnect_count', 0)
        }
    except Exception as e:
        logger.error(f"Health endpoint error: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/health')
def health():
    try:
        is_ready = bot.is_ready()
        uptime = time.time() - bot.start_time if hasattr(bot, 'start_time') else 0
        
        # Health checks
        health_status = "healthy" if is_ready else "unhealthy"
        
        return {
            "status": health_status,
            "bot_ready": is_ready,
            "servers": len(bot.guilds) if is_ready else 0,
            "uptime_seconds": round(uptime, 1),
            "reconnects": getattr(bot, 'reconnect_count', 0),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/ping')
def ping():
    """Simple ping endpoint for monitoring"""
    return {"pong": True, "timestamp": time.time()}

def run_web_server():
    """Run Flask web server with enhanced error handling"""
    try:
        port = int(os.getenv('PORT', 5000))  # Render provides PORT env var
        logger.info(f"🌐 Starting web server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Web server failed to start: {e}")
        # Don't exit - let the bot continue running
        time.sleep(5)  # Wait before potential restart

def start_bot_with_retry(token, max_retries=3):
    """Start bot with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 Starting Discord bot (attempt {attempt + 1}/{max_retries})...")
            bot.run(token, reconnect=True, log_level=logging.WARNING)
            break  # If we get here, bot ran successfully
        except discord.LoginFailure:
            logger.error("❌ Invalid bot token! Check your DISCORD_BOT_TOKEN")
            exit(1)
        except discord.ConnectionClosed:
            logger.warning(f"Connection closed, retrying in 10 seconds... (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                logger.error("Max retries reached, exiting")
                exit(1)
        except Exception as e:
            logger.error(f"Bot error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 15 seconds...")
                time.sleep(15)
            else:
                logger.error("Max retries reached, exiting")
                exit(1)

# Optimize for Render deployment with enhanced reliability
if __name__ == "__main__":
    logger.info("🚀 Initializing Goofy Mod Bot for hosting...")
    
    # Validate token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("❌ No bot token found! Please set DISCORD_BOT_TOKEN in your environment variables!")
        exit(1)
    
    logger.info("🚀 Starting Goofy Mod bot with enhanced hosting features...")
    
    try:
        # Start Flask web server in a separate daemon thread
        web_thread = threading.Thread(target=run_web_server, daemon=True, name="WebServer")
        web_thread.start()
        
        # Wait a moment for web server to start
        time.sleep(2)
        
        if web_thread.is_alive():
            logger.info("✅ Web server started successfully!")
        else:
            logger.warning("⚠️ Web server thread not responding")
        
        # Start Discord bot with retry logic
        start_bot_with_retry(token, max_retries=3)
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Critical startup error: {e}")
        exit(1)
    finally:
        logger.info("🔄 Bot shutdown complete")