import discord
import asyncio
import requests
import json
import os
import logging
from discord.ext import commands, tasks

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot-Konfiguration aus Umgebungsvariablen
TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = int(os.environ.get('GUILD_ID', '0'))
ROLE_ID = int(os.environ.get('ROLE_ID', '0'))
SERVER_API = os.environ.get('SERVER_API', 'http://localhost:30120')
API_KEY = os.environ.get('API_KEY', 'default_api_key')

# Bot-Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Bot erstellen
bot = commands.Bot(command_prefix='!azb ', intents=intents, help_command=None)

# Globale Variablen
server_online = False

@bot.event
async def on_ready():
    logger.info(f'🚀 Alpha Zentauri Base Bot ist online!')
    logger.info(f'📡 Bot-Name: {bot.user.name}#{bot.user.discriminator}')
    logger.info(f'🏠 Überwache Server: {GUILD_ID}')
    logger.info(f'🎭 Überwache Rolle: {ROLE_ID}')
    logger.info(f'🌐 FiveM Server: {SERVER_API}')
    
    # Status setzen
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Alpha Zentauri Base | !azb info"
        ),
        status=discord.Status.online
    )
    
    # Server-Check starten
    server_check.start()

@tasks.loop(minutes=5)
async def server_check():
    """Überprüft regelmäßig den FiveM-Server Status"""
    global server_online
    
    try:
        response = requests.get(f"{SERVER_API}/api/status", timeout=10)
        current_status = response.status_code == 200
        
        if server_online != current_status:
            server_online = current_status
            
            if server_online:
                await bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name="Alpha Zentauri Base | Server Online"
                    ),
                    status=discord.Status.online
                )
                logger.info("✅ FiveM Server ist online")
            else:
                await bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name="Alpha Zentauri Base | Server Offline"
                    ),
                    status=discord.Status.idle
                )
                logger.warning("❌ FiveM Server ist offline")
        
    except Exception as e:
        if server_online:
            logger.error(f"Server-Check Fehler: {e}")
            server_online = False

@bot.event
async def on_member_update(before, after):
    """Reagiert auf Rollenänderungen"""
    # Nur auf dem konfigurierten Server reagieren
    if after.guild.id != GUILD_ID:
        return
        
    # Prüfen, ob die Rolle hinzugefügt wurde
    had_role = discord.utils.get(before.roles, id=ROLE_ID)
    has_role = discord.utils.get(after.roles, id=ROLE_ID)
    
    if not had_role and has_role:
        logger.info(f'✅ Rolle hinzugefügt für {after.name}#{after.discriminator}')
        
        # Willkommensnachricht per DM senden
        embed = discord.Embed(
            title="🚀 Willkommen bei Alpha Zentauri Base!",
            description="Du hast Zugang zu unserem FiveM-Server erhalten!",
            color=0x9932cc
        )
        
        embed.add_field(
            name="📋 So verbindest du dich:",
            value=f"1. **Starte FiveM**\n2. **Drücke F8** und gib ein:\n```connect {SERVER_API.replace('http://', '').replace(':30120', '')}```\n3. **Warte auf den Login-Screen**\n4. **Erstelle deinen Charakter**",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Wichtige Links:",
            value="**Discord:** https://discord.gg/pvVDVVK9jc\n**Regeln:** Lies die Serverregeln\n**Support:** Wende dich an die Admins",
            inline=False
        )
        
        embed.set_footer(text="Alpha Zentauri Base - Dein Premium GTA Roleplay Server")
        
        try:
            await after.send(embed=embed)
            logger.info(f"📨 Willkommensnachricht an {after.name} gesendet")
        except discord.Forbidden:
            logger.warning(f"❌ Kann keine DM an {after.name} senden")
            
            # Fallback: Nachricht im Channel
            channel = after.guild.system_channel
            if channel:
                await channel.send(f"🎉 Willkommen {after.mention}! Ich konnte dir keine DM senden. Bitte aktiviere DMs von Servermitgliedern.")

