import discord
import asyncio
import requests
import json
import os
import logging
import random
import string
from datetime import datetime
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
accounts_file = 'accounts.json'

# Account-Verwaltung
def load_accounts():
    """Lädt Accounts aus JSON-Datei"""
    try:
        if os.path.exists(accounts_file):
            with open(accounts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Accounts: {e}")
        return {}

def save_accounts(accounts):
    """Speichert Accounts in JSON-Datei"""
    try:
        with open(accounts_file, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Accounts: {e}")
        return False

def generate_username():
    """Generiert einen zufälligen Username"""
    prefix = "AZB_"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return prefix + suffix

def generate_password(length=8):
    """Generiert ein zufälliges Passwort"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def create_account(discord_id, discord_username):
    """Erstellt einen neuen Account"""
    accounts = load_accounts()
    
    # Prüfen ob Account bereits existiert
    if discord_id in accounts:
        # Neues Passwort generieren
        accounts[discord_id]['password'] = generate_password()
        accounts[discord_id]['last_updated'] = datetime.now().isoformat()
        logger.info(f"Passwort erneuert für {discord_username}")
    else:
        # Neuen Account erstellen
        accounts[discord_id] = {
            'username': generate_username(),
            'password': generate_password(),
            'discord_username': discord_username,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'last_login': None
        }
        logger.info(f"Neuer Account erstellt für {discord_username}")
    
    # Accounts speichern
    if save_accounts(accounts):
        return accounts[discord_id]
    return None

async def find_member(ctx, user_input):
    """Findet einen Member basierend auf verschiedenen Inputs"""
    guild = ctx.guild
    
    # Versuche verschiedene Methoden
    member = None
    
    # 1. Direkte Mention
    if isinstance(user_input, discord.Member):
        return user_input
    
    # 2. User ID
    if user_input.isdigit():
        try:
            member = guild.get_member(int(user_input))
            if member:
                return member
        except:
            pass
    
    # 3. Username#discriminator
    if '#' in user_input:
        for m in guild.members:
            if f"{m.name}#{m.discriminator}" == user_input:
                return m
    
    # 4. Display name oder username
    user_input_lower = user_input.lower()
    for m in guild.members:
        if (m.name.lower() == user_input_lower or 
            m.display_name.lower() == user_input_lower):
            return m
    
    # 5. Teilweise Übereinstimmung
    for m in guild.members:
        if (user_input_lower in m.name.lower() or 
            user_input_lower in m.display_name.lower()):
            return m
    
    return None

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
        
        # Account erstellen
        account = create_account(str(after.id), f"{after.name}#{after.discriminator}")
        
        if account:
            # Willkommensnachricht mit Zugangsdaten per DM senden
            embed = discord.Embed(
                title="🚀 Willkommen bei Alpha Zentauri Base!",
                description="Dein Account wurde erfolgreich erstellt!",
                color=0x9932cc
            )
            
            embed.add_field(
                name="🔐 Deine Zugangsdaten:",
                value=f"**Benutzername:** `{account['username']}`\n**Passwort:** `{account['password']}`",
                inline=False
            )
            
            embed.add_field(
                name="📋 So verbindest du dich:",
                value=f"1. **Starte FiveM**\n2. **Drücke F8** und gib ein:\n```connect {SERVER_API.replace('http://', '').replace(':30120', '')}```\n3. **Gib deine Zugangsdaten ein**\n4. **Erstelle deinen Charakter**",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Wichtige Hinweise:",
                value="• **Teile deine Zugangsdaten mit niemandem!**\n• **Screenshot diese Nachricht** für später\n• **Bei Problemen:** Wende dich an die Admins",
                inline=False
            )
            
            embed.add_field(
                name="🔗 Wichtige Links:",
                value="**Discord:** https://discord.gg/pvVDVVK9jc\n**Regeln:** Lies die Serverregeln\n**Support:** Ticket erstellen",
                inline=False
            )
            
            embed.set_footer(text="Alpha Zentauri Base - Dein Premium GTA Roleplay Server")
            
            try:
                await after.send(embed=embed)
                logger.info(f"📨 Zugangsdaten an {after.name} gesendet")
                
            except discord.Forbidden:
                logger.warning(f"❌ Kann keine DM an {after.name} senden")
                
                # Fallback: Nachricht im Channel
                channel = after.guild.system_channel
                if channel:
                    fallback_embed = discord.Embed(
                        title="❌ DM fehlgeschlagen",
                        description=f"Konnte {after.mention} keine DM senden. Bitte aktiviere DMs von Servermitgliedern.",
                        color=0xff0000
                    )
                    await channel.send(embed=fallback_embed)
        else:
            logger.error(f"❌ Fehler beim Erstellen des Accounts für {after.name}")

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

@bot.command(name='create')
@commands.has_permissions(administrator=True)
async def create_account_manual(ctx, *, user_input):
    """Erstellt manuell einen Account für einen Benutzer"""
    # Versuche Member zu finden
    member = await find_member(ctx, user_input)
    
    if not member:
        embed = discord.Embed(
            title="❌ Benutzer nicht gefunden",
            description=f"Konnte keinen Benutzer mit `{user_input}` finden.\n\n**Versuche:**\n• `!azb create @Username` (echte Erwähnung)\n• `!azb create Username`\n• `!azb create 123456789` (User ID)",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    # Account erstellen
    account = create_account(str(member.id), f"{member.name}#{member.discriminator}")
    
    if account:
        embed = discord.Embed(
            title="✅ Account erstellt",
            description=f"Account für {member.mention} wurde erstellt:",
            color=0x00ff00
        )
        embed.add_field(
            name="🔐 Zugangsdaten:",
            value=f"**Username:** `{account['username']}`\n**Passwort:** `{account['password']}`",
            inline=False
        )
        await ctx.send(embed=embed, delete_after=30)  # Nachricht nach 30s löschen
        
        # DM an Benutzer senden
        try:
            user_embed = discord.Embed(
                title="🔐 Deine Zugangsdaten",
                description="Ein Admin hat dir einen Account erstellt:",
                color=0x9932cc
            )
            user_embed.add_field(
                name="🔐 Zugangsdaten:",
                value=f"**Benutzername:** `{account['username']}`\n**Passwort:** `{account['password']}`",
                inline=False
            )
            user_embed.add_field(
                name="📋 Server-Verbindung:",
                value=f"1. **Starte FiveM**\n2. **Drücke F8** und gib ein:\n```connect {SERVER_API.replace('http://', '').replace(':30120', '')}```\n3. **Gib deine Zugangsdaten ein**",
                inline=False
            )
            await member.send(embed=user_embed)
            logger.info(f"📨 Zugangsdaten per DM an {member.name} gesendet")
        except discord.Forbidden:
            await ctx.send(f"⚠️ Konnte {member.mention} keine DM senden.", delete_after=10)
    else:
        embed = discord.Embed(
            title="❌ Fehler",
            description="Account konnte nicht erstellt werden.",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.command(name='reset')
@commands.has_permissions(administrator=True)
async def reset_password(ctx, *, user_input):
    """Setzt das Passwort eines Benutzers zurück"""
    member = await find_member(ctx, user_input)
    
    if not member:
        embed = discord.Embed(
            title="❌ Benutzer nicht gefunden",
            description=f"Konnte keinen Benutzer mit `{user_input}` finden.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    account = create_account(str(member.id), f"{member.name}#{member.discriminator}")
    
    if account:
        embed = discord.Embed(
            title="🔄 Passwort zurückgesetzt",
            description=f"Neues Passwort für {member.mention}:",
            color=0x00ff00
        )
        embed.add_field(
            name="🔐 Neue Zugangsdaten:",
            value=f"**Username:** `{account['username']}`\n**Passwort:** `{account['password']}`",
            inline=False
        )
        await ctx.send(embed=embed, delete_after=30)
        
        # DM an Benutzer
        try:
            user_embed = discord.Embed(
                title="🔄 Passwort zurückgesetzt",
                description="Dein Passwort wurde zurückgesetzt:",
                color=0x9932cc
            )
            user_embed.add_field(
                name="🔐 Neue Zugangsdaten:",
                value=f"**Benutzername:** `{account['username']}`\n**Passwort:** `{account['password']}`",
                inline=False
            )
            await member.send(embed=user_embed)
        except discord.Forbidden:
            await ctx.send(f"⚠️ Konnte {member.mention} keine DM senden.", delete_after=10)

@bot.command(name='accounts')
@commands.has_permissions(administrator=True)
async def list_accounts(ctx):
    """Zeigt alle erstellten Accounts"""
    accounts = load_accounts()
    
    if not accounts:
        embed = discord.Embed(
            title="📋 Account-Liste",
            description="Keine Accounts vorhanden.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📋 Account-Liste",
        description=f"Insgesamt {len(accounts)} Accounts:",
        color=0x9932cc
    )
    
    for discord_id, account in accounts.items():
        try:
            user = await bot.fetch_user(int(discord_id))
            username = f"{user.name}#{user.discriminator}"
        except:
            username = account.get('discord_username', 'Unbekannt')
            
        embed.add_field(
            name=f"👤 {username}",
            value=f"**Login:** `{account['username']}`\n**Erstellt:** {account.get('created_at', 'Unbekannt')[:10]}",
            inline=True
        )
    
    await ctx.send(embed=embed, delete_after=60)

@bot.command(name='info')
async def bot_info(ctx):
    """Zeigt Bot-Informationen"""
    accounts = load_accounts()
    
    embed = discord.Embed(
        title="🤖 Alpha Zentauri Base Bot",
        description="Discord-Bot für das FiveM Login-System",
        color=0x9932cc
    )
    
    embed.add_field(
        name="📊 Status", 
        value=f"**Latenz:** {round(bot.latency * 1000)}ms\n**Server:** {'🟢 Online' if server_online else '🔴 Offline'}\n**Accounts:** {len(accounts)}", 
        inline=True
    )
    embed.add_field(
        name="📋 Commands", 
        value="**!azb status** - Server prüfen\n**!azb create @user** - Account erstellen\n**!azb reset @user** - Passwort zurücksetzen\n**!azb accounts** - Account-Liste", 
        inline=True
    )
    
    embed.add_field(
        name="🔗 Links",
        value="**Discord:** https://discord.gg/pvVDVVK9jc\n**Server:** Alpha Zentauri Base RP",
        inline=False
    )
    
    embed.set_footer(text="Alpha Zentauri Base - Entwickelt für das beste Roleplay")
    
    await ctx.send(embed=embed)

# Verbesserte Fehlerbehandlung
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Keine Berechtigung",
            description="Du brauchst **Administrator-Rechte** für diesen Befehl.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Fehlende Parameter",
            description=f"**Verwendung:** `{ctx.prefix}{ctx.command.name} <benutzer>`\n\n**Beispiele:**\n• `!azb create @Username`\n• `!azb create Username`\n• `!azb create 123456789`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignoriere unbekannte Befehle
    else:
        logger.error(f"Command-Fehler: {error}")
        embed = discord.Embed(
            title="❌ Unbekannter Fehler",
            description=f"Ein Fehler ist aufgetreten: `{str(error)[:100]}`",
            color=0xff0000
        )
        await ctx.send(embed=embed)

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
