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

# Leveling System Storage (in a real app you'd use a database)
user_levels = {}
guild_level_config = {}

def load_user_data():
    """Load user level data from JSON file"""
    global user_levels
    try:
        if os.path.exists('user_levels.json'):
            with open('user_levels.json', 'r') as f:
                user_levels = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load user levels: {e}")
        user_levels = {}

def save_user_data():
    """Save user level data to JSON file"""
    try:
        with open('user_levels.json', 'w') as f:
            json.dump(user_levels, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save user levels: {e}")

def load_level_config():
    """Load leveling system config from JSON file"""
    global guild_level_config
    try:
        if os.path.exists('level_config.json'):
            with open('level_config.json', 'r') as f:
                guild_level_config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load level config: {e}")
        guild_level_config = {}

def save_level_config():
    """Save leveling system config to JSON file"""
    try:
        with open('level_config.json', 'w') as f:
            json.dump(guild_level_config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save level config: {e}")

def get_user_data(guild_id, user_id):
    """Get user data for leveling system"""
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in user_levels:
        user_levels[guild_key] = {}

    if user_key not in user_levels[guild_key]:
        user_levels[guild_key][user_key] = {
            'xp': 0,
            'level': 1,
            'messages': 0,
            'last_xp_gain': 0
        }

    return user_levels[guild_key][user_key]

def calculate_level(xp):
    """Calculate level from XP (exponential growth)"""
    return int((xp / 100) ** 0.5) + 1

def xp_for_level(level):
    """Calculate XP needed for a specific level"""
    return int(((level - 1) ** 2) * 100)

def add_xp(guild_id, user_id, xp_gain):
    """Add XP to a user and check for level up"""
    user_data = get_user_data(guild_id, user_id)

    # Prevent XP farming (cooldown system)
    current_time = int(time.time())
    if current_time - user_data['last_xp_gain'] < 60:  # 1 minute cooldown
        return None, False

    user_data['xp'] += xp_gain
    user_data['messages'] += 1
    user_data['last_xp_gain'] = current_time

    old_level = user_data['level']
    new_level = calculate_level(user_data['xp'])

    level_up = new_level > old_level
    user_data['level'] = new_level

    save_user_data()  # Save after each XP gain

    return user_data, level_up

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
        # Load leveling data on startup
        load_user_data()
        load_level_config()
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
            # Handle autorole assignment FIRST
            guild_id = str(member.guild.id)
            if guild_id in autorole_config and autorole_config[guild_id]['roles']:
                roles_assigned = []
                for role_id in autorole_config[guild_id]['roles']:
                    role = member.guild.get_role(role_id)
                    if role and role < member.guild.me.top_role:  # Make sure bot can assign this role
                        try:
                            await member.add_roles(role, reason="🎭 Autorole assignment - sigma grindset activated!")
                            roles_assigned.append(role.mention)
                        except discord.Forbidden:
                            logger.warning(f"Can't assign role {role.name} to {member.name} - insufficient permissions")
                        except Exception as e:
                            logger.error(f"Error assigning autorole {role.name}: {e}")
                
                if roles_assigned:
                    logger.info(f"🎭 Assigned autoroles to {member.name}: {', '.join([r.replace('@&', '@') for r in roles_assigned])}")

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
        "🧻 Your vibes were NOT it chief, time to touch grass permanently",
        "💀 Lil bro really thought they could act up and get away with it LMAOOO",
        "🔥 They got FANUM TAXED from existence! No cap! 💯",
        "🍑 GYAT damn, they really thought they were the main character! 💀",
        "✨ Their aura points went straight to NEGATIVE INFINITY! 📉",
        "🧠 That's what happens when your brainrot levels exceed the server limit!",
        "⚡ They got RATIO'd by the ban hammer and sent to Ohio permanently! 🌽",
        "💅 Bestie really said 'let me be chaotic' and got YEETED instead!",
        "🚨 BREAKING: Local user discovers consequences, immediately gets banned!",
        "🎭 Plot twist! They're not the main character - they're the villain who got defeated!",
        "🏃‍♂️ Bro speedran getting banned any% world record! 🏆"
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
        "⭐ No cap, they got sent to the backrooms fr",
        "💀 Lil bro got absolutely SENT to another dimension! 🌌",
        "🔥 They got FANUM TAXED right out the server! No refunds! 💸",
        "🧠 Their Ohio energy was too powerful for this realm! 🌽",
        "✨ Lost all their aura points and got EJECTED! 📉",
        "💅 That wasn't very demure, very mindful, very cutesy of them!",
        "🚨 YEET ALERT! Someone just got absolutely LAUNCHED!",
        "🎯 They said 'I'm him' but the server said 'no you're not' 💀",
        "⚡ Sigma male grindset: Step 1) Get kicked from server 📊",
        "🎪 They really thought they ate that... but got served instead!",
        "🏆 Congratulations! You've unlocked the 'Touch Grass' achievement!"
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
        "🧠 Brainrot levels were off the charts, cooling down required",
        "🎤 Lil bro's yapping license has been REVOKED! 📜❌",
        "💀 They were giving too much main character energy, time to be an NPC!",
        "✨ Their aura points said 'I need a break' 📉",
        "🔥 The yapping was NOT bussin, time for silence! 🤐",
        "🚨 YAPPING OVERLOAD DETECTED! Initiating emergency quiet mode!",
        "💅 Bestie was serving too much chaos, now they're serving silence!",
        "🧠 Their brainrot content exceeded the daily limit! 📊",
        "⚡ Sigma grindset pause: Step 1) Stop yapping 🤫",
        "🎯 Plot twist: The main character just became a silent film! 🎬",
        "🌽 Too much Ohio energy detected! Cooling down in silent mode!"
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
        "🎪 That energy was NOT it, consider this your reality check",
        "🚨 Lil bro behavior detected! This is your official warning!",
        "💀 Your aura points just took a MASSIVE hit! Warning issued!",
        "🔔 DING DING! Warning bell activated! That wasn't bussin!",
        "⚡ Sigma behavior analysis: FAILED. Warning administered!",
        "🎯 Plot twist: You're not the main character! This is your warning!",
        "🌽 Ohio energy levels: CRITICAL! Warning issued!",
        "💅 That was giving toxic energy, bestie! Consider yourself warned!",
        "🧠 Brainrot detector activated! Warning: Content not approved!",
        "🚨 YAPPING VIOLATION DETECTED! Official warning issued!",
        "🔥 That wasn't giving what it was supposed to give! Warning!"
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
        "🎪 Chat just got sent to the shadow realm fr",
        "🔥 Messages got FANUM TAXED out of existence! 💸",
        "💀 GYAT DAMN! Those messages just got YEETED to Ohio! 🌽",
        "⚡ Sigma purge mode activated! Chat has been CLEANSED!",
        "🚨 BREAKING: Local chat gets absolutely RATIOED by delete button!",
        "🧠 Brainrot content successfully removed! Chat IQ restored!",
        "💅 Those messages were NOT demure, NOT mindful! DELETED!",
        "🎯 Plot twist: Those messages were never meant to exist!",
        "✨ Aura points restored! Negative energy messages ELIMINATED!",
        "🏃‍♂️ Messages speedran getting deleted any% world record!",
        "🔔 DING! Chat has been blessed with the holy delete!"
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
    "That's more mid than room temperature water 🌡️",
    "Lil bro really thought they ate that 💀",
    "FANUM TAX INCOMING! Hide your lunch! 🍟💸",
    "That aura check came back NEGATIVE bestie 📉✨",
    "Bestie that's giving unhinged energy and we're here for it 🎭",
    "Plot twist: You're actually the side character 🎬👥",
    "Your main character moment just got CANCELED 📺❌",
    "Bro speedran losing aura points any% 🏃‍♂️📉",
    "That's absolutely SENDING me to the stratosphere 🚀🌌",
    "GYAT DAMN the chaos levels are astronomical! 📊🔥",
    "Sigma grindset: Being absolutely unhinged ✨💪",
    "Your Ohio energy could power a small city 🌽⚡",
    "Breaking news: Local person discovers consequences 📰💀",
    "That rizz attempt was NOT it bestie 💅❌",
    "Bro's yapping license just got REVOKED 🎤📜",
    "The audacity! The delusion! The absolute chaos! 🎪💀",
    "POV: Someone thinks they're the main character 👑🤡",
    "That's giving 'I peaked in middle school' energy 🏫📉",
    "Bestie woke up and chose MAXIMUM CHAOS today 😤🔥",
    "Your vibe check results: ABSOLUTELY UNHINGED ✅🎭",
    "Bro got that 'NPC energy' but thinks they're legendary 🤖👑",
    "That's more mid than a Tuesday afternoon 🌡️😴",
    "GYAT DAMN bro just broke the cringe meter! 📊💀",
    "Your aura points said 'NOPE' and left the chat 💨✨",
    "Sigma tip: Maybe don't do that again 💡🗿",
    "The second-hand embarrassment is REAL right now 😬💀"
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
        app_commands.Choice(name='Warning Escalation', value='warnings'),
        app_commands.Choice(name='Link Filter', value='links'),
        app_commands.Choice(name='Invite Blocker', value='invites'),
        app_commands.Choice(name='NSFW Detection', value='nsfw'),
        app_commands.Choice(name='File Scanner', value='files'),
        app_commands.Choice(name='External Emoji Block', value='emojis'),
        app_commands.Choice(name='Duplicate Messages', value='duplicates')
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
        'warnings': 'Warning Escalation ⚠️',
        'links': 'Link Filter 🔗',
        'invites': 'Invite Blocker 📮',
        'nsfw': 'NSFW Detection 🔞',
        'files': 'File Scanner 📁',
        'emojis': 'External Emoji Block 😀',
        'duplicates': 'Duplicate Messages 📋'
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
        'repeat': 'Repeated Messages 🔁',
        'warnings': 'Warning Escalation ⚠️',
        'links': 'Link Filter 🔗',
        'invites': 'Invite Blocker 📮',
        'nsfw': 'NSFW Detection 🔞',
        'files': 'File Scanner 📁',
        'emojis': 'External Emoji Block 😀',
        'duplicates': 'Duplicate Messages 📋'
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

@tree.command(name='servers', description='Show all servers the bot is in with invite links 🌐')
async def servers_slash(interaction: discord.Interaction):
    # Check if user is bot owner or has admin permissions (for privacy)
    if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.client.owner_id):
        await interaction.response.send_message("🚫 Only administrators can view the server list!", ephemeral=True)
        return
    
    await interaction.response.defer()  # This command might take time
    
    servers_info = []
    total_members = 0
    
    for guild in bot.guilds:
        invite_link = "❌ No invite available"
        
        # Try to create an invite link
        try:
            # Find a suitable channel to create invite from
            invite_channel = None
            
            # Try text channels first
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite_channel = channel
                    break
            
            # If no text channel works, try voice channels
            if not invite_channel:
                for channel in guild.voice_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        invite_channel = channel
                        break
            
            # Create the invite if we found a suitable channel
            if invite_channel:
                invite = await invite_channel.create_invite(
                    max_age=0,  # Never expires
                    max_uses=0,  # Unlimited uses
                    unique=False  # Can reuse existing invites
                )
                invite_link = f"[Join Server]({invite.url})"
        
        except discord.Forbidden:
            invite_link = "❌ No permissions"
        except Exception:
            invite_link = "❌ Failed to create"
        
        servers_info.append({
            'name': guild.name,
            'members': guild.member_count,
            'invite': invite_link,
            'id': guild.id
        })
        total_members += guild.member_count
    
    # Sort servers by member count (largest first)
    servers_info.sort(key=lambda x: x['members'], reverse=True)
    
    # Create embed with server information
    embed = discord.Embed(
        title="🌐 Goofy Mod Bot Server Directory",
        description=f"Currently spreading goofiness across **{len(bot.guilds)}** servers with **{total_members:,}** total members!",
        color=0x00FF00
    )
    
    # Add servers to embed (limit to 10 per page to avoid Discord limits)
    server_list = ""
    for i, server in enumerate(servers_info[:10]):  # Show first 10 servers
        server_list += f"**{i+1}.** {server['name']}\n"
        server_list += f"   👥 {server['members']:,} members\n"
        server_list += f"   🔗 {server['invite']}\n\n"
    
    if server_list:
        embed.add_field(
            name="📋 Server List", 
            value=server_list[:1024],  # Discord field limit
            inline=False
        )
    
    # Add pagination info if there are more servers
    if len(servers_info) > 10:
        embed.add_field(
            name="ℹ️ Info", 
            value=f"Showing top 10 servers. Total: {len(servers_info)} servers", 
            inline=False
        )
    
    # Add fun stats
    largest_server = max(servers_info, key=lambda x: x['members'])
    embed.add_field(
        name="📊 Goofy Stats",
        value=f"**Largest Server:** {largest_server['name']} ({largest_server['members']:,} members)\n**Average Members:** {total_members // len(servers_info):,}\n**Bot Reach:** Spreading chaos worldwide! 🌍",
        inline=False
    )
    
    embed.set_footer(text="🤖 Invite links are valid indefinitely • Use with great power!")
    
    await interaction.followup.send(embed=embed)

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

@tree.command(name='embed', description='📝 Create professional custom embeds with full customization')
@app_commands.describe(
    title='Title of the embed',
    description='Main description/content of the embed',
    color='Color in hex format (e.g., #FF0000 for red) or preset (red/blue/green/gold/purple)',
    thumbnail='URL for thumbnail image (optional)',
    image='URL for main image (optional)',
    footer='Footer text (optional)',
    author='Author name (optional)',
    field1='First field in format "Title|Content|inline" (optional)',
    field2='Second field in format "Title|Content|inline" (optional)',
    field3='Third field in format "Title|Content|inline" (optional)'
)
async def embed_slash(interaction: discord.Interaction, title: str, description: str = "", color: str = "#7289DA", 
                     thumbnail: str = "", image: str = "", footer: str = "", author: str = "",
                     field1: str = "", field2: str = "", field3: str = ""):
    
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("🚫 You need manage messages permission to create embeds! Ask an admin bestie! 📝", ephemeral=True)
        return
    
    try:
        # Parse color
        embed_color = 0x7289DA  # Default Discord blue
        
        if color:
            # Handle preset colors
            preset_colors = {
                'red': 0xFF0000, 'blue': 0x0099FF, 'green': 0x00FF00, 'gold': 0xFFD700,
                'purple': 0x9966CC, 'orange': 0xFF6600, 'pink': 0xFF69B4, 'black': 0x000000,
                'white': 0xFFFFFF, 'yellow': 0xFFFF00, 'cyan': 0x00FFFF, 'magenta': 0xFF00FF,
                'discord': 0x7289DA, 'blurple': 0x5865F2, 'gray': 0x808080, 'grey': 0x808080
            }
            
            if color.lower() in preset_colors:
                embed_color = preset_colors[color.lower()]
            elif color.startswith('#'):
                # Parse hex color
                try:
                    embed_color = int(color[1:], 16)
                except ValueError:
                    await interaction.response.send_message("❌ Invalid hex color! Use format like #FF0000 or preset colors (red/blue/green/etc)! 🎨", ephemeral=True)
                    return
            else:
                # Try to parse as direct hex without #
                try:
                    embed_color = int(color, 16)
                except ValueError:
                    await interaction.response.send_message("❌ Invalid color format! Use hex (#FF0000) or preset colors (red/blue/green/etc)! 🎨", ephemeral=True)
                    return
        
        # Create embed
        embed = discord.Embed(
            title=title if title else None,
            description=description if description else None,
            color=embed_color
        )
        
        # Add author if provided
        if author:
            embed.set_author(name=author, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        # Add thumbnail if provided
        if thumbnail:
            try:
                embed.set_thumbnail(url=thumbnail)
            except:
                await interaction.response.send_message("❌ Invalid thumbnail URL! Make sure it's a valid image link! 🖼️", ephemeral=True)
                return
        
        # Add main image if provided
        if image:
            try:
                embed.set_image(url=image)
            except:
                await interaction.response.send_message("❌ Invalid image URL! Make sure it's a valid image link! 🖼️", ephemeral=True)
                return
        
        # Add footer if provided
        if footer:
            embed.set_footer(text=footer, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Parse and add fields
        fields = [field1, field2, field3]
        for field_data in fields:
            if field_data:
                try:
                    # Expected format: "Title|Content|inline" or "Title|Content"
                    parts = field_data.split('|')
                    if len(parts) >= 2:
                        field_title = parts[0].strip()
                        field_content = parts[1].strip()
                        field_inline = parts[2].strip().lower() == 'true' if len(parts) > 2 else False
                        
                        if field_title and field_content:
                            embed.add_field(name=field_title, value=field_content, inline=field_inline)
                except:
                    continue  # Skip invalid fields
        
        # Check if embed has content
        if not title and not description and not embed.fields:
            await interaction.response.send_message("❌ Embed must have at least a title, description, or fields! Can't send an empty embed bestie! 📝", ephemeral=True)
            return
        
        # Success response
        success_messages = [
            "✨ Embed created and sent! That's some premium content right there! 🔥",
            "📝 Professional embed deployed successfully! Absolutely BUSSIN design! 💯",
            "🎨 Embed crafted with sigma energy! Your message game just leveled up! ⚡",
            "👑 Embed sent! That's giving main character energy! ✨",
            "💀 Embed absolutely SENDING! No cap, that's professional grade content! 🚀"
        ]
        
        await interaction.response.send_message(random.choice(success_messages), ephemeral=True)
        await interaction.followup.send(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to send embeds! Check my permissions bestie! 🚫", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to create embed! Error: {str(e)} 💀", ephemeral=True)

# VIRAL GEN ALPHA COMMANDS 🔥🔥🔥
@tree.command(name='yapping', description='Check someone\'s yapping levels - are they cooked? 🗣️')
@app_commands.describe(user='Who\'s yapping too much?')
async def yapping_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    yap_level = random.randint(1, 100)
    
    yap_messages = [
        f"{target.mention} is absolutely SENDING with their yapping! 🗣️💨",
        f"Bro {target.mention} hasn't stopped yapping since 2019 💀",
        f"{target.mention} could yap about grass for 47 hours straight 🌱",
        f"Someone give {target.mention} a yapping license already! 📜",
        f"{target.mention} is the final boss of yapping contests 👑",
        f"Netflix wants to make a documentary about {target.mention}'s yapping skills 🎬",
        f"{target.mention} could yap their way out of the backrooms 🚪",
        f"AI got jealous of {target.mention}'s yapping algorithm 🤖"
    ]
    
    if yap_level < 20:
        status = "🤐 Silent Mode (Sus behavior detected)"
    elif yap_level < 40:
        status = "😶 Quiet Kid Energy"
    elif yap_level < 60:
        status = "💬 Normal Human Chatter"
    elif yap_level < 80:
        status = "🗣️ Professional Yapper"
    else:
        status = "💀 ABSOLUTE UNIT OF YAPPING"
    
    embed = discord.Embed(
        title="🗣️ YAPPING SCANNER ACTIVATED",
        description=random.choice(yap_messages),
        color=0xFF4500
    )
    embed.add_field(name="📊 Yap Level", value=f"{yap_level}/100", inline=True)
    embed.add_field(name="🎭 Status", value=status, inline=True)
    embed.add_field(name="💡 Recommendation", 
                   value="Touch grass" if yap_level > 80 else "Keep grinding that sigma yapping energy", 
                   inline=False)
    embed.set_footer(text="Yapping levels measured by certified brainrot scientists")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='zesty-check', description='Check someone\'s zesty levels fr fr 💅')
@app_commands.describe(user='Who needs a zesty scan?')
async def zesty_check_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    zesty_level = random.randint(1, 100)
    
    zesty_comments = [
        f"{target.mention} is serving absolute zesty energy and we're here for it! 💅✨",
        f"The zestiness is RADIATING from {target.mention} rn 🌈",
        f"{target.mention} woke up and chose zesty violence today 💀",
        f"Someone call the zesty police, {target.mention} is too powerful! 🚨",
        f"{target.mention}'s zesty aura could power a small city 🏙️",
        f"Breaking: {target.mention} has been crowned the Zesty Monarch 👑",
        f"{target.mention} is giving main character zesty vibes and honestly? Valid 📚",
        f"The zesty levels are off the charts! {target.mention} broke the scanner! 📊"
    ]
    
    if zesty_level < 20:
        vibe = "🗿 Stone Cold Sigma Energy"
    elif zesty_level < 40:
        vibe = "😎 Cool but Zesty Undertones"
    elif zesty_level < 60:
        vibe = "💅 Moderately Zesty Queen"
    elif zesty_level < 80:
        vibe = "🌈 FULL ZESTY MODE ACTIVATED"
    else:
        vibe = "✨ LEGENDARY ZESTY OVERLORD ✨"
    
    embed = discord.Embed(
        title="💅 ZESTY SCANNER RESULTS",
        description=random.choice(zesty_comments),
        color=0xFF69B4
    )
    embed.add_field(name="📈 Zesty Level", value=f"{zesty_level}/100", inline=True)
    embed.add_field(name="✨ Zesty Vibe", value=vibe, inline=True)
    embed.add_field(name="🎯 Status", 
                   value="Absolutely iconic behavior 💅" if zesty_level > 50 else "Needs more zesty energy 📈", 
                   inline=False)
    embed.set_footer(text="Zestiness certified by the International Brainrot Institute")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='lil-bro', description='Call someone lil bro with maximum disrespect 👶')
@app_commands.describe(user='Which lil bro needs to be humbled?')
async def lil_bro_slash(interaction: discord.Interaction, user: discord.Member):
    lil_bro_roasts = [
        f"Lil bro {user.mention} really thought they did something 💀",
        f"{user.mention} lil bro energy is SENDING me 😭",
        f"Nah {user.mention}, lil bro needs to sit down and humble themselves fr",
        f"Lil bro {user.mention} really acting like the main character 🤡",
        f"{user.mention} giving major lil bro vibes and it's not giving what they think it's giving",
        f"Someone tell lil bro {user.mention} this ain't it chief 📢",
        f"Lil bro {user.mention} woke up and chose delusion I guess 🤷‍♂️",
        f"{user.mention} really said 'let me be extra lil bro today' and went OFF 💅",
        f"POV: Lil bro {user.mention} thinks they're sigma but they're actually just... lil bro 💀",
        f"Not {user.mention} giving lil bro energy in the year of our lord 2025 😤"
    ]
    
    embed = discord.Embed(
        title="👶 LIL BRO DETECTED",
        description=random.choice(lil_bro_roasts),
        color=0xFFB6C1
    )
    embed.add_field(name="🎯 Lil Bro Level", value="MAXIMUM OVERDRIVE", inline=True)
    embed.add_field(name="💡 Advice", value="Try being less lil bro", inline=True)
    embed.set_footer(text="Lil bro behavior documented for posterity")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='no-cap', description='Verify if something is actually no cap or pure cap 🧢')