# Commands
@bot.command(name='status')
@commands.has_permissions(administrator=True)
async def server_status(ctx):
    """Zeigt den Status des FiveM-Servers"""
    try:
        response = requests.get(f"{SERVER_API}/api/status", timeout=10)
        
        embed = discord.Embed(
            title="🖥️ Server-Status",
            color=0x00ff00 if response.status_code == 200 else 0xff0000
        )
        
        if response.status_code == 200:
            embed.description = "✅ FiveM-Server ist **online**"
        else:
            embed.description = f"❌ Server antwortet nicht (HTTP {response.status_code})"
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Verbindungsfehler",
            description=f"Fehler: {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.command(name='welcome')
@commands.has_permissions(administrator=True)
async def send_welcome_manual(ctx, member: discord.Member):
    """Sendet manuell eine Willkommensnachricht"""
    embed = discord.Embed(
        title="🚀 Willkommen bei Alpha Zentauri Base!",
        description="Du hast Zugang zu unserem FiveM-Server erhalten!",
        color=0x9932cc
    )
    
    embed.add_field(
        name="📋 So verbindest du dich:",
        value=f"1. **Starte FiveM**\n2. **Drücke F8** und gib ein:\n```connect {SERVER_API.replace('http://', '').replace(':30120', '')}```\n3. **Warte auf den Login-Screen**\n4. **Erstelle deinen Charakter**",
        inline=False
    )
    
    embed.add_field(
        name="🔗 Wichtige Links:",
        value="**Discord:** https://discord.gg/pvVDVVK9jc\n**Regeln:** Lies die Serverregeln\n**Support:** Wende dich an die Admins",
        inline=False
    )
    
    embed.set_footer(text="Alpha Zentauri Base - Dein Premium GTA Roleplay Server")
    
    try:
        await member.send(embed=embed)
        await ctx.send(f"✅ Willkommensnachricht an {member.mention} gesendet!")
    except discord.Forbidden:
        await ctx.send(f"❌ Kann keine DM an {member.mention} senden.")

@bot.command(name='info')
async def bot_info(ctx):
    """Zeigt Bot-Informationen"""
    embed = discord.Embed(
        title="🤖 Alpha Zentauri Base Bot",
        description="Discord-Bot für das FiveM Login-System",
        color=0x9932cc
    )
    
    embed.add_field(
        name="📊 Status", 
        value=f"**Latenz:** {round(bot.latency * 1000)}ms\n**Server:** {'🟢 Online' if server_online else '🔴 Offline'}", 
        inline=True
    )
    embed.add_field(
        name="📋 Commands", 
        value="**!azb status** - Server prüfen\n**!azb welcome @user** - Willkommensnachricht\n**!azb info** - Bot-Info", 
        inline=True
    )
    
    embed.add_field(
        name="🔗 Links",
        value="**Discord:** https://discord.gg/pvVDVVK9jc\n**Server:** Alpha Zentauri Base RP",
        inline=False
    )
    
    embed.set_footer(text="Alpha Zentauri Base - Entwickelt für das beste Roleplay")
    
    await ctx.send(embed=embed)

# Fehlerbehandlung
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Keine Berechtigung",
            description="Du brauchst **Administrator-Rechte** für diesen Befehl.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignoriere unbekannte Befehle
    else:
        logger.error(f"Command-Fehler: {error}")

# Bot starten
if __name__ == "__main__":
    # Überprüfe Umgebungsvariablen
    required_vars = ['DISCORD_TOKEN', 'GUILD_ID', 'ROLE_ID']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"❌ Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")
        logger.info("Setze diese Umgebungsvariablen:")
        logger.info("DISCORD_TOKEN = dein_bot_token")
        logger.info("GUILD_ID = deine_server_id")
        logger.info("ROLE_ID = deine_rollen_id")
        exit(1)
    
    logger.info("🚀 Starte Alpha Zentauri Base Discord Bot...")
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        logger.error("❌ Ungültiger Discord-Token!")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler: {e}")
        exit(1)