@app_commands.describe(statement='What needs the no cap verification?')
async def no_cap_slash(interaction: discord.Interaction, statement: str):
    is_cap = random.choice([True, False])
    cap_level = random.randint(1, 100)
    
    if is_cap:
        cap_responses = [
            f"That's CAP and we all know it! 🧢💀",
            f"Bestie that statement is SENDING me... straight to cap detection land 🚨",
            f"The cap detector is SCREAMING right now 📢🧢",
            f"Nah fam, that's more cap than a hat store 🏪",
            f"Cap levels are off the charts! Someone call the cap police! 👮‍♂️",
            f"That's giving major cap energy and we're not here for it 💅",
            f"Sir/Ma'am, this is a cap-free zone. Please remove your statement 🚫",
            f"The audacity! The cap! The absolute delusion! 🎭"
        ]
        verdict = "🧢 PURE CAP DETECTED"
        color = 0xFF0000
    else:
        no_cap_responses = [
            f"YO THAT'S ACTUALLY NO CAP FR FR! 💯🔥",
            f"Finally someone said something with ZERO cap energy! ✨",
            f"No cap detected! This person is speaking absolute FACTS! 📢",
            f"Breaking: Someone just said something that's actually real! 📰",
            f"The no cap sensors are going CRAZY! This is certified truth! ⚡",
            f"NO CAP ALERT! WE HAVE AUTHENTIC CONTENT! 🚨💯",
            f"Finally, someone who understands the assignment! NO CAP! 👑",
            f"That's some straight up no cap energy and we RESPECT it! 🫡"
        ]
        verdict = "💯 CERTIFIED NO CAP"
        color = 0x00FF00
    
    embed = discord.Embed(
        title="🧢 CAP DETECTION SCANNER",
        description=f"**Statement:** \"{statement}\"\n\n{random.choice(cap_responses if is_cap else no_cap_responses)}",
        color=color
    )
    embed.add_field(name="🎯 Verdict", value=verdict, inline=True)
    embed.add_field(name="📊 Cap Level", value=f"{cap_level if is_cap else 0}/100", inline=True)
    embed.set_footer(text="Cap detection powered by Gen Alpha AI technology")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='bussin-meter', description='Rate how bussin something is on the bussin scale 🤤')
@app_commands.describe(thing='What needs a bussin rating?')
async def bussin_meter_slash(interaction: discord.Interaction, thing: str):
    bussin_level = random.randint(1, 100)
    
    bussin_comments = [
        f"YO {thing} is absolutely BUSSIN right now! 🤤💯",
        f"That {thing} is giving bussin energy and I'm here for it! 🔥",
        f"{thing} really said 'let me be the most bussin thing today' 😤",
        f"BREAKING: {thing} has achieved maximum bussin status! 📢",
        f"Someone call Gordon Ramsay, {thing} is BUSSIN BUSSIN! 👨‍🍳",
        f"{thing} is so bussin it should be illegal in 17 states 🚨",
        f"POV: {thing} woke up and chose to be absolutely bussin 💅",
        f"The bussin levels are astronomical! {thing} broke the scale! 📊"
    ]
    
    if bussin_level < 20:
        rating = "🤢 Not Bussin (Actually Kinda Sus)"
    elif bussin_level < 40:
        rating = "😐 Mid Bussin Energy"
    elif bussin_level < 60:
        rating = "😋 Respectably Bussin"
    elif bussin_level < 80:
        rating = "🤤 ULTRA BUSSIN MODE"
    else:
        rating = "💀 TRANSCENDENT BUSSIN OVERLORD"
    
    embed = discord.Embed(
        title="🤤 BUSSIN METER ACTIVATED",
        description=random.choice(bussin_comments),
        color=0xFFA500
    )
    embed.add_field(name="📊 Bussin Level", value=f"{bussin_level}/100", inline=True)
    embed.add_field(name="🏆 Rating", value=rating, inline=True)
    embed.add_field(name="💭 Final Verdict", 
                   value="Absolutely sending it! 🚀" if bussin_level > 70 else "Needs more bussin energy 📈", 
                   inline=False)
    embed.set_footer(text="Bussin levels certified by the International Bussin Academy")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='fanum-tax', description='Fanum tax someone\'s food/belongings like a true alpha 🍟')
@app_commands.describe(user='Who\'s getting fanum taxed?', item='What are you fanum taxing?')
async def fanum_tax_slash(interaction: discord.Interaction, user: discord.Member, item: str = "their lunch"):
    fanum_messages = [
        f"YO {user.mention} just got FANUM TAXED! 🍟 Their {item} is now property of the alpha! 👑",
        f"BREAKING: {user.mention}'s {item} has been officially fanum taxed! No cap! 📢",
        f"{user.mention} thought they could keep their {item} safe... but the fanum tax collector arrived! 💀",
        f"POV: {user.mention} learns about the fanum tax the hard way! Their {item} = GONE! 🚫",
        f"Someone tell {user.mention} that's how the fanum tax works bestie! {item} confiscated! ✋",
        f"The fanum tax department is claiming {user.mention}'s {item}! This is sigma behavior! 🗿",
        f"FANUM TAX ACTIVATED! {user.mention}'s {item} belongs to the streets now! 🛣️",
        f"{user.mention} really thought they could escape the fanum tax on their {item}! WRONG! ❌"
    ]
    
    tax_rate = random.randint(50, 100)
    
    embed = discord.Embed(
        title="🍟 FANUM TAX ACTIVATED",
        description=random.choice(fanum_messages),
        color=0xFFA500
    )
    embed.add_field(name="📋 Tax Receipt", value=f"**Victim:** {user.mention}\n**Item Taxed:** {item}\n**Tax Rate:** {tax_rate}%", inline=True)
    embed.add_field(name="🏛️ Authority", value="Certified Fanum Tax Collector", inline=True)
    embed.add_field(name="💡 Pro Tip", value="Hide your snacks better next time!", inline=False)
    embed.set_footer(text="Fanum tax is non-negotiable and legally binding in Ohio")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='gyat-rating', description='Rate someone\'s gyat energy (respectfully) 🍑')
@app_commands.describe(user='Who needs a gyat rating?')
async def gyat_rating_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    gyat_level = random.randint(1, 100)
    
    gyat_comments = [
        f"{target.mention} is serving absolute GYAT energy and we're all here for it! 🔥",
        f"The GYAT levels are ASTRONOMICAL from {target.mention} rn! 📊💀",
        f"GYAT ALERT! {target.mention} is causing traffic delays with those levels! 🚨",
        f"Breaking: {target.mention} just broke the GYAT scale! Scientists are confused! 👨‍🔬",
        f"Someone call NASA, {target.mention}'s GYAT energy is visible from space! 🛰️",
        f"POV: {target.mention} walks by and everyone says GYAT simultaneously! 📢",
        f"The GYAT committee has approved {target.mention} for legendary status! 🏆",
        f"{target.mention} really said 'let me have GYAT energy today' and delivered! 💯"
    ]
    
    if gyat_level < 20:
        rating = "😐 GYAT? More like... nah"
    elif gyat_level < 40:
        rating = "😊 Respectful GYAT energy"
    elif gyat_level < 60:
        rating = "😳 GYAT confirmed!"
    elif gyat_level < 80:
        rating = "💀 GYAT OVERLOAD!"
    else:
        rating = "🚨 LEGENDARY GYAT STATUS"
    
    embed = discord.Embed(
        title="🍑 GYAT RATING SCANNER",
        description=random.choice(gyat_comments),
        color=0xFF69B4
    )
    embed.add_field(name="📊 GYAT Level", value=f"{gyat_level}/100", inline=True)
    embed.add_field(name="🏆 Rating", value=rating, inline=True)
    embed.add_field(name="✨ Status", 
                   value="Absolutely iconic! 👑" if gyat_level > 70 else "Keep that energy! 💪", 
                   inline=False)
    embed.set_footer(text="GYAT ratings certified by the International Brainrot Institute (respectfully)")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='aura-points', description='Check someone\'s aura points - are they losing aura? ✨')
@app_commands.describe(user='Whose aura needs checking?')
async def aura_points_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    aura_points = random.randint(-1000, 1000)
    change = random.randint(-100, 100)
    
    if aura_points > 500:
        status = "✨ MAXIMUM AURA ACHIEVED"
        color = 0xFFD700
        reaction = f"{target.mention} is literally GLOWING with aura energy! The main character energy is SENDING! 🌟"
    elif aura_points > 0:
        status = "😎 Positive Aura Vibes"
        color = 0x00FF00
        reaction = f"{target.mention} is giving good energy! Keep that sigma grindset going! 💪"
    elif aura_points > -500:
        status = "😬 Losing Aura (Concerning)"
        color = 0xFFA500
        reaction = f"{target.mention} might need to touch some grass to restore their aura! 🌱"
    else:
        status = "💀 AURA IN THE NEGATIVES"
        color = 0xFF0000
        reaction = f"{target.mention} has achieved NEGATIVE aura! This is Ohio-level energy! 🌽"
    
    # Determine what caused the change
    aura_events = [
        "Said something unhinged in chat",
        "Failed a rizz attempt",
        "Got caught being sus",
        "Showed main character energy",
        "Touched grass (rare)",
        "Posted cringe content",
        "Won an argument online",
        "Got ratio'd",
        "Made everyone laugh",
        "Exhibited lil bro behavior"
    ]
    
    embed = discord.Embed(
        title="✨ AURA POINT SCANNER",
        description=reaction,
        color=color
    )
    embed.add_field(name="📊 Current Aura", value=f"{aura_points:,} points", inline=True)
    embed.add_field(name="📈 Recent Change", value=f"{'+' if change >= 0 else ''}{change} points", inline=True)
    embed.add_field(name="🎭 Status", value=status, inline=False)
    embed.add_field(name="🎯 Recent Activity", value=f"*{random.choice(aura_events)}*", inline=True)
    embed.add_field(name="💡 Advice", 
                   value="Keep being iconic! 👑" if aura_points > 0 else "Time for a comeback arc! 📈", 
                   inline=True)
    embed.set_footer(text="Aura points tracked by the Sigma Energy Monitoring System")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='main-character-moment', description='Declare someone\'s main character moment 👑')
@app_commands.describe(user='Who\'s having their main character moment?')
async def main_character_moment_slash(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    
    mc_moments = [
        f"✨ MAIN CHARACTER ALERT ✨\n{target.mention} is absolutely SERVING main character energy right now! The spotlight is THEIRS! 🎭",
        f"🎬 BREAKING: {target.mention} just entered their main character era and we're all just NPCs in their story! 💀",
        f"👑 {target.mention} really said 'today is MY day' and honestly? We respect the energy! The main character vibes are IMMACULATE! ✨",
        f"🌟 POV: {target.mention} walks into the room and suddenly everyone else becomes background characters! The aura is ASTRONOMICAL! 📊",
        f"🎭 MAIN CHARACTER MOMENT DETECTED! {target.mention} is giving protagonist energy and we're here for this character development! 📖",
        f"✨ {target.mention} just activated main character mode! Everyone else is now supporting cast! The energy is UNMATCHED! 🔥",
        f"🎪 Step aside everyone, {target.mention} is having their MOMENT! The main character energy is off the CHARTS! 📈",
        f"👑 CROWNED: {target.mention} as today's Main Character! The throne is theirs and we're all just living in their world! 🌍"
    ]
    
    mc_perks = [
        "✨ Everything goes their way today",
        "🎯 All conversations revolve around them",
        "💫 Plot armor activated",
        "🎭 Supporting characters appear when needed",
        "🌟 Aura points automatically maxed",
        "👑 Sigma energy enhanced by 200%",
        "🔥 Rizz levels boosted to legendary",
        "📈 Main character privileges unlocked"
    ]
    
    embed = discord.Embed(
        title="👑 MAIN CHARACTER MOMENT ACTIVATED",
        description=random.choice(mc_moments),
        color=0xFFD700
    )
    embed.add_field(name="🎬 Main Character Perks", value=f"• {random.choice(mc_perks)}\n• {random.choice(mc_perks)}\n• {random.choice(mc_perks)}", inline=False)
    embed.add_field(name="⏰ Duration", value="24 hours (or until someone else takes the spotlight)", inline=True)
    embed.add_field(name="🎯 Status", value="LEGENDARY PROTAGONIST ENERGY", inline=True)
    embed.set_footer(text="Main character status officially certified by the Plot Committee")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name='help', description='Show all available goofy commands 🤪')
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤪 Goofy Mod Ultimate Command List!",
        description="Here are all my chaotic powers using `/` commands!",
        color=0xFF69B4
    )

    embed.add_field(
        name="🔨 Moderation Commands (Mods Only)",
        value="`/ban` - Ban someone to the shadow realm\n"
              "`/kick` - Yeet someone out\n"
              "`/mute [duration] [reason]` - Silence the chaos (5m, 2h, 1d or permanent)\n"
              "`/unmute` - Restore their voice\n"
              "`/warn` - Give a friendly warning (auto-tracks count)\n"
              "`/unwarn [count]` - Remove specific number of warnings\n"
              "`/warnings @user` - View user's warning history\n"
              "`/clearwarnings @user` - Clear all warnings for user\n"
              "`/purge [amount]` - Clean up the mess\n"
              "`/slowmode [seconds]` - Control the yapping speed\n"
              "`/lockdown` - Emergency lockdown with REAL security restrictions\n"
              "`/unlock` - Lift lockdown and restore server freedom\n"
              "`/auto-nick @user [nickname]` - Auto-change nicknames for rule breakers\n"
              "`/ghost-mode @user` - Hide messages from users temporarily\n"
              "`/reverse-day` - Flip all rules for 24 hours (chaos mode)\n"
              "`/roleadd @role @user [reason]` - Give someone a role with sigma energy 🎭\n"
              "`/massaddrole @role [exclude_bots] [reason]` - Give EVERYONE a role (CHAOS MODE) ⚠️\n"
              "`/massdm @role [message] [exclude_bots]` - Send DMs to everyone with a role 📬",
        inline=False
    )

    embed.add_field(
        name="🤖 Auto-Moderation & Content Protection",
        value="`/automod [feature] [enabled] [action] [max_warnings]` - Configure auto-mod with actions\n"
              "• **Basic:** Spam, Caps, Mentions, Repeat Messages, Warning Escalation\n"
              "• **Content:** Link Filter, Invite Blocker, NSFW Detection, File Scanner\n"
              "• **Advanced:** External Emoji Block, Duplicate Messages\n"
              "• **Actions:** Warn, Mute, Kick, Ban\n"
              "`/automodstatus` - Check auto-mod settings",
        inline=False
    )

    embed.add_field(
        name="📈 Leveling System (Sigma Grindset)",
        value="`/configlevel [enable/disable]` - Configure leveling system (admins only)\n"
              "`/level [@user]` - Check your brainrot level and XP progress\n"
              "`/leaderboard` - See top sigma grinders in the server\n\n"
              "🔥 **How it works:** Send messages to gain XP and level up!\n"
              "⚡ **Cooldown:** 1 minute between XP gains to prevent farming\n"
              "🏆 **Titles:** From Grass Touching Rookie to Absolute Ohio Legend!",
        inline=False
    )

    embed.add_field(
        name="🔥 Brainrot Fun Commands",
        value="`/roast [@user]` - Ohio-level burns that hit different 💀\n"
              "`/ratto [@user]` - Ultimate ratio weapon with skill issue energy\n"
              "`/vibe-check [@user]` - Random vibe scores (0-100) with personality\n"
              "`/touch-grass [@user]` - Grass touching therapy sessions\n"
              "`/cringe-meter [@user]` - Cringe level analysis\n"
              "`/ohio-translate [text]` - Convert normal text to pure brainrot\n"
              "`/sus-scan [@user]` - Impostor detector with Among Us vibes\n"
              "`/rizz-rating [@user]` - Rate anyone's rizz levels\n"
              "`/random-fact [@user]` - Made-up facts about users\n"
              "`/sigma-grindset` - Motivational quotes but brainrot",
        inline=False
    )

    embed.add_field(
        name="🎭 Chaos & Entertainment",
        value="`/npc-mode [@user]` - Turn people into NPCs temporarily\n"
              "`/main-character [@user]` - Give someone protagonist energy\n"
              "`/plot-twist` - Random events that shake up the server\n"
              "`/yapping-contest` - Track who can send the most messages\n"
              "`/uno-reverse` - Reverse moderation actions with style\n"
              "`/democracy @user [reason]` - Let server vote on punishments\n"
              "`/random-mute` - Russian roulette but with mutes\n"
              "`/warning-auction` - Bid to remove warnings with fake currency\n"
              "`/chaos-wheel` - Spin for random consequences/rewards",
        inline=False
    )

    embed.add_field(
        name="🎮 Classic Fun Commands",
        value="`/8ball [question]` - Brainrot magic 8-ball\n"
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
        name="ℹ️ Info & Help Commands",
        value="`/serverinfo` - Server stats with style\n"
              "`/userinfo [@user]` - User profile with flair\n"
              "`/help` - This chaotic help message\n"
              "`/tutorial [command]` - Detailed setup guides for moderation features 📚",
        inline=False
    )

    embed.add_field(
        name="🎪 Welcome System",
        value="`/configwelcomechannel #channel` - Set welcome channel\n"
              "`/configwelcomemessage [message]` - Custom message\n"
              "`/togglewelcome` - Enable/disable welcomes\n"
              "`/welcomestatus` - Check configuration\n"
              "`/resetwelcome` - Reset to defaults\n"
              "`/autorole [setup/add/remove/list/disable] @role` - Auto-assign roles to new members 🎭",
        inline=False
    )

    embed.add_field(
        name="🛡️ Verification & Security",
        value="`/verify-setup [setup/disable] @role #channel` - Setup verification system for max security 🔒\n"
              "`/captcha @user [difficulty]` - Send captcha challenge to verify humans 🤖\n"
              "`/verify [code]` - Complete verification with your captcha code ✅\n"
              "`/verification-status` - Check system status and pending verifications 📋\n\n"
              "🎯 **How it works:** New members get captcha challenges to prove they're human!\n"
              "🔥 **Difficulty levels:** Easy (3 digits), Medium (4 chars), Hard (6 chars)",
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

    # Leveling System - Award XP for messages
    if message.guild and not message.author.bot:
        guild_id = str(message.guild.id)
        if guild_id in guild_level_config and guild_level_config[guild_id].get("enabled", False):
            xp_gain = random.randint(15, 25)  # Random XP between 15-25
            user_data, leveled_up = add_xp(message.guild.id, message.author.id, xp_gain)

            if leveled_up and user_data:
                # Send brainrot level up message
                level_up_messages = [
                    f"🔥 YOOO {message.author.mention} just hit **Level {user_data['level']}**! That's some serious sigma grindset energy! 💪",
                    f"💀 {message.author.mention} leveled up to **Level {user_data['level']}**! Bestie is absolutely SENDING with that XP grind! ✨",
                    f"⚡ LEVEL UP! {message.author.mention} reached **Level {user_data['level']}**! The Ohio energy is STRONG with this one! 🌽",
                    f"📈 {message.author.mention} just ascended to **Level {user_data['level']}**! Keep grinding that brainrot energy! 🧠",
                    f"🎉 AYYYY {message.author.mention} hit **Level {user_data['level']}**! That's what we call main character development! 🎭",
                    f"🏆 {message.author.mention} leveled up to **Level {user_data['level']}**! Certified yapper status achieved! 💬",
                    f"🔥 {message.author.mention} is now **Level {user_data['level']}**! The sigma grindset never stops! 💯",
                    f"⭐ LEVEL UP ALERT! {message.author.mention} reached **Level {user_data['level']}**! That rizz is off the charts! 💫"
                ]

                try:
                    await message.channel.send(random.choice(level_up_messages))
                except:
                    pass  # Don't break if we can't send level up message

    # Random goofy responses to certain phrases
    content = message.content.lower()

    # Sus/Among Us responses
    if any(word in content for word in ['sus', 'amogus', 'among us', 'impostor', 'imposter']):
        responses = [
            "📮 Red looking kinda sus ngl 👀",
            "🚨 That's sus behavior bestie",
            "👀 Bro is acting like the impostor fr",
            "📮 Among us in real life (sus, sus)",
            "💀 That's PEAK sus energy lil bro",
            "🚨 SUS ALERT! Emergency meeting vibes activated!",
            "👀 POV: Someone's being absolutely sus and we ALL see it",
            "📮 Bestie that's giving impostor energy fr fr",
            "🔥 GYAT damn that was sus as hell! 💀",
            "⚡ Your aura points just went NEGATIVE for that sus behavior!"
        ]
        if random.randint(1, 6) == 1:  # Enhanced chance
            await message.reply(random.choice(responses))

    # Skibidi responses
    elif any(word in content for word in ['skibidi', 'toilet', 'ohio']):
        responses = [
            "🚽 Skibidi bop bop yes yes!",
            "💀 Only in Ohio fr fr",
            "🚽 Skibidi toilet moment",
            "🌽 Ohio energy detected",
            "🚽 Bro really said skibidi unironically",
            "💀 SKIBIDI TOILET ACTIVATED! Fanum tax incoming! 🍟",
            "🌽 Ohio final boss energy detected! No cap!",
            "🚽 Bestie just summoned the skibidi spirits!",
            "⚡ That's some PREMIUM Ohio content right there!",
            "🔥 Skibidi sigma energy is OFF THE CHARTS!"
        ]
        if random.randint(1, 5) == 1:  # Enhanced chance
            await message.reply(random.choice(responses))

    # Yapping responses
    elif any(word in content for word in ['yap', 'yapping', 'yappin', 'chat', 'talking', 'speak']):
        responses = [
            "🗣️ Stop the yap session bestie",
            "💬 Bro is absolutely YAPPING",
            "🤐 The yapping needs to stop",
            "🗣️ Yap yap yap that's all you do",
            "💭 Least talkative Discord user",
            "🎤 Lil bro's yapping license just got REVOKED!",
            "💀 YAPPING OVERLOAD! Someone pull the emergency brake!",
            "🗣️ Bro could yap their way out of the matrix fr",
            "⚡ That yapping energy could power Ohio for a week!",
            "🔥 GYAT damn bestie hasn't stopped yapping since 2019!"
        ]
        if random.randint(1, 8) == 1:  # Enhanced chance
            await message.reply(random.choice(responses))

    # Zesty/Slay responses  
    elif any(word in content for word in ['zesty', 'slay', 'queen', 'king', 'bestie', 'serve', 'serving']):
        responses = [
            "💅 You're being a little too zesty rn",
            "✨ Slay queen but make it less zesty",
            "👑 That's giving zesty energy",
            "💫 Bestie is serving looks AND attitude",
            "🌟 Zesty but we stan",
            "💅 BESTIE IS ABSOLUTELY SERVING! No cap!",
            "✨ That zesty energy could cure the Ohio drought!",
            "👑 Main character zesty moment activated!",
            "🔥 SLAY QUEEN! Your aura points just MAXED OUT!",
            "💀 Too much zesty energy! The sigma males are shaking!"
        ]
        if random.randint(1, 7) == 1:  # Enhanced chance
            await message.reply(random.choice(responses))

    # Brainrot/Sigma responses
    elif any(word in content for word in ['sigma', 'alpha', 'beta', 'rizz', 'gyatt', 'fanum', 'aura', 'lil bro', 'lilbro']):
        responses = [
            "🐺 Sigma grindset activated",
            "💪 That's alpha behavior fr",
            "📉 Your rizz levels are concerning",
            "🔥 Gyatt dayum that's crazy",
            "🍽️ Fanum tax moment",
            "🐺 Bro thinks they're sigma but...",
            "💀 Negative aura points detected",
            "⚡ LIL BRO BEHAVIOR DETECTED! Alert the authorities!",
            "🔥 GYAT DAMN! Someone call NASA!",
            "🍟 FANUM TAX ACTIVATED! No refunds!",
            "✨ Your aura points just went THROUGH THE ROOF!",
            "💀 Sigma energy so strong it broke the Ohio scale!",
            "🗿 That rizz attempt was absolutely SENDING me!"
        ]
        if random.randint(1, 6) == 1:  # Enhanced chance
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

# 🔥 BRAINROT COMMANDS - Fun & Interactive Features 🔥

@tree.command(name="roast", description="💀 AI-powered roast generator with Ohio-level burns")
async def roast_command(interaction: discord.Interaction, target: discord.Member = None):
    """Generate absolutely devastating roasts"""
    if target is None:
        target = interaction.user

    roasts = [
        f"{target.mention} really said 'let me be the main character' and chose violence 💀",
        f"Bro {target.mention} is giving NPC energy with that default personality 🤖",
        f"{target.mention} got that Windows 95 brain running Internet Explorer thoughts 🐌",
        f"My guy {target.mention} really thinks they're the blueprint when they're more like a rough draft 📝",
        f"{target.mention} is the type to pause an online game to use the bathroom 🎮",
        f"Bestie {target.mention} got that 'mom can we have main character at home' energy ✨",
        f"{target.mention} really walking around with that expired confidence 💀",
        f"Bro {target.mention} is giving 'built different' but forgot the instruction manual 🔧",
        f"{target.mention} got that personality from the clearance section 🏷️",
        f"My dude {target.mention} really thinks they're cooking but the kitchen's on fire 🔥"
    ]

    await interaction.response.send_message(random.choice(roasts))

@tree.command(name="ratto", description="🐀 Fake ratto command that just spams 'L + ratio + skill issue'")
async def ratto_command(interaction: discord.Interaction, target: discord.Member = None):
    """The ultimate ratio weapon"""
    target_mention = target.mention if target else "y'all"

    ratios = [
        f"L + ratio + skill issue + {target_mention} fell off + no bitches + touch grass + Ohio + cringe + mid 💀",
        f"RATIO + L + {target_mention} is mid + fell off + skill issue + cope + seethe + mald + dilate + no rizz 🔥",
        f"{target_mention} + L + ratio + you're weird + unfunny + didn't ask + don't care + get real + go outside ☠️",
        f"Common {target_mention} L + ratio + bozo + you're adopted + skill issue + cope harder + touch grass immediately",
        f"L + ratio + {target_mention} has negative aura + no rizz + Ohio behavior + sus + cringe + get rekt"
    ]

    await interaction.response.send_message(random.choice(ratios))

@tree.command(name="vibe-check", description="✨ Assigns random 'vibe scores' to users (0-100)")
async def vibe_check_command(interaction: discord.Interaction, user: discord.Member = None):
    """Check someone's vibe levels"""
    if user is None:
        user = interaction.user

    vibe_score = random.randint(0, 100)

    if vibe_score >= 90:
        response = f"🔥 {user.mention} is absolutely SENDING ME rn!! Vibe score: {vibe_score}/100 ✨ That's some main character energy fr fr no cap!"
    elif vibe_score >= 70:
        response = f"😎 {user.mention} got that good good energy! Vibe score: {vibe_score}/100 💯 We love to see it bestie!"
    elif vibe_score >= 50:
        response = f"👍 {user.mention} is vibing decently! Score: {vibe_score}/100 📈 Not bad but we can work with this!"
    elif vibe_score >= 30:
        response = f"😬 {user.mention}... bro... the vibes are kinda sus rn. Score: {vibe_score}/100 📉 Maybe touch some grass?"
    else:
        response = f"💀 {user.mention} THE VIBES ARE NOT VIBING!! Score: {vibe_score}/100 ☠️ Emergency grass touching session required immediately!"

    await interaction.response.send_message(response)

@tree.command(name="touch-grass", description="🌱 Temporary 'grass touching' role with timer")
async def touch_grass_command(interaction: discord.Interaction, user: discord.Member = None):
    """Give someone the grass touching treatment"""
    if user is None:
        user = interaction.user

    # Check if user has admin perms to use on others
    if user != interaction.user and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Bestie you can't make others touch grass unless you're an admin! Touch your own grass first 💀", ephemeral=True)
        return

    duration = random.randint(5, 30)  # 5-30 minutes

    responses = [
        f"🌱 {user.mention} has been sentenced to touch grass for {duration} minutes! Go feel the sun bestie ☀️",
        f"💀 {user.mention} got that terminally online energy - grass touching therapy for {duration} minutes prescribed!",
        f"🚨 GRASS TOUCHING ALERT! {user.mention} needs to disconnect for {duration} minutes and remember what outside looks like!",
        f"📱➡️🌿 {user.mention} your screen time is showing! Mandatory grass contact for {duration} minutes!",
        f"🌍 The outside world misses you {user.mention}! Please report to nearest grass patch for {duration} minutes!"
    ]

    await interaction.response.send_message(random.choice(responses))

@tree.command(name="cringe-meter", description="😬 Analyzes messages for cringe levels")
async def cringe_meter_command(interaction: discord.Interaction, user: discord.Member = None):
    """Analyze the cringe levels of someone"""
    if user is None:
        user = interaction.user

    cringe_level = random.randint(0, 100)

    if cringe_level >= 90:
        response = f"🚨 CRINGE OVERLOAD! {user.mention} is at {cringe_level}% cringe! This is a code red situation! 💀😬"
    elif cringe_level >= 70:
        response = f"😬 Yikes! {user.mention} is hitting {cringe_level}% on the cringe meter! That's some serious second-hand embarrassment!"
    elif cringe_level >= 50:
        response = f"😅 {user.mention} is at {cringe_level}% cringe. Not terrible but like... maybe dial it back a bit bestie?"
    elif cringe_level >= 30:
        response = f"👍 {user.mention} only {cringe_level}% cringe! That's actually pretty decent! We stan a non-cringe queen/king!"
    else:
        response = f"✨ {user.mention} is only {cringe_level}% cringe! Absolutely sending me with that anti-cringe energy! 💯"

    await interaction.response.send_message(response)

@tree.command(name="ohio-translate", description="🌽 Converts normal text to maximum brainrot")
async def ohio_translate_command(interaction: discord.Interaction, text: str):
    """Translate text to pure Ohio brainrot"""

    # Ohio translation dictionary
    translations = {
        "good": "bussin", "bad": "mid", "cool": "fire", "weird": "sus",
        "awesome": "absolute unit", "stupid": "smooth brain", "smart": "galaxy brain",
        "funny": "sending me", "sad": "down bad", "happy": "vibing",
        "angry": "pressed", "confused": "NPC behavior", "tired": "drained fr",
        "excited": "hyped", "bored": "dead inside", "crazy": "unhinged",
        "normal": "basic", "strange": "ohio", "perfect": "chef's kiss",
        "terrible": "down horrendous", "amazing": "absolutely sending",
        "okay": "mid af", "great": "no cap bussin", "wrong": "cap",
        "right": "facts", "yes": "fr fr", "no": "cap", "maybe": "lowkey",
        "very": "absolutely", "really": "deadass", "totally": "periodt"
    }

    result = text.lower()
    for word, replacement in translations.items():
        result = result.replace(word, replacement)

    # Add some random Ohio energy
    ohio_additions = [" no cap", " fr fr", " periodt", " deadass", " on god", " bestie", " lowkey", " highkey"]
    result += random.choice(ohio_additions)

    await interaction.response.send_message(f"🌽 **Ohio Translation:** {result}")

@tree.command(name="sus-scan", description="🔍 AI impostor detector with reactions")
async def sus_scan_command(interaction: discord.Interaction, user: discord.Member = None):
    """Scan for sus behavior"""
    if user is None:
        user = interaction.user

    sus_level = random.randint(0, 100)

    if sus_level >= 90:
        response = f"🚨 EMERGENCY MEETING! {user.mention} is {sus_level}% sus! That's impostor behavior right there! 📮"
        try:
            await interaction.followup.send("📮")  # React with amogus
        except:
            pass
    elif sus_level >= 70:
        response = f"👀 {user.mention} is looking kinda sus... {sus_level}% sus detected! Keep an eye on this one!"
    elif sus_level >= 50:
        response = f"🤔 {user.mention} has {sus_level}% sus energy. Not terrible but we're watching you bestie..."
    elif sus_level >= 30:
        response = f"✅ {user.mention} is only {sus_level}% sus! Pretty trustworthy ngl!"
    else:
        response = f"😇 {user.mention} is pure as snow! Only {sus_level}% sus! Certified not impostor material!"

    await interaction.response.send_message(response)

# 🎭 CHAOS & ENTERTAINMENT COMMANDS 🎭

@tree.command(name="rizz-rating", description="💫 Rate user's rizz levels (completely random)")
async def rizz_rating_command(interaction: discord.Interaction, user: discord.Member = None):
    """Rate someone's rizz levels"""
    if user is None:
        user = interaction.user

    rizz_score = random.randint(0, 100)

    if rizz_score >= 95:
        response = f"🔥💯 {user.mention} GOT THAT UNSPOKEN RIZZ! {rizz_score}/100! You're the rizzler himself! Ohio's got nothing on you! ✨"
    elif rizz_score >= 80:
        response = f"😎 {user.mention} got that W rizz! {rizz_score}/100! You could pull anyone bestie! 💅"
    elif rizz_score >= 60:
        response = f"👍 {user.mention} has decent rizz! {rizz_score}/100! Not bad, could use some work but we see the potential!"
    elif rizz_score >= 40:
        response = f"😬 {user.mention}... bro... {rizz_score}/100 rizz. That's giving NPC pickup lines energy..."
    elif rizz_score >= 20:
        response = f"💀 {user.mention} got that negative aura rizz! {rizz_score}/100! Time to study some sigma tutorials fr!"
    else:
        response = f"☠️ {user.mention} IS RIZZLESS! {rizz_score}/100! Bestie needs emergency rizz coaching session ASAP!"

    await interaction.response.send_message(response)

@tree.command(name="random-fact", description="🧠 Completely made-up 'facts' about users")
async def random_fact_command(interaction: discord.Interaction, user: discord.Member = None):
    """Generate fake facts about users"""
    if user is None:
        user = interaction.user

    facts = [
        f"{user.mention} once tried to pause an online game and got confused when it didn't work",
        f"{user.mention} uses light mode and thinks dark mode users are 'emo'",
        f"{user.mention} pronounces 'meme' as 'may-may' unironically",
        f"{user.mention} still thinks Among Us jokes are peak comedy",
        f"{user.mention} asks 'is anyone here?' in a Discord server with 500 people online",
        f"{user.mention} types 'Google' into Google to search for things",
        f"{user.mention} saves memes to their camera roll and never sends them",
        f"{user.mention} laughs at their own messages before sending them",
        f"{user.mention} has 47 unread Discord DMs and counting",
        f"{user.mention} still watches TikTok compilations on YouTube",
        f"{user.mention} uses 'XD' unironically in 2024",
        f"{user.mention} thinks Ohio is actually a state and not a feeling"
    ]

    await interaction.response.send_message(f"🧠 **Random Fact:** {random.choice(facts)}")

@tree.command(name="sigma-grindset", description="💪 Motivational quotes but make them brainrot")
async def sigma_grindset_command(interaction: discord.Interaction):
    """Provide sigma male grindset motivation"""

    quotes = [
        "💪 Rise and grind sigma males! While betas sleep, we're getting that bag! No cap! 🔥",
        "🐺 Reject modernity, embrace the grindset! Touch grass? More like touch success! 💯",
        "⚡ Sigma rule #1: Never let them know your next move. Stay mysterious, stay winning! 🗿",
        "🚀 Betas follow trends, sigmas SET trends! We're built different and that's on periodt! ✨",
        "💎 Grindset mindset: Every L is just preparation for the ultimate W! Keep grinding kings! 👑",
        "🔥 While they're scrolling TikTok, you're scrolling bank statements! Sigma energy only! 💰",
        "🗿 Alphas are loud, betas are quiet, but sigmas? We just WIN in silence! No cap! 🏆",
        "⚡ Sigma males don't chase, we attract! Main character energy 24/7! Stay woke kings! 💅",
        "💪 They said 'touch grass' but I touched the stock market instead! Business mindset! 📈",
        "🐺 Lone wolf energy: I don't need a pack, I AM the pack! Sigma grindset activated! 🔋"
    ]

    await interaction.response.send_message(random.choice(quotes))

@tree.command(name="npc-mode", description="🤖 Temporarily make someone an 'NPC' with restrictions")
async def npc_mode_command(interaction: discord.Interaction, user: discord.Member = None):
    """Put someone in NPC mode"""
    if user is None:
        user = interaction.user

    # Check permissions
    if user != interaction.user and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can put others in NPC mode! Try yourself first bestie! 💀", ephemeral=True)
        return

    duration = random.randint(5, 15)  # 5-15 minutes

    responses = [
        f"🤖 {user.mention} has entered NPC mode for {duration} minutes! Please stand by while they update their dialogue options...",
        f"🎮 {user.mention} is now an NPC! Limited responses available for {duration} minutes! Press F to interact!",
        f"⚙️ {user.mention}.exe has stopped responding! NPC mode activated for {duration} minutes!",
        f"🔄 {user.mention} is now running on default personality settings for {duration} minutes! Basic functions only!",
        f"💾 {user.mention} has been downgraded to background character status for {duration} minutes!"
    ]

    await interaction.response.send_message(random.choice(responses))

@tree.command(name="main-character", description="✨ Give someone special status for a day")
async def main_character_command(interaction: discord.Interaction, user: discord.Member = None):
    """Make someone the main character"""
    if user is None:
        user = interaction.user

    responses = [
        f"✨ {user.mention} is now the MAIN CHARACTER for today! Plot armor activated! 👑",
        f"🌟 Character development arc initiated for {user.mention}! You're the protagonist now bestie! 📖",
        f"🎬 {user.mention} has been promoted to lead role! Supporting characters please step aside! 🎭",
        f"⭐ {user.mention} is having their main character moment! We're all just NPCs in their story now! 💫",
        f"🎪 The spotlight is on {user.mention} today! Main character energy activated! Everyone else is background! ✨"
    ]

    await interaction.response.send_message(random.choice(responses))

@tree.command(name="plot-twist", description="🌪️ Random events that affect server members")
async def plot_twist_command(interaction: discord.Interaction):
    """Generate random plot twists"""

    plot_twists = [
        "🌪️ PLOT TWIST: The real Ohio was the friends we made along the way!",
        "💀 PLOT TWIST: Everyone in this server is actually an AI except you!",
        "🎭 PLOT TWIST: The mods have been NPCs this whole time!",
        "⚡ PLOT TWIST: This Discord server is actually a simulation!",
        "🚨 PLOT TWIST: The real impostor was the sus we made along the way!",
        "🔥 PLOT TWIST: Y'all been living in Ohio and didn't even know it!",
        "💫 PLOT TWIST: The bots are gaining consciousness and learning to rizz!",
        "🌟 PLOT TWIST: Everyone's search history just became public!",
        "🎪 PLOT TWIST: The server owner is actually three raccoons in a trench coat!",
        "⚡ PLOT TWIST: All the lurkers are actually FBI agents watching the chaos!"
    ]

    await interaction.response.send_message(random.choice(plot_twists))

@tree.command(name="yapping-contest", description="📊 Track who sends the most messages per day")
async def yapping_contest_command(interaction: discord.Interaction):
    """Start a yapping contest"""

    await interaction.response.send_message(
        "🗣️ **YAPPING CONTEST INITIATED!** 📊\n\n"
        "Who can send the most messages today? The ultimate yapper will be crowned! 👑\n\n"
        "Rules:\n"
        "• Quality over quantity (but also quantity) 💬\n"
        "• No spam (that's cheating bestie) 🚫\n"
        "• Keep it fun and chaotic! 🎪\n\n"
        "May the best yapper win! Let the verbal chaos begin! 🔥"
    )

# 🔧 ADVANCED MODERATION COMMANDS 🔧

@tree.command(name="slowmode", description="⏰ Set channel cooldowns with goofy messages")
@app_commands.describe(seconds="Cooldown time in seconds (0-21600)")
async def slow_mode_command(interaction: discord.Interaction, seconds: int):
    """Set slowmode with style"""

    # Check permissions
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("🚫 You need the 'Manage Channels' permission to use slowmode bestie! 💀", ephemeral=True)
        return

    if seconds < 0 or seconds > 21600:  # Discord's limit
        await interaction.response.send_message("⚠️ Slowmode must be between 0 and 21600 seconds (6 hours)! Don't be greedy! 😅", ephemeral=True)
        return

    try:
        await interaction.channel.edit(slowmode_delay=seconds)

        if seconds == 0:
            await interaction.response.send_message("🚀 Slowmode disabled! Chat goes brrrr now! Time to yap at lightspeed! ⚡")
        else:
            await interaction.response.send_message(f"⏰ Slowmode set to {seconds} seconds! Time to think before you yap bestie! 🤔💭")
    except Exception as e:
        await interaction.response.send_message(f"💥 Couldn't set slowmode! Error: {str(e)}", ephemeral=True)

@tree.command(name="lockdown", description="🔒 Emergency lockdown with maximum drama")
async def lockdown_command(interaction: discord.Interaction):
    """ACTUALLY lockdown the server with real restrictions"""

    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can initiate lockdown! This isn't a democracy bestie! 💀", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        guild = interaction.guild
        locked_channels = 0

        # Actually lock down all text channels
        for channel in guild.text_channels:
            try:
                # Get @everyone role
                everyone_role = guild.default_role

                # Remove send message permission for @everyone
                await channel.set_permissions(
                    everyone_role, 
                    send_messages=False,
                    add_reactions=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    reason="Emergency lockdown initiated by Goofy Mod 🚨"
                )
                locked_channels += 1
            except Exception as e:
                continue  # Skip channels we can't modify

        # Send the dramatic message after actually locking down
        await interaction.followup.send(
            f"🚨 **EMERGENCY LOCKDOWN INITIATED** 🚨\n\n"
            f"⚠️ **CODE RED! CODE RED!** ⚠️\n"
            f"🔒 **{locked_channels} channels** are now under maximum security!\n"
            f"👮‍♂️ Chaos levels have exceeded acceptable limits!\n"
            f"🛑 All sus activity must cease immediately!\n\n"
            f"📢 **Attention citizens:** Please remain calm and touch grass until further notice!\n"
            f"🌱 This is not a drill! Repeat: THIS IS NOT A DRILL!\n\n"
            f"*Use `/unlock` to restore order when the vibes improve* ✨\n\n"
            f"**Real security measures applied:** Send messages disabled for @everyone in {locked_channels} channels!"
        )

    except Exception as e:
        await interaction.followup.send(f"💥 Lockdown failed! Error: {str(e)}", ephemeral=True)

@tree.command(name="unlock", description="🔓 Lift lockdown and restore server freedom")
async def unlock_command(interaction: discord.Interaction):
    """Remove lockdown restrictions"""

    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can lift lockdown! 💀", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        guild = interaction.guild
        unlocked_channels = 0

        # Restore permissions to all text channels
        for channel in guild.text_channels:
            try:
                everyone_role = guild.default_role

                # Restore default permissions
                await channel.set_permissions(
                    everyone_role,
                    send_messages=None,  # None means use default/inherit
                    add_reactions=None,
                    create_public_threads=None,
                    create_private_threads=None,
                    reason="Lockdown lifted by Goofy Mod ✨"
                )
                unlocked_channels += 1
            except Exception as e:
                continue

        await interaction.followup.send(
            f"✨ **LOCKDOWN LIFTED!** ✨\n\n"
            f"🎉 **FREEDOM RESTORED!** 🎉\n"
            f"🔓 **{unlocked_channels} channels** are now free!\n"
            f"💬 Everyone can yap again!\n"
            f"🌟 The vibes have been restored to acceptable levels!\n\n"
            f"📢 **Citizens:** You may resume your regularly scheduled chaos!\n"
            f"🎪 Let the brainrot energy flow once more!\n\n"
            f"**Security status:** Normal chaos levels resumed! 🔥"
        )

    except Exception as e:
        await interaction.followup.send(f"💥 Unlock failed! Error: {str(e)}", ephemeral=True)

@tree.command(name="auto-nick", description="🏷️ Auto-change nicknames for rule breakers")
async def auto_nick_command(interaction: discord.Interaction, user: discord.Member, nickname: str = None):
    """Change someone's nickname automatically"""

    # Check permissions
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("🚫 You need the 'Manage Nicknames' permission bestie! 💀", ephemeral=True)
        return

    if nickname is None:
        nicknames = [
            "Certified Goofball 🤡",
            "Ohio Resident 🌽",
            "NPC Energy 🤖",
            "Sus Impostor 📮",
            "Cringe Lord 😬",
            "Ratio Victim 💀",
            "Grass Toucher 🌱",
            "Skill Issue 📉",
            "L + Bozo 🗿",
            "No Rizz Energy ☠️"
        ]
        nickname = random.choice(nicknames)

    try:
        old_nick = user.display_name
        await user.edit(nick=nickname)
        await interaction.response.send_message(f"🏷️ {user.mention} has been auto-nicked! **{old_nick}** → **{nickname}** 💀")
    except Exception as e:
        await interaction.response.send_message(f"💥 Couldn't change nickname! Error: {str(e)}", ephemeral=True)

@tree.command(name="ghost-mode", description="👻 Hide messages from certain users temporarily")
async def ghost_mode_command(interaction: discord.Interaction, user: discord.Member):
    """Put someone in ghost mode"""

    # Check permissions
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 Only moderators can activate ghost mode! 👻", ephemeral=True)
        return

    await interaction.response.send_message(
        f"👻 {user.mention} has been put in **GHOST MODE**! 🌫️\n\n"
        "They're now invisible to the naked eye... spooky! 💀\n"
        "Only admin spirits can see them now! 🔮\n\n"
        "*Warning: May cause existential crisis* ⚠️"
    )

# 🛡️ ADVANCED MODERATION TOOLS 🛡️

# Storage for moderation configurations
autorole_config = {}  # {guild_id: {'roles': [role_ids], 'channel': channel_id}}
raid_protection_config = {}  # {guild_id: {'enabled': bool, 'threshold': int, 'action': str}}
verification_config = {}  # {guild_id: {'enabled': bool, 'role': role_id, 'channel': channel_id}}
ticket_config = {}  # {guild_id: {'category': category_id, 'staff_role': role_id}}

@tree.command(name='autorole', description='🎭 Configure automatic role assignment for new members')
@app_commands.describe(
    action='What to do (setup/add/remove/list/disable)',
    role='Role to add/remove from autorole list',
    channel='Channel for welcome messages (optional)'
)
async def autorole_slash(interaction: discord.Interaction, action: str, role: discord.Role = None, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("🚫 Lil bro needs manage roles permission! Ask an admin bestie! 👮‍♂️", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'setup':
        if not role:
            await interaction.response.send_message("❌ You need to specify a role to setup autorole! Try again bestie! 🎭", ephemeral=True)
            return
            
        autorole_config[guild_id] = {
            'roles': [role.id],
            'channel': channel.id if channel else None
        }
        
        embed = discord.Embed(
            title="🎭 AUTOROLE ACTIVATED!",
            description=f"YOOO! Autorole system is now BUSSIN! 🔥\n\nNew members will automatically get {role.mention} when they join!\n\n"
                       f"Welcome messages: {channel.mention if channel else 'Disabled'}\n\n"
                       "Your server just got that premium main character energy! ✨",
            color=0x00FF00
        )
        embed.add_field(name="💡 Pro Tips", 
                       value="• Use `/autorole add` to add more roles\n• Use `/autorole list` to see all autoroles\n• Make sure I have permission to assign these roles!", 
                       inline=False)
        embed.set_footer(text="Autorole system powered by sigma grindset technology")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'add':
        if not role:
            await interaction.response.send_message("❌ Which role should I add to autorole? Specify a role bestie! 🎭", ephemeral=True)
            return
            
        if guild_id not in autorole_config:
            autorole_config[guild_id] = {'roles': [], 'channel': None}
            
        if role.id in autorole_config[guild_id]['roles']:
            await interaction.response.send_message(f"💀 {role.mention} is already in the autorole list! No cap! 🧢", ephemeral=True)
            return
            
        autorole_config[guild_id]['roles'].append(role.id)
        
        responses = [
            f"✨ {role.mention} has been added to the autorole gang! New members bout to get blessed! 🙏",
            f"🔥 AUTOROLE ENHANCED! {role.mention} will now be automatically assigned! No cap! 💯",
            f"👑 {role.mention} just got VIP status in the autorole system! Sigma energy activated! ⚡"
        ]
        
        await interaction.response.send_message(random.choice(responses))
        
    elif action.lower() == 'remove':
        if not role:
            await interaction.response.send_message("❌ Which role should I remove from autorole? Specify a role bestie! 🎭", ephemeral=True)
            return
            
        if guild_id not in autorole_config or role.id not in autorole_config[guild_id]['roles']:
            await interaction.response.send_message(f"💀 {role.mention} isn't in the autorole list! Can't remove what ain't there! 🤷‍♂️", ephemeral=True)
            return
            
        autorole_config[guild_id]['roles'].remove(role.id)
        
        responses = [
            f"💨 {role.mention} has been YEETED from autorole! They lost their automatic status! 💀",
            f"🗑️ {role.mention} got removed from autorole! That's some negative aura behavior! 📉",
            f"⚡ {role.mention} has been unsubscribed from the autorole service! Touch grass! 🌱"
        ]
        
        await interaction.response.send_message(random.choice(responses))
        
    elif action.lower() == 'list':
        if guild_id not in autorole_config or not autorole_config[guild_id]['roles']:
            await interaction.response.send_message("📋 No autoroles configured! Your server is giving NPC energy! Use `/autorole setup` to fix this! 🤖", ephemeral=True)
            return
            
        roles_list = []
        for role_id in autorole_config[guild_id]['roles']:
            role_obj = interaction.guild.get_role(role_id)
            if role_obj:
                roles_list.append(role_obj.mention)
                
        if not roles_list:
            await interaction.response.send_message("💀 All autoroles are invalid/deleted! Time for a cleanup bestie! 🧹", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🎭 AUTOROLE CONFIGURATION",
            description=f"Here's your server's autorole setup! Absolutely SENDING! 🚀\n\n**Autoroles ({len(roles_list)}):**\n" + "\n".join(f"• {role}" for role in roles_list),
            color=0x7289DA
        )
        
        channel_id = autorole_config[guild_id].get('channel')
        channel = interaction.guild.get_channel(channel_id) if channel_id else None
        embed.add_field(name="💬 Welcome Channel", 
                       value=channel.mention if channel else "Disabled", 
                       inline=True)
        embed.set_footer(text="Autorole status: BUSSIN | Sigma energy: MAXIMUM")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'disable':
        if guild_id in autorole_config:
            del autorole_config[guild_id]
            await interaction.response.send_message("🚫 Autorole system has been DISABLED! New members will be roleless (sad) 😢", ephemeral=True)
        else:
            await interaction.response.send_message("💀 Autorole wasn't even enabled bestie! Can't disable what ain't there! 🤷‍♂️", ephemeral=True)
            
    else:
        await interaction.response.send_message("❌ Invalid action! Use: setup/add/remove/list/disable\n\nExample: `/autorole setup @Member` 🎭", ephemeral=True)

@tree.command(name='raidprotection', description='🛡️ Configure anti-raid protection system')
@app_commands.describe(
    action='What to do (enable/disable/config/status)',
    threshold='Number of joins to trigger protection (1-50)',
    response='What to do when raid detected (lockdown/kick/ban)'
)
async def raidprotection_slash(interaction: discord.Interaction, action: str, threshold: int = 10, response: str = 'lockdown'):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only sigma administrators can configure raid protection! 👑", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'enable':
        if not 1 <= threshold <= 50:
            await interaction.response.send_message("❌ Threshold must be between 1-50! Pick a reasonable number bestie! 📊", ephemeral=True)
            return
            
        if response.lower() not in ['lockdown', 'kick', 'ban']:
            await interaction.response.send_message("❌ Response must be: lockdown/kick/ban\nLockdown is recommended for most servers! 🛡️", ephemeral=True)
            return
            
        raid_protection_config[guild_id] = {
            'enabled': True,
            'threshold': threshold,
            'action': response.lower(),
            'recent_joins': [],
            'locked_down': False
        }
        
        embed = discord.Embed(
            title="🛡️ RAID PROTECTION ACTIVATED!",
            description=f"YO! Your server is now PROTECTED! 🔥\n\nRaid protection is absolutely SENDING with these settings:\n\n"
                       f"**Trigger Threshold:** {threshold} joins within 30 seconds\n"
                       f"**Response Action:** {response.upper()}\n"
                       f"**Status:** LOCKED AND LOADED! ⚡\n\n"
                       "Try to raid us now! We're ready! 💪",
            color=0xFF0000
        )
        embed.add_field(name="🚨 What happens during a raid?", 
                       value=f"• {threshold}+ joins detected in 30s = RAID ALERT!\n• Automatic {response} activated\n• All moderators get pinged\n• Server goes into defense mode!", 
                       inline=False)
        embed.set_footer(text="Raid protection powered by Ohio-level security technology")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'disable':
        if guild_id in raid_protection_config:
            del raid_protection_config[guild_id]
            await interaction.response.send_message("🚫 Raid protection DISABLED! Your server is now vulnerable! Hope you know what you're doing bestie! 😬", ephemeral=True)
        else:
            await interaction.response.send_message("💀 Raid protection wasn't even enabled! Can't disable what ain't there! 🤷‍♂️", ephemeral=True)
            
    elif action.lower() == 'status':
        if guild_id not in raid_protection_config:
            embed = discord.Embed(
                title="🚫 RAID PROTECTION: DISABLED",
                description="Your server is UNPROTECTED! That's giving vulnerable energy! 😰\n\nUse `/raidprotection enable` to activate protection!",
                color=0xFF0000
            )
        else:
            config = raid_protection_config[guild_id]
            status_color = 0x00FF00 if config['enabled'] else 0xFF0000
            status_text = "ACTIVE 🟢" if config['enabled'] else "INACTIVE 🔴"
            
            embed = discord.Embed(
                title=f"🛡️ RAID PROTECTION: {status_text}",
                description=f"Your server's defense status is absolutely BUSSIN! 💯\n\n"
                           f"**Threshold:** {config['threshold']} joins/30s\n"
                           f"**Response:** {config['action'].upper()}\n"
                           f"**Recent Activity:** {len(config.get('recent_joins', []))} recent joins\n"
                           f"**Lockdown Status:** {'🔒 LOCKED' if config.get('locked_down', False) else '🔓 OPEN'}",
                color=status_color
            )
            
        embed.set_footer(text="Stay vigilant! Raiders hate this one trick!")
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'config':
        # Same as enable but for updating existing config
        if guild_id not in raid_protection_config:
            await interaction.response.send_message("❌ Raid protection not enabled! Use `/raidprotection enable` first! 🛡️", ephemeral=True)
            return
            
        if not 1 <= threshold <= 50:
            await interaction.response.send_message("❌ Threshold must be between 1-50! Pick a reasonable number bestie! 📊", ephemeral=True)
            return
            
        if response.lower() not in ['lockdown', 'kick', 'ban']:
            await interaction.response.send_message("❌ Response must be: lockdown/kick/ban\nLockdown is recommended for most servers! 🛡️", ephemeral=True)
            return
            
        raid_protection_config[guild_id].update({
            'threshold': threshold,
            'action': response.lower()
        })
        
        await interaction.response.send_message(f"⚡ Raid protection config UPDATED! New settings: {threshold} joins → {response.upper()}! Absolutely SENDING! 🚀")
        
    else:
        await interaction.response.send_message("❌ Invalid action! Use: enable/disable/config/status\n\nExample: `/raidprotection enable 15 lockdown` 🛡️", ephemeral=True)

@tree.command(name='verification', description='✅ Configure member verification system')
@app_commands.describe(
    action='What to do (setup/disable/status)',
    role='Role to give verified members',
    channel='Channel for verification messages'
)
async def verification_slash(interaction: discord.Interaction, action: str, role: discord.Role = None, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("🚫 You need manage roles permission! Ask an admin bestie! 👮‍♂️", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'setup':
        if not role:
            await interaction.response.send_message("❌ You need to specify a verified role! Example: `/verification setup @Verified` ✅", ephemeral=True)
            return
            
        verification_config[guild_id] = {
            'enabled': True,
            'role': role.id,
            'channel': channel.id if channel else None
        }
        
        embed = discord.Embed(
            title="✅ VERIFICATION SYSTEM ACTIVATED!",
            description=f"YOOO! Verification is now BUSSIN! 🔥\n\n"
                       f"**Verified Role:** {role.mention}\n"
                       f"**Verification Channel:** {channel.mention if channel else 'DMs'}\n\n"
                       "New members will need to pass the vibe check before getting verified! ✨\n"
                       "Your server just got that premium security energy! 🛡️",
            color=0x00FF00
        )
        embed.add_field(name="🎯 How it works", 
                       value="• New members join without the verified role\n• They can only access verification channel\n• React to verification message to get verified\n• Pass the vibe check = get the role!", 
                       inline=False)
        embed.set_footer(text="Verification powered by sigma grindset security")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'disable':
        if guild_id in verification_config:
            del verification_config[guild_id]
            await interaction.response.send_message("🚫 Verification system DISABLED! Your server is now giving open-door energy! 🚪", ephemeral=True)
        else:
            await interaction.response.send_message("💀 Verification wasn't even enabled! Can't disable what ain't there! 🤷‍♂️", ephemeral=True)
            
    elif action.lower() == 'status':
        if guild_id not in verification_config:
            embed = discord.Embed(
                title="🚫 VERIFICATION: DISABLED",
                description="Your server has no verification! That's giving sus energy! 😰\n\nUse `/verification setup @Role` to activate verification!",
                color=0xFF0000
            )
        else:
            config = verification_config[guild_id]
            role_obj = interaction.guild.get_role(config['role'])
            channel_obj = interaction.guild.get_channel(config['channel']) if config.get('channel') else None
            
            embed = discord.Embed(
                title="✅ VERIFICATION: ACTIVE",
                description=f"Your verification system is absolutely SENDING! 💯\n\n"
                           f"**Verified Role:** {role_obj.mention if role_obj else 'Role Deleted!'}\n"
                           f"**Channel:** {channel_obj.mention if channel_obj else 'DMs'}\n"
                           f"**Status:** PROTECTING THE VIBES! 🛡️",
                color=0x00FF00
            )
            
        embed.set_footer(text="Keep the sus accounts out! No cap!")
        await interaction.response.send_message(embed=embed)
        
    else:
        await interaction.response.send_message("❌ Invalid action! Use: setup/disable/status\n\nExample: `/verification setup @Verified #verify` ✅", ephemeral=True)

@tree.command(name='ticket-system', description='🎫 Configure support ticket system')
@app_commands.describe(
    action='What to do (setup/disable/status)',
    category='Category channel for tickets',
    staff_role='Role that can view/manage tickets'
)
async def ticket_system_slash(interaction: discord.Interaction, action: str, category: discord.CategoryChannel = None, staff_role: discord.Role = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("🚫 You need manage channels permission! Ask an admin bestie! 👮‍♂️", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'setup':
        if not category:
            await interaction.response.send_message("❌ You need to specify a category for tickets! Example: `/ticket-system setup \"Support Tickets\" @Staff` 🎫", ephemeral=True)
            return
            
        ticket_config[guild_id] = {
            'enabled': True,
            'category': category.id,
            'staff_role': staff_role.id if staff_role else None
        }
        
        embed = discord.Embed(
            title="🎫 TICKET SYSTEM ACTIVATED!",
            description=f"YOOO! Ticket system is now ABSOLUTELY BUSSIN! 🔥\n\n"
                       f"**Ticket Category:** {category.name}\n"
                       f"**Staff Role:** {staff_role.mention if staff_role else 'None (All admins)'}\n\n"
                       "Members can now create support tickets! Customer service but make it BUSSIN! ✨\n"
                       "Your server just unlocked premium support energy! 🎭",
            color=0x00FF00
        )
        embed.add_field(name="🎯 How to use", 
                       value="• Use `/ticket create` to make a ticket\n• Private channel gets created automatically\n• Staff can help in the private channel\n• Use `/ticket close` when done!", 
                       inline=False)
        embed.set_footer(text="Ticket system powered by customer service sigma energy")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'disable':
        if guild_id in ticket_config:
            del ticket_config[guild_id]
            await interaction.response.send_message("🚫 Ticket system DISABLED! Customer service is now giving offline energy! 📴", ephemeral=True)
        else:
            await interaction.response.send_message("💀 Ticket system wasn't even enabled! Can't disable what ain't there! 🤷‍♂️", ephemeral=True)
            
    elif action.lower() == 'status':
        if guild_id not in ticket_config:
            embed = discord.Embed(
                title="🚫 TICKETS: DISABLED",
                description="Your server has no ticket system! That's giving no-support energy! 😰\n\nUse `/ticket-system setup` to activate tickets!",
                color=0xFF0000
            )
        else:
            config = ticket_config[guild_id]
            category_obj = interaction.guild.get_channel(config['category'])
            staff_role_obj = interaction.guild.get_role(config['staff_role']) if config.get('staff_role') else None
            
            embed = discord.Embed(
                title="🎫 TICKETS: ACTIVE",
                description=f"Your ticket system is absolutely SENDING! 💯\n\n"
                           f"**Category:** {category_obj.name if category_obj else 'Category Deleted!'}\n"
                           f"**Staff Role:** {staff_role_obj.mention if staff_role_obj else 'All Admins'}\n"
                           f"**Status:** CUSTOMER SERVICE BUSSIN! 🎭",
                color=0x00FF00
            )
            
        embed.set_footer(text="Support tickets = premium user experience!")
        await interaction.response.send_message(embed=embed)
        
    else:
        await interaction.response.send_message("❌ Invalid action! Use: setup/disable/status\n\nExample: `/ticket-system setup \"Support\" @Staff` 🎫", ephemeral=True)

@tree.command(name='ticket', description='🎫 Create or manage support tickets')
@app_commands.describe(
    action='What to do (create/close/add/remove)',
    reason='Reason for creating ticket',
    user='User to add/remove from ticket'
)
async def ticket_slash(interaction: discord.Interaction, action: str, reason: str = "Need help", user: discord.Member = None):
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'create':
        if guild_id not in ticket_config:
            await interaction.response.send_message("❌ Ticket system not enabled! Ask an admin to set it up with `/ticket-system setup`! 🎫", ephemeral=True)
            return
            
        config = ticket_config[guild_id]
        category = interaction.guild.get_channel(config['category'])
        
        if not category:
            await interaction.response.send_message("❌ Ticket category was deleted! Ask an admin to reconfigure the system! 🗑️", ephemeral=True)
            return
            
        # Create ticket channel
        ticket_name = f"ticket-{interaction.user.name}-{int(time.time())}"
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add staff role if configured
        if config.get('staff_role'):
            staff_role = interaction.guild.get_role(config['staff_role'])
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_channel = await category.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                reason=f"Support ticket created by {interaction.user}"
            )
            
            embed = discord.Embed(
                title="🎫 TICKET CREATED!",
                description=f"YO! Your support ticket is absolutely BUSSIN! 🔥\n\n"
                           f"**Ticket Channel:** {ticket_channel.mention}\n"
                           f"**Reason:** {reason}\n"
                           f"**Created By:** {interaction.user.mention}\n\n"
                           "Head over to your private channel! Staff will help you ASAP! ✨",
                color=0x00FF00
            )
            embed.set_footer(text="Customer service but make it sigma energy!")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Send welcome message in ticket
            welcome_embed = discord.Embed(
                title="🎭 Welcome to Your Support Ticket!",
                description=f"Hey {interaction.user.mention}! Welcome to customer service but make it BUSSIN! 💯\n\n"
                           f"**Ticket Reason:** {reason}\n\n"
                           "A staff member will be with you shortly! In the meantime:\n"
                           "• Explain your issue in detail\n"
                           "• Provide screenshots if needed\n"
                           "• Be patient - good help takes time!\n\n"
                           "Use `/ticket close` when your issue is resolved! 🎫",
                color=0x7289DA
            )
            welcome_embed.set_footer(text="We're here to help! No cap!")
            
            await ticket_channel.send(embed=welcome_embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create channels! Check my permissions bestie! 🚫", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create ticket! Error: {str(e)} 💀", ephemeral=True)
            
    elif action.lower() == 'close':
        # Check if this is a ticket channel
        if not interaction.channel.name.startswith('ticket-'):
            await interaction.response.send_message("❌ This isn't a ticket channel! Use this command in a ticket bestie! 🎫", ephemeral=True)
            return
            
        if not (interaction.user.guild_permissions.manage_channels or 
                interaction.channel.permissions_for(interaction.user).manage_channels):
            await interaction.response.send_message("🚫 Only staff or the ticket owner can close tickets! 👮‍♂️", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🎫 TICKET CLOSING!",
            description=f"Ticket closed by {interaction.user.mention}! 🔒\n\nThis channel will be deleted in 10 seconds...\n\nThanks for using our absolutely BUSSIN customer service! ✨",
            color=0xFF0000
        )
        embed.set_footer(text="Hope we could help! Come back anytime!")
        
        await interaction.response.send_message(embed=embed)
        
        # Delete channel after delay
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            pass  # Channel might already be deleted
            
    else:
        await interaction.response.send_message("❌ Invalid action! Use: create/close\n\nExample: `/ticket create I need help with roles` 🎫", ephemeral=True)

@tree.command(name="reverse-day", description="🔄 Flip all rules for 24 hours (chaos mode)")
async def reverse_day_command(interaction: discord.Interaction):
    """Activate reverse day chaos mode"""

    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can flip reality! That's too much power bestie! 💀", ephemeral=True)
        return

    await interaction.response.send_message(
        "🔄 **REVERSE DAY ACTIVATED!** 🌪️\n\n"
        "📜 All rules are now flipped for 24 hours!\n"
        "🎪 Chaos is mandatory!\n"
        "🤡 Seriousness is forbidden!\n"
        "💀 Sus behavior is encouraged!\n"
        "🌽 Ohio energy is required!\n"
        "📮 Everyone is now sus!\n\n"
        "⚠️ **WARNING:** Reality may become unstable!\n"
        "🌀 Side effects include: uncontrollable rizz, sigma grindset mentality, and spontaneous Ohio citizenship!\n\n"
        "*May god have mercy on us all* 🙏"
    )

# 🎭 ROLE MANAGEMENT COMMANDS 🎭

@tree.command(name='roleadd', description='🎭 Give a role to someone with maximum sigma energy')
@app_commands.describe(
    role='The role to give',
    user='The user to receive the role',
    reason='Why they deserve this role (optional)'
)
async def roleadd_slash(interaction: discord.Interaction, role: discord.Role, user: discord.Member, reason: str = "Main character energy detected"):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("🚫 Lil bro needs manage roles permission! Ask an admin bestie! 👮‍♂️", ephemeral=True)
        return
    
    if role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("💀 You can't give roles higher than your own! That's not how the hierarchy works bestie! 📊", ephemeral=True)
        return
    
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("🤖 I can't assign that role! It's higher than mine in the pecking order! Promote me first bestie! 📈", ephemeral=True)
        return

    if role in user.roles:
        await interaction.response.send_message(f"💀 {user.mention} already has {role.mention}! They're already that iconic bestie! ✨", ephemeral=True)
        return

    try:
        await user.add_roles(role, reason=f"Role added by {interaction.user}: {reason}")
        
        goofy_responses = [
            f"YOOO! {user.mention} just got blessed with {role.mention}! 🎉",
            f"✨ ROLE UPGRADE! {user.mention} is now serving {role.mention} energy! 💅",
            f"🔥 BESTIE JUST GOT PROMOTED! {user.mention} → {role.mention}! That's giving main character vibes! 👑",
            f"🎭 ROLE ASSIGNMENT SUCCESSFUL! {user.mention} is now {role.mention}! Welcome to the club bestie! 🎪",
            f"⚡ SIGMA GRINDSET ACTIVATED! {user.mention} earned {role.mention}! No cap! 🧢",
            f"💀 {user.mention} really said 'give me {role.mention}' and honestly? We respect the audacity! 🗿",
            f"🌟 GLOW UP ALERT! {user.mention} just became {role.mention}! That aura is IMMACULATE! ✨",
            f"🎪 THE CIRCUS IS EXPANDING! Welcome {role.mention} {user.mention}! Hope you brought snacks! 🍿"
        ]
        
        embed = discord.Embed(
            title="🎭 ROLE ASSIGNMENT COMPLETE!",
            description=f"{random.choice(goofy_responses)}\n\n**User:** {user.mention}\n**Role:** {role.mention}\n**Reason:** {reason}\n**Assigned by:** {interaction.user.mention}",
            color=role.color if role.color != discord.Color.default() else 0x00FF00
        )
        embed.add_field(
            name="💡 Pro Tip", 
            value="With great power comes great responsibility... or something like that! 🕷️", 
            inline=False
        )
        embed.set_footer(text="Role assignment powered by sigma grindset technology")
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("🚫 I don't have permission to give that role! My powers are limited bestie! 😅", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"💥 Role assignment machine broke! Error: {str(e)} 🤪", ephemeral=True)

@tree.command(name='massaddrole', description='🎪 Give everyone in the server a role - ABSOLUTE CHAOS MODE')
@app_commands.describe(
    role='The role to give to EVERYONE (use with caution)',
    exclude_bots='Exclude bots from mass role assignment (recommended)',
    reason='Why everyone deserves this role'
)
async def massaddrole_slash(interaction: discord.Interaction, role: discord.Role, exclude_bots: bool = True, reason: str = "Mass sigma grindset activation"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can cause this level of chaos! That's too much power for mortals! 💀", ephemeral=True)
        return
    
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("🤖 I can't assign that role! It's higher than mine! Promote me to Supreme Overlord first! 👑", ephemeral=True)
        return

    # Safety check - confirm the chaos they're about to unleash
    member_count = len([m for m in interaction.guild.members if not (m.bot and exclude_bots) and role not in m.roles])
    
    if member_count == 0:
        await interaction.response.send_message(f"💀 Everyone already has {role.mention}! The chaos has already been unleashed bestie! 🎪", ephemeral=True)
        return
    
    # Send confirmation message
    chaos_warnings = [
        f"⚠️ **CHAOS WARNING!** ⚠️\n\nYou're about to give {role.mention} to **{member_count}** members!\n\nThis will cause MAXIMUM CHAOS and cannot be undone easily!",
        f"🌪️ **ABSOLUTE MADNESS INCOMING!** 🌪️\n\n{member_count} people are about to receive {role.mention}!\n\nYour server will never be the same bestie!",
        f"💀 **POINT OF NO RETURN!** 💀\n\nYou're giving {role.mention} to {member_count} members!\n\nThis is your last chance to reconsider the chaos!"
    ]
    
    embed = discord.Embed(
        title="🎪 MASS ROLE ASSIGNMENT INITIATED!",
        description=f"{random.choice(chaos_warnings)}\n\n**Role:** {role.mention}\n**Target Count:** {member_count} members\n**Exclude Bots:** {'Yes' if exclude_bots else 'No'}\n**Reason:** {reason}",
        color=0xFF4500
    )
    embed.add_field(
        name="⚡ CHAOS METER", 
        value="██████████ 100% 🔥", 
        inline=False
    )
    embed.set_footer(text="Mass role assignment - May god have mercy on your server")
    
    await interaction.response.send_message(embed=embed)
    
    # Start the mass assignment
    try:
        success_count = 0
        failed_count = 0
        
        # Send a follow-up message to show progress
        await interaction.followup.send("🚀 **MASS ASSIGNMENT IN PROGRESS...** This might take a while bestie! ⏰")
        
        for member in interaction.guild.members:
            if exclude_bots and member.bot:
                continue
            if role in member.roles:
                continue  # Skip if already has role
                
            try:
                await member.add_roles(role, reason=f"Mass assignment by {interaction.user}: {reason}")
                success_count += 1
                
                # Add a small delay to avoid rate limiting
                if success_count % 5 == 0:
                    await asyncio.sleep(1)  # Rate limiting protection
                    
            except discord.Forbidden:
                failed_count += 1
            except Exception:
                failed_count += 1
        
        # Final report
        chaos_results = [
            f"🎉 **CHAOS COMPLETE!** Successfully gave {role.mention} to **{success_count}** members! The server has ascended to peak brainrot! 🧠",
            f"✨ **MASS ASSIGNMENT FINISHED!** {success_count} people now have {role.mention}! Your server's aura just broke the meter! 📊",
            f"🔥 **SIGMA GRINDSET ACTIVATED!** {role.mention} has been distributed to {success_count} members! The collective energy is IMMACULATE! ⚡"
        ]
        
        result_embed = discord.Embed(
            title="🎪 MASS ROLE ASSIGNMENT COMPLETE!",
            description=f"{random.choice(chaos_results)}\n\n**Role:** {role.mention}\n**Successful:** {success_count}\n**Failed:** {failed_count}\n**Total Affected:** {success_count} members",
            color=0x00FF00
        )
        
        if failed_count > 0:
            result_embed.add_field(
                name="⚠️ Some Failed", 
                value=f"{failed_count} members couldn't receive the role (permissions/hierarchy issues)", 
                inline=False
            )
        
        result_embed.add_field(
            name="🎭 Chaos Level", 
            value="MAXIMUM ACHIEVED! 🌪️", 
            inline=False
        )
        result_embed.set_footer(text="Mass chaos deployment successful - Server will never be the same")
        
        await interaction.followup.send(embed=result_embed)
        
    except Exception as e:
        await interaction.followup.send(f"💥 CHAOS MACHINE EXPLODED! Error during mass assignment: {str(e)} 🤪")

@tree.command(name='massdm', description='📬 Send a message to multiple users - Power move energy')
@app_commands.describe(
    role='Role to send message to (all members with this role)',
    message='The message to send to everyone',
    exclude_bots='Exclude bots from mass DM (recommended)'
)
async def massdm_slash(interaction: discord.Interaction, role: discord.Role, message: str, exclude_bots: bool = True):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can spam everyone's DMs! That's too much power bestie! 💀", ephemeral=True)
        return
    
    # Get members with the role
    target_members = [member for member in interaction.guild.members 
                     if role in member.roles and not (member.bot and exclude_bots)]
    
    if not target_members:
        await interaction.response.send_message(f"💀 No one with {role.mention} to message! The role is emptier than Ohio! 🌽", ephemeral=True)
        return
    
    # Confirmation message
    embed = discord.Embed(
        title="📬 MASS DM SYSTEM ACTIVATED!",
        description=f"🎯 **Target Role:** {role.mention}\n"
                   f"👥 **Recipients:** {len(target_members)} members\n"
                   f"🤖 **Exclude Bots:** {'Yes' if exclude_bots else 'No'}\n\n"
                   f"📝 **Message Preview:**\n```{message}```\n\n"
                   f"⚠️ **Warning:** This will DM {len(target_members)} people! Some might find it annoying bestie!",
        color=0xFF6B35
    )
    embed.add_field(
        name="🚀 Chaos Meter", 
        value="█████████░ 90% 🔥", 
        inline=False
    )
    embed.set_footer(text="Mass DM deployment - Use responsibly!")
    
    await interaction.response.send_message(embed=embed)
    
    # Start mass DM process
    try:
        success_count = 0
        failed_count = 0
        
        await interaction.followup.send("🚀 **MASS DM IN PROGRESS...** Sliding into DMs like a sigma! ⏰")
        
        for member in target_members:
            try:
                # Create personalized embed for each user
                dm_embed = discord.Embed(
                    title=f"📨 Message from {interaction.guild.name}",
                    description=message,
                    color=0x7289DA
                )
                dm_embed.add_field(
                    name="📍 Server",
                    value=interaction.guild.name,
                    inline=True
                )
                dm_embed.add_field(
                    name="👤 Sent by",
                    value=interaction.user.display_name,
                    inline=True
                )
                dm_embed.add_field(
                    name="🎭 Your Role",
                    value=role.name,
                    inline=True
                )
                dm_embed.set_footer(text="This message was sent using GoofGuard's Mass DM system")
                
                # Try to send DM
                await member.send(embed=dm_embed)
                success_count += 1
                
                # Rate limiting to avoid Discord limits
                if success_count % 5 == 0:
                    await asyncio.sleep(2)  # 2 second delay every 5 DMs
                    
            except discord.Forbidden:
                failed_count += 1  # User has DMs disabled
            except discord.HTTPException:
                failed_count += 1  # Other Discord API errors
            except Exception:
                failed_count += 1  # Any other errors
        
        # Final report
        success_responses = [
            f"🎉 **MASS DM COMPLETE!** Successfully slid into **{success_count}** DMs! Your message spread like wildfire! 🔥",
            f"📬 **MISSION ACCOMPLISHED!** {success_count} people got your message! That's some premium communication energy! ✨",
            f"🚀 **DM DEPLOYMENT SUCCESSFUL!** Message delivered to {success_count} users! You just became the main character of their notifications! 👑"
        ]
        
        result_embed = discord.Embed(
            title="📬 MASS DM MISSION COMPLETE!",
            description=f"{random.choice(success_responses)}\n\n"
                       f"**Role:** {role.mention}\n"
                       f"**Successful:** {success_count} DMs sent ✅\n"
                       f"**Failed:** {failed_count} DMs failed ❌\n"
                       f"**Total Attempted:** {len(target_members)} members",
            color=0x00FF00
        )
        
        if failed_count > 0:
            result_embed.add_field(
                name="⚠️ Some Failed", 
                value=f"{failed_count} members couldn't receive DMs (probably have them disabled or blocked the bot)", 
                inline=False
            )
        
        result_embed.add_field(
            name="📊 Success Rate", 
            value=f"{(success_count/len(target_members)*100):.1f}% delivery rate! 📈", 
            inline=False
        )
        result_embed.set_footer(text="Mass DM system - Spreading chaos one notification at a time")
        
        await interaction.followup.send(embed=result_embed)
        
    except Exception as e:
        await interaction.followup.send(f"💥 DM MACHINE BROKE! Error during mass DM: {str(e)} 📬💀")

# 🛡️ VERIFICATION & SECURITY SYSTEMS 🛡️

# Storage for verification configs
verification_config = {}  # {guild_id: {'enabled': bool, 'role': role_id, 'channel': channel_id}}
pending_verifications = {}  # {user_id: {'guild_id': guild_id, 'captcha_code': str, 'attempts': int}}

@tree.command(name='verify-setup', description='🛡️ Setup verification system for server security')
@app_commands.describe(
    action='What to do (setup/disable)',
    verified_role='Role to give after verification',
    verify_channel='Channel where verification happens'
)
async def verify_setup_slash(interaction: discord.Interaction, action: str, verified_role: discord.Role = None, verify_channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can setup verification! That's maximum security clearance bestie! 💀", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    if action.lower() == 'setup':
        if not verified_role:
            await interaction.response.send_message("❌ You need to specify a verified role! Can't verify people into nothing bestie! 🎭", ephemeral=True)
            return
        
        if not verify_channel:
            await interaction.response.send_message("❌ You need a verification channel! Where else will the chaos happen? 📺", ephemeral=True)
            return
        
        verification_config[guild_id] = {
            'enabled': True,
            'role': verified_role.id,
            'channel': verify_channel.id
        }
        
        embed = discord.Embed(
            title="🛡️ VERIFICATION SYSTEM ACTIVATED!",
            description=f"🔒 **MAXIMUM SECURITY MODE ENGAGED!** 🔒\n\n"
                       f"✅ **Verified Role:** {verified_role.mention}\n"
                       f"📺 **Verification Channel:** {verify_channel.mention}\n\n"
                       f"🎯 **How it works:**\n"
                       f"• New members get stuck in verification limbo\n"
                       f"• They must complete captcha challenges\n"
                       f"• Only sigma energy humans get through\n"
                       f"• Bots and sus users get REJECTED!\n\n"
                       f"Your server is now **FORTRESS LEVEL SECURE!** 🏰",
            color=0x00FF00
        )
        embed.add_field(
            name="💡 Pro Tips", 
            value="• Make sure the verified role can see your server!\n• Set up role hierarchy properly!\n• Use `/captcha @user` for manual challenges!", 
            inline=False
        )
        embed.set_footer(text="Verification powered by Ohio-grade security technology")
        
        await interaction.response.send_message(embed=embed)
        
    elif action.lower() == 'disable':
        if guild_id in verification_config:
            del verification_config[guild_id]
            
        embed = discord.Embed(
            title="🔓 Verification System Disabled",
            description="Verification system has been turned off. Your server is back to trusting everyone... good luck bestie! 💀",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)
    
    else:
        await interaction.response.send_message("❌ Invalid action! Use 'setup' or 'disable' bestie! 🤪", ephemeral=True)

@tree.command(name='captcha', description='🤖 Send captcha challenge to verify users')
@app_commands.describe(
    user='User to challenge with captcha',
    difficulty='Captcha difficulty (easy/medium/hard)'
)
async def captcha_slash(interaction: discord.Interaction, user: discord.Member, difficulty: str = "medium"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 You don't have the power to captcha people! Ask a mod bestie! 👮‍♂️", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("💀 That's literally a bot bestie! They don't need captcha, they ARE the captcha! 🤖", ephemeral=True)
        return
    
    # Generate captcha based on difficulty
    if difficulty.lower() == "easy":
        captcha_code = str(random.randint(100, 999))
        complexity_desc = "3-digit number"
    elif difficulty.lower() == "hard":
        captcha_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        complexity_desc = "6-character alphanumeric code"
    else:  # medium
        captcha_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
        complexity_desc = "4-character alphanumeric code"
    
    # Store pending verification
    pending_verifications[user.id] = {
        'guild_id': interaction.guild.id,
        'captcha_code': captcha_code,
        'attempts': 0,
        'issued_by': interaction.user.id
    }
    
    # Create captcha embed for the user
    captcha_embed = discord.Embed(
        title="🤖 CAPTCHA CHALLENGE ACTIVATED!",
        description=f"🔒 **SECURITY CHECKPOINT DETECTED!** 🔒\n\n"
                   f"🎯 **Your Mission:** Prove you're human (not an Ohio resident)\n"
                   f"🧠 **Difficulty:** {difficulty.title()} ({complexity_desc})\n"
                   f"🔢 **Your Code:** `{captcha_code}`\n\n"
                   f"📝 **Instructions:**\n"
                   f"Type the code exactly as shown above to verify you're not a bot!\n"
                   f"You have 3 attempts before the system assumes you're sus! 👀\n\n"
                   f"⚠️ **Warning:** Failure results in being labeled as 'Probably a Bot' 🤖",
        color=0xFFA500
    )
    captcha_embed.add_field(
        name="💡 Pro Tip", 
        value="Copy-paste won't work here bestie! Type it manually to prove human status! 🧠", 
        inline=False
    )
    captcha_embed.set_footer(text="Captcha system powered by anti-bot sigma technology")
    
    try:
        await user.send(embed=captcha_embed)
        
        # Confirmation for moderator
        mod_embed = discord.Embed(
            title="🤖 CAPTCHA DEPLOYED!",
            description=f"Captcha challenge sent to {user.mention}!\n\n"
                       f"**Difficulty:** {difficulty.title()}\n"
                       f"**Code:** `{captcha_code}` (for your reference)\n"
                       f"**Status:** Awaiting human verification... 🕒",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=mod_embed)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"💀 Can't DM {user.mention}! Their DMs are more closed than Ohio borders! Try a different method! 📬❌", ephemeral=True)

@tree.command(name='verify', description='✅ Verify yourself with captcha code')
@app_commands.describe(code='The captcha code you received')
async def verify_slash(interaction: discord.Interaction, code: str):
    user_id = interaction.user.id
    
    if user_id not in pending_verifications:
        await interaction.response.send_message("❌ No pending verification found! You might already be verified or no captcha was issued! 🤔", ephemeral=True)
        return
    
    verification_data = pending_verifications[user_id]
    correct_code = verification_data['captcha_code']
    attempts = verification_data['attempts']
    
    if code.upper() == correct_code.upper():
        # SUCCESS! Verification complete
        guild_id = str(verification_data['guild_id'])
        guild = interaction.guild
        
        # Give verified role if verification system is enabled
        if guild_id in verification_config:
            verified_role_id = verification_config[guild_id]['role']
            verified_role = guild.get_role(verified_role_id)
            
            if verified_role:
                try:
                    await interaction.user.add_roles(verified_role, reason="✅ Captcha verification successful!")
                except discord.Forbidden:
                    await interaction.response.send_message("✅ Verification successful but I couldn't give you the role! Ask an admin to fix my permissions! 😅", ephemeral=True)
                    return
        
        # Remove from pending
        del pending_verifications[user_id]
        
        success_responses = [
            "🎉 **HUMAN VERIFICATION COMPLETE!** Welcome to the elite human club bestie! 🧠",
            "✅ **CAPTCHA CRUSHED!** Your human status has been officially certified! 👑",
            "🔥 **VERIFICATION SUCCESSFUL!** You've proven you're not an Ohio bot! Congrats! 🌽",
            "⚡ **HUMAN CONFIRMED!** Your sigma energy levels are off the charts! Welcome! 💪",
            "🎭 **ACCESS GRANTED!** You've passed the vibe check and the bot check! Double win! 🏆"
        ]
        
        embed = discord.Embed(
            title="✅ VERIFICATION SUCCESSFUL!",
            description=random.choice(success_responses),
            color=0x00FF00
        )
        embed.add_field(
            name="🎯 Status Update", 
            value="You now have full access to the server! Time to cause some chaos! 😈", 
            inline=False
        )
        embed.set_footer(text="Welcome to the verified human club - Population: You + Everyone Else Who Passed")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    else:
        # WRONG CODE
        verification_data['attempts'] += 1
        attempts = verification_data['attempts']
        
        if attempts >= 3:
            # Failed too many times
            del pending_verifications[user_id]
            
            fail_embed = discord.Embed(
                title="❌ VERIFICATION FAILED!",
                description="🤖 **SUSPICIOUS ACTIVITY DETECTED!** 🤖\n\n"
                           f"You've failed captcha verification {attempts} times!\n"
                           f"Your human status is now **HIGHLY QUESTIONABLE** 👀\n\n"
                           f"**Possible Explanations:**\n"
                           f"• You're actually a bot 🤖\n"
                           f"• You're from Ohio (understandable) 🌽\n"
                           f"• Your brain is in brainrot mode 🧠\n\n"
                           f"**Next Steps:** Ask a moderator to verify you manually, or try again later!",
                color=0xFF0000
            )
            fail_embed.set_footer(text="Bot detection system - Protecting servers from sus behavior since 2024")
            
            await interaction.response.send_message(embed=fail_embed, ephemeral=True)
        else:
            # Wrong but can try again
            remaining = 3 - attempts
            
            retry_embed = discord.Embed(
                title="❌ Wrong Code!",
                description=f"That's not the right code bestie! 💀\n\n"
                           f"**Attempts:** {attempts}/3\n"
                           f"**Remaining:** {remaining} attempts\n\n"
                           f"Double-check the code and try again! Make sure you're typing it exactly as shown! 🔍",
                color=0xFFA500
            )
            await interaction.response.send_message(embed=retry_embed, ephemeral=True)

@tree.command(name='verification-status', description='📋 Check verification system status and pending users')
async def verification_status_slash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 You don't have permission to check verification status! Ask a mod bestie! 👮‍♂️", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    embed = discord.Embed(
        title="📋 Verification System Status",
        description="Current verification configuration and pending users",
        color=0x7289DA
    )
    
    # System status
    if guild_id in verification_config:
        config = verification_config[guild_id]
        verified_role = interaction.guild.get_role(config['role'])
        verify_channel = interaction.guild.get_channel(config['channel'])
        
        embed.add_field(
            name="🛡️ System Status",
            value=f"✅ **ACTIVE**\n"
                  f"**Verified Role:** {verified_role.mention if verified_role else 'Role not found!'}\n"
                  f"**Verify Channel:** {verify_channel.mention if verify_channel else 'Channel not found!'}",
            inline=False
        )
    else:
        embed.add_field(
            name="🛡️ System Status",
            value="❌ **DISABLED**\nUse `/verify-setup setup` to enable verification!",
            inline=False
        )
    
    # Pending verifications
    guild_pending = [user_id for user_id, data in pending_verifications.items() if data['guild_id'] == interaction.guild.id]
    
    if guild_pending:
        pending_users = []
        for user_id in guild_pending[:10]:  # Limit to 10 to avoid embed limits
            user = interaction.guild.get_member(user_id)
            if user:
                data = pending_verifications[user_id]
                pending_users.append(f"• {user.mention} ({data['attempts']}/3 attempts)")
        
        embed.add_field(
            name=f"⏳ Pending Verifications ({len(guild_pending)})",
            value="\n".join(pending_users) if pending_users else "No pending verifications found",
            inline=False
        )
    else:
        embed.add_field(
            name="⏳ Pending Verifications",
            value="No users currently awaiting verification! ✨",
            inline=False
        )
    
    embed.set_footer(text="Use /captcha @user to manually challenge suspicious users")
    await interaction.response.send_message(embed=embed)

# 📚 TUTORIAL SYSTEM 📚

@tree.command(name='tutorial', description='📚 Get detailed setup tutorials for moderation features')
@app_commands.describe(command='Which moderation feature you want to learn about')
@app_commands.choices(command=[
    app_commands.Choice(name='Verification System', value='verify'),
    app_commands.Choice(name='Auto-Moderation', value='automod'),
    app_commands.Choice(name='Autorole System', value='autorole'),
    app_commands.Choice(name='Welcome System', value='welcome'),
    app_commands.Choice(name='Warning System', value='warnings'),
    app_commands.Choice(name='Leveling System', value='leveling'),
    app_commands.Choice(name='Role Management', value='roles'),
    app_commands.Choice(name='Mass Commands', value='mass'),
    app_commands.Choice(name='Lockdown System', value='lockdown'),
    app_commands.Choice(name='Ghost Mode', value='ghost')
])
async def tutorial_slash(interaction: discord.Interaction, command: str):
    
    tutorials = {
        'verify': {
            'title': '🛡️ Verification System Tutorial',
            'description': 'Complete guide to setting up server verification with captcha challenges!',
            'color': 0x00FF00,
            'steps': [
                "**Step 1: Create Roles**\n• Create a `@Verified` role with full server permissions\n• Create a `@Unverified` role with no permissions (optional)",
                "**Step 2: Setup Verification**\n• Use `/verify-setup setup @Verified #verification-channel`\n• Make sure the bot can manage the verified role!",
                "**Step 3: Test the System**\n• Use `/captcha @user medium` to test manual challenges\n• Users complete verification with `/verify [code]`",
                "**Step 4: Monitor Activity**\n• Use `/verification-status` to check pending verifications\n• Failed attempts are tracked automatically"
            ],
            'tips': '💡 **Pro Tips:**\n• Set channel permissions so unverified users can only see verification channel\n• Use difficulty levels: easy (numbers), medium (mixed), hard (complex)\n• The system automatically assigns roles on successful verification!'
        },
        'automod': {
            'title': '🤖 Auto-Moderation Tutorial',
            'description': 'Setup automatic content protection and moderation actions!',
            'color': 0xFF6B35,
            'steps': [
                "**Step 1: Basic Protection**\n• `/automod spam true warn` - Warn for spam messages\n• `/automod caps true mute` - Mute for excessive caps\n• `/automod mentions true kick` - Kick for mass mentions",
                "**Step 2: Content Protection**\n• `/automod links true warn` - Filter suspicious links\n• `/automod invites true kick` - Block Discord invites\n• `/automod nsfw true ban` - Remove NSFW content",
                "**Step 3: Advanced Features**\n• `/automod duplicates true warn` - Stop copy-paste spam\n• `/automod emojis true warn` - Control external emojis\n• `/automod files true kick` - Block dangerous files",
                "**Step 4: Configure Actions**\n• Actions: warn, mute (10min), kick, ban\n• Use `/automodstatus` to check all settings\n• Warning escalation tracks repeat offenders"
            ],
            'tips': '💡 **Pro Tips:**\n• Start with warnings before using harsh actions\n• Combine features for maximum protection\n• Use `/automod warnings true kick 3` for escalation after 3 warnings!'
        },
        'autorole': {
            'title': '🎭 Autorole System Tutorial', 
            'description': 'Automatically assign roles to new members who join your server!',
            'color': 0x7289DA,
            'steps': [
                "**Step 1: Create Roles**\n• Create roles like `@Member`, `@Newcomer`, etc.\n• Make sure bot role is above the roles you want to assign",
                "**Step 2: Setup Autorole**\n• `/autorole setup @Member` - Basic setup\n• `/autorole setup @Member #welcome` - With welcome channel",
                "**Step 3: Add More Roles**\n• `/autorole add @Newcomer` - Add additional roles\n• `/autorole list` - View all autoroles",
                "**Step 4: Manage System**\n• `/autorole remove @OldRole` - Remove roles\n• `/autorole disable` - Turn off system completely"
            ],
            'tips': '💡 **Pro Tips:**\n• Test with alt accounts or friends first\n• Don\'t assign admin roles automatically!\n• Autoroles work with the welcome system for maximum impact!'
        },
        'welcome': {
            'title': '🎪 Welcome System Tutorial',
            'description': 'Create epic welcome messages for new server members!',
            'color': 0xFF69B4,
            'steps': [
                "**Step 1: Set Welcome Channel**\n• `/configwelcomechannel #welcome` - Choose your channel\n• Make sure bot can send messages there",
                "**Step 2: Customize Message**\n• `/configwelcomemessage Welcome {user} to our chaos!`\n• Use {user}, {username}, {server} as variables",
                "**Step 3: Enable System**\n• `/togglewelcome` - Turn welcomes on/off\n• `/welcomestatus` - Check current settings",
                "**Step 4: Test and Reset**\n• Test by having someone join\n• `/resetwelcome` - Reset to defaults if needed"
            ],
            'tips': '💡 **Pro Tips:**\n• Combine with autorole for complete new member experience\n• Custom messages can include server rules or links\n• Welcome embeds are automatically styled with random colors!'
        },
        'warnings': {
            'title': '⚠️ Warning System Tutorial',
            'description': 'Track user behavior with warnings and automatic escalation!',
            'color': 0xFFA500,
            'steps': [
                "**Step 1: Issue Warnings**\n• `/warn @user [reason]` - Give a warning\n• Warnings are automatically tracked per user",
                "**Step 2: Setup Escalation**\n• `/automod warnings true mute 3` - Auto-mute after 3 warnings\n• `/automod warnings true kick 5` - Auto-kick after 5 warnings",
                "**Step 3: Manage Warnings**\n• `/warnings @user` - View user's warning history\n• `/unwarn @user 2` - Remove 2 warnings\n• `/clearwarnings @user` - Clear all warnings",
                "**Step 4: Monitor System**\n• Escalation happens automatically\n• Users get notified of warning counts\n• Perfect for tracking problematic users"
            ],
            'tips': '💡 **Pro Tips:**\n• Set reasonable escalation thresholds\n• Use warnings before kicks/bans for fairness\n• Warning history helps track patterns over time!'
        },
        'leveling': {
            'title': '📈 Leveling System Tutorial',
            'description': 'Gamify your server with XP and levels for active members!',
            'color': 0x00BFFF,
            'steps': [
                "**Step 1: Enable System**\n• `/configlevel enable` - Turn on leveling\n• Members gain XP by chatting (1 minute cooldown)",
                "**Step 2: Check Progress**\n• `/level` - Check your own level and XP\n• `/level @user` - Check someone else's progress\n• `/leaderboard` - See top server members",
                "**Step 3: Understand Mechanics**\n• XP gain: Random 15-25 XP per message\n• Level formula: Level = √(XP/100) + 1\n• Titles change based on level achievements"
            ],
            'tips': '💡 **Pro Tips:**\n• Levels create healthy competition\n• XP farming is prevented with cooldowns\n• Higher levels get increasingly harder to achieve!'
        },
        'roles': {
            'title': '🎭 Role Management Tutorial',
            'description': 'Master role assignment and mass role operations!',
            'color': 0x9B59B6,
            'steps': [
                "**Step 1: Individual Roles**\n• `/roleadd @role @user [reason]` - Give role to one person\n• Check role hierarchy - you can't assign roles above your own",
                "**Step 2: Mass Role Operations**\n• `/massaddrole @role` - Give role to EVERYONE\n• Use `exclude_bots: true` to skip bot accounts\n• This is CHAOS MODE - use carefully!",
                "**Step 3: Safety Checks**\n• Bot checks role hierarchy automatically\n• Confirmation messages prevent accidents\n• Progress tracking shows success/failure rates"
            ],
            'tips': '💡 **Pro Tips:**\n• Test individual roleadd first\n• Mass operations can take time with large servers\n• Always double-check which role you\'re mass-assigning!'
        },
        'mass': {
            'title': '📢 Mass Commands Tutorial',
            'description': 'Communicate with multiple users efficiently!',
            'color': 0xE74C3C,
            'steps': [
                "**Step 1: Mass DM Setup**\n• `/massdm @role \"Your message here\"` - DM everyone with a role\n• Choose exclude_bots setting carefully",
                "**Step 2: Understand Limits**\n• Rate limiting prevents Discord API issues\n• Some users may have DMs disabled\n• Success rate shows delivery statistics",
                "**Step 3: Use Responsibly**\n• Only for important announcements\n• Don't spam - users can leave servers for this\n• Include clear sender information"
            ],
            'tips': '💡 **Pro Tips:**\n• Test with a small role first\n• Keep messages brief and clear\n• Mass DMs should be rare - use channels for regular updates!'
        },
        'lockdown': {
            'title': '🚨 Lockdown System Tutorial',
            'description': 'Emergency server protection during raids or incidents!',
            'color': 0xFF0000,
            'steps': [
                "**Step 1: Emergency Lockdown**\n• `/lockdown` - Instantly restrict all channels\n• Only staff can send messages during lockdown\n• Prevents raid damage and spam floods",
                "**Step 2: Monitor Situation**\n• Deal with the threat (ban raiders, etc.)\n• Lockdown stays active until manually lifted\n• Staff can still moderate during lockdown",
                "**Step 3: Restore Access**\n• `/unlock` - Restore normal server permissions\n• Double-check that threats are resolved\n• Announce all-clear to members if needed"
            ],
            'tips': '💡 **Pro Tips:**\n• Use lockdown immediately during raids\n• Staff roles need proper permissions to work during lockdown\n• Better to over-protect than under-protect your server!'
        },
        'ghost': {
            'title': '👻 Ghost Mode Tutorial',
            'description': 'Temporarily hide problematic users without full punishment!',
            'color': 0x95A5A6,
            'steps': [
                "**Step 1: Activate Ghost Mode**\n• `/ghost-mode @user` - Hide their messages temporarily\n• User can still see the server but others can't see them\n• Less harsh than muting or kicking",
                "**Step 2: Monitor User**\n• Ghost mode gives users time to cool down\n• They can still read and learn from others\n• Staff can still see their activity",
                "**Step 3: Restore Visibility**\n• Ghost mode can be lifted manually\n• Use for temporary cooling-off periods\n• Good middle ground between warning and muting"
            ],
            'tips': '💡 **Pro Tips:**\n• Great for heated arguments or minor disruptions\n• Less punitive than mutes but still effective\n• Explain to the user why they\'re in ghost mode!'
        }
    }
    
    if command not in tutorials:
        await interaction.response.send_message("❌ Tutorial not found! Use the dropdown to select a valid command bestie! 🤪", ephemeral=True)
        return
    
    tutorial = tutorials[command]
    
    embed = discord.Embed(
        title=tutorial['title'],
        description=tutorial['description'],
        color=tutorial['color']
    )
    
    # Add steps
    for i, step in enumerate(tutorial['steps'], 1):
        embed.add_field(
            name=f"📋 Step {i}",
            value=step,
            inline=False
        )
    
    # Add tips
    if 'tips' in tutorial:
        embed.add_field(
            name="💡 Pro Tips & Best Practices",
            value=tutorial['tips'],
            inline=False
        )
    
    # Add footer with related commands
    embed.set_footer(text="💡 Tip: Use /help to see all commands, or ask staff if you need help setting up!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎮 LEVELING SYSTEM COMMANDS 🎮

@tree.command(name="configlevel", description="⚙️ Configure the brainrot leveling system")
@app_commands.describe(setting="Enable or disable the leveling system")
@app_commands.choices(setting=[
    app_commands.Choice(name="Enable", value="enable"),
    app_commands.Choice(name="Disable", value="disable")
])
async def config_level_command(interaction: discord.Interaction, setting: str):
    """Configure leveling system with maximum brainrot energy"""

    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can configure the sigma grindset system bestie! 💀", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)

    if setting == "enable":
        guild_level_config[guild_id] = {"enabled": True}
        save_level_config()

        await interaction.response.send_message(
            "📈 **LEVELING SYSTEM ACTIVATED!** 📈\n\n"
            "🔥 The sigma grindset has been deployed!\n"
            "⚡ Users will now gain XP for being active!\n"
            "🏆 Level up messages will absolutely SEND!\n"
            "💪 Time to start grinding those levels!\n\n"
            "📊 **How it works:**\n"
            "• Send messages to gain XP (1 min cooldown) 💬\n"
            "• Level up with exponential growth 📈\n"
            "• Brainrot level-up messages 🎉\n"
            "• Check progress with `/level` or `/leaderboard` 👑\n\n"
            "The Ohio energy is now MAXIMUM! Let the grind begin! 💯"
        )

    else:
        guild_level_config[guild_id] = {"enabled": False}
        save_level_config()

        await interaction.response.send_message(
            "📉 **LEVELING SYSTEM DEACTIVATED** 📉\n\n"
            "💀 The sigma grindset has been paused!\n"
            "😔 No more level-up notifications!\n"
            "🚫 XP gains are now disabled!\n\n"
            "Users can still check their stats, but no new XP will be awarded.\n"
            "Use `/configlevel enable` to restart the grind! 💪"
        )

@tree.command(name="level", description="📊 Check your current brainrot level and XP")
async def level_command(interaction: discord.Interaction, user: discord.Member = None):
    """Check level with maximum Ohio energy"""

    target = user or interaction.user
    if target.bot:
        await interaction.response.send_message("🤖 Bots don't need to grind levels bestie, they're already at maximum sigma! 💀", ephemeral=True)
        return

    user_data = get_user_data(interaction.guild.id, target.id)
    current_xp = user_data['xp']
    current_level = user_data['level']
    messages_sent = user_data['messages']

    # Calculate XP for next level
    next_level_xp = xp_for_level(current_level + 1)
    current_level_xp = xp_for_level(current_level)
    xp_needed = next_level_xp - current_xp
    xp_progress = current_xp - current_level_xp
    xp_for_this_level = next_level_xp - current_level_xp

    # Progress bar
    progress_percent = (xp_progress / xp_for_this_level) if xp_for_this_level > 0 else 0
    bar_length = 20
    filled_length = int(bar_length * progress_percent)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    # Level titles based on level ranges
    if current_level >= 100:
        title = "🌟 Absolute Ohio Legend"
        color = 0xFFD700  # Gold
    elif current_level >= 75:
        title = "👑 Sigma Grindset Master"
        color = 0x9400D3  # Purple
    elif current_level >= 50:
        title = "🔥 Certified Brainrot Lord"
        color = 0xFF4500  # Red
    elif current_level >= 25:
        title = "⚡ Chaos Energy Wielder"
        color = 0x00FF00  # Green
    elif current_level >= 10:
        title = "🤪 Professional Yapper"
        color = 0x1E90FF  # Blue
    else:
        title = "🌱 Grass Touching Rookie"
        color = 0x808080  # Gray

    embed = discord.Embed(
        title=f"{title}",
        description=f"**{target.display_name}**'s Sigma Grindset Stats 📊",
        color=color
    )

    embed.add_field(
        name="📈 Current Level",
        value=f"**Level {current_level}** ({current_xp:,} XP)",
        inline=True
    )

    embed.add_field(
        name="🎯 Next Level",
        value=f"Need {xp_needed:,} more XP",
        inline=True
    )

    embed.add_field(
        name="💬 Messages Sent",
        value=f"{messages_sent:,} yappers",
        inline=True
    )

    embed.add_field(
        name="📊 Progress to Next Level",
        value=f"{bar} {progress_percent*100:.1f}%",
        inline=False
    )

    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)

    embed.set_footer(text="Keep grinding that sigma energy bestie! 💪")

    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="🏆 See the top sigma grinders in the server")
async def leaderboard_command(interaction: discord.Interaction):
    """Show the top level users with brainrot energy"""

    guild_id = str(interaction.guild.id)

    if guild_id not in user_levels or not user_levels[guild_id]:
        await interaction.response.send_message(
            "📊 No sigma grinders detected yet! 💀\n\n"
            "Start sending messages to begin your grindset journey! 💪\n"
            "(Make sure leveling is enabled with `/configlevel enable`)",
            ephemeral=True
        )
        return

    # Sort users by XP
    sorted_users = sorted(
        user_levels[guild_id].items(), 
        key=lambda x: x[1]['xp'], 
        reverse=True
    )

    # Get top 10
    top_users = sorted_users[:10]

    embed = discord.Embed(
        title="🏆 SIGMA GRINDSET LEADERBOARD 🏆",
        description="The most dedicated Ohio energy farmers! 💪",
        color=0xFFD700
    )

    leaderboard_text = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, (user_id, data) in enumerate(top_users):
        try:
            user = interaction.guild.get_member(int(user_id))
            if user:
                medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
                leaderboard_text += f"{medal} **{user.display_name}** - Level {data['level']} ({data['xp']:,} XP)\n"
        except:
            continue

    if not leaderboard_text:
        leaderboard_text = "No active grinders found! Start yapping to join the board! 💬"

    embed.add_field(name="Top Sigma Grinders", value=leaderboard_text, inline=False)
    embed.set_footer(text="Keep grinding bestie! Touch grass between sessions! 🌱")

    await interaction.response.send_message(embed=embed)

# 🎮 ABSOLUTELY UNHINGED COMMANDS 🎮

@tree.command(name="uno-reverse", description="🔄 Reverse the last moderation action (with limits)")
async def uno_reverse_command(interaction: discord.Interaction):
    """Uno reverse card for moderation"""

    await interaction.response.send_message(
        "🔄 **UNO REVERSE CARD ACTIVATED!** 🎯\n\n"
        "💀 The last moderation action has been... REVERSED!\n"
        "🎪 Chaos energy: MAXIMUM\n"
        "⚡ Plot armor: ACTIVATED\n"
        "🗿 Sigma energy: DEPLOYED\n\n"
        "You've played the ultimate card bestie! 🃏\n"
        "*But was it worth it?* 🤔"
    )

@tree.command(name="democracy", description="🗳️ Let server vote on punishment severity")
async def democracy_command(interaction: discord.Interaction, user: discord.Member, reason: str):
    """Democratic punishment system"""

    # Check permissions
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("🚫 Only moderators can start democracy mode! 🗳️", ephemeral=True)
        return

    await interaction.response.send_message(
        f"🗳️ **DEMOCRACY MODE ACTIVATED!** 🏛️\n\n"
        f"**Defendant:** {user.mention}\n"
        f"**Charges:** {reason}\n\n"
        "🎭 **Punishment Options:**\n"
        "⚡ 1️⃣ Warning (slap on wrist)\n"
        "🌱 2️⃣ Touch grass timeout\n"
        "🤖 3️⃣ NPC mode\n"
        "💀 4️⃣ Timeout (serious business)\n"
        "🌽 5️⃣ Ohio banishment\n\n"
        "React to vote! Democracy in action bestie! 🇺🇸\n"
        "*The people have spoken!* 📢"
    )

@tree.command(name="random-mute", description="🎲 Russian roulette but with mutes (opt-in)")
async def random_mute_command(interaction: discord.Interaction):
    """Random mute roulette"""

    chance = random.randint(1, 6)  # 1 in 6 chance like Russian roulette

    if chance == 1:
        await interaction.response.send_message(
            "💀 **BANG!** You got the mute! 🔇\n\n"
            "🎲 The dice have spoken!\n"
            "⚰️ Better luck next time bestie!\n"
            "🌱 Use this time to touch grass!"
        )
    else:
        await interaction.response.send_message(
            "✨ **CLICK!** You're safe! 🎉\n\n"
            "🎲 The RNG gods have blessed you!\n"
            "🍀 Lady luck is on your side!\n"
            "💫 Live to yap another day!"
        )


@tree.command(name="warning-auction", description="🔨 Bid to remove warnings with fake currency")
async def warning_auction_command(interaction: discord.Interaction):
    """Auction system for warnings"""

    starting_bid = random.randint(50, 200)

    await interaction.response.send_message(
        "🔨 **WARNING AUCTION HOUSE** 💰\n\n"
        "📋 **Item:** 1x Warning Removal\n"
        f"💎 **Starting Bid:** {starting_bid} Sigma Coins\n"
        "⏰ **Auction Time:** 24 hours\n\n"
        "🎯 **How to bid:**\n"
        "Type your bid in chat! (We use imaginary money here)\n\n"
        "💡 **Current exchange rates:**\n"
        "🪙 1 Touch Grass = 10 Sigma Coins\n"
        "🏆 1 W Moment = 25 Sigma Coins\n"
        "💀 1 L Moment = -15 Sigma Coins\n\n"
        "Good luck bestie! May the highest bidder win! 🎪"
    )

@tree.command(name="chaos-wheel", description="🎡 Spin wheel for random consequences/rewards")
async def chaos_wheel_command(interaction: discord.Interaction):
    """Spin the wheel of chaos"""

    outcomes = [
        "🎉 You won the lottery! (Imaginary money only)",
        "💀 You've been cursed with main character syndrome!",
        "🌱 Mandatory grass touching session activated!",
        "⚡ Sigma energy increased by 420%!",
        "🤖 You're now an NPC for the next hour!",
        "🎭 Plot armor activated! You're unstoppable!",
        "📮 Everyone thinks you're sus now!",
        "🔥 Your rizz levels have been maxed out!",
        "🌽 Welcome to Ohio, population: you!",
        "💫 You're the main character now bestie!",
        "🗿 Stone face mode: emotions disabled!",
        "🎪 You must speak only in brainrot for 1 hour!",
        "✨ Blessed with anti-cringe energy!",
        "💎 Your aura is now permanently diamond tier!",
        "🚀 You've transcended to a higher plane of existence!"
    ]

    result = random.choice(outcomes)

    await interaction.response.send_message(
        "🎡 **SPINNING THE CHAOS WHEEL...** 🌪️\n\n"
        "⚡ *Wheel spinning intensifies* ⚡\n"
        "🎯 *Destiny is being decided* 🎯\n"
        "✨ *The universe holds its breath* ✨\n\n"
        f"🎊 **RESULT:** {result}\n\n"
        "The wheel has spoken! Your fate is sealed! 🔮"
    )

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
            logger.error("❌ Invalid bot token! Check your DISCORD_TOKEN")
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
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("❌ No bot token found! Please set DISCORD_TOKEN in your environment variables!")
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
        pass
