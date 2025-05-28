import discord
import asyncio
import requests
import json
import os
import logging
import random
import string
import socket
from datetime import datetime
from discord.ext import commands, tasks
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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
SERVER_IP = os.environ.get('SERVER_IP', 'localhost')
SERVER_PORT = int(os.environ.get('SERVER_PORT', '40120'))
API_KEY = os.environ.get('API_KEY', 'default_api_key')

# Render.com Port
RENDER_PORT = int(os.environ.get('PORT', '10000'))

# Einfacher HTTP-Handler für Render.com
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'bot': 'Alpha Zentauri Base',
                'server_online': server_online
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = '''
            <html>
            <head><title>Alpha Zentauri Base Bot</title></head>
            <body>
                <h1>🤖 Alpha Zentauri Base Discord Bot</h1>
                <p>Status: <strong>Online</strong></p>
                <p>Server: <strong>{}</strong></p>
                <p><a href="/health">Health Check</a></p>
            </body>
            </html>
            '''.format('🟢 Online' if server_online else '🔴 Offline')
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Unterdrücke HTTP-Logs

def start_http_server():
    """Startet HTTP-Server für Render.com"""
    try:
        server = HTTPServer(('0.0.0.0', RENDER_PORT), HealthCheckHandler)
        logger.info(f"🌐 HTTP-Server gestartet auf Port {RENDER_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ HTTP-Server Fehler: {e}")

# Bot-Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Bot erstellen
bot = commands.Bot(command_prefix='!azb ', intents=intents, help_command=None)

# Globale Variablen
server_online = False
accounts_file = 'accounts.json'

# [Rest des Bot-Codes bleibt gleich - Account-Verwaltung, Commands, etc.]

def check_server_port(host, port, timeout=5):
    """Prüft ob ein Port erreichbar ist"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Port-Check Fehler: {e}")
        return False

def check_server_http(host, port):
    """Prüft FiveM-Server über HTTP"""
    try:
        endpoints = [
            f"http://{host}:{port}/info.json",
            f"http://{host}:{port}/players.json",
            f"http://{host}:{port}/api/status"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ HTTP-Endpoint erreichbar: {endpoint}")
                    return True, endpoint
            except:
                continue
                
        return False, None
    except Exception as e:
        logger.error(f"HTTP-Check Fehler: {e}")
        return False, None

# Account-Verwaltung
def load_accounts():
    try:
        if os.path.exists(accounts_file):
            with open(accounts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Accounts: {e}")
        return {}

def save_accounts(accounts):
    try:
        with open(accounts_file, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Accounts: {e}")
        return False

def generate_username():
    prefix = "AZB_"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return prefix + suffix

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def create_account(discord_id, discord_username):
    accounts = load_accounts()
    
    if discord_id in accounts:
        accounts[discord_id]['password'] = generate_password()
        accounts[discord_id]['last_updated'] = datetime.now().isoformat()
        logger.info(f"Passwort erneuert für {discord_username}")
    else:
        accounts[discord_id] = {
            'username': generate_username(),
            'password': generate_password(),
            'discord_username': discord_username,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'last_login': None
        }
        logger.info(f"Neuer Account erstellt für {discord_username}")
    
    if save_accounts(accounts):
        return accounts[discord_id]
    return None

@bot.event
async def on_ready():
    logger.info(f'🚀 Alpha Zentauri Base Bot ist online!')
    logger.info(f'📡 Bot-Name: {bot.user.name}#{bot.user.discriminator}')
    logger.info(f'🏠 Überwache Server: {GUILD_ID}')
    logger.info(f'🎭 Überwache Rolle: {ROLE_ID}')
    logger.info(f'🌐 FiveM Server: {SERVER_IP}:{SERVER_PORT}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Alpha Zentauri Base | !azb info"
        ),
        status=discord.Status.online
    )
    
    server_check.start()

@tasks.loop(minutes=2)
async def server_check():
    global server_online
    
    port_open = check_server_port(SERVER_IP, SERVER_PORT)
    http_available = False
    if port_open:
        http_available, endpoint = check_server_http(SERVER_IP, SERVER_PORT)
    
    current_status = port_open
    
    if server_online != current_status:
        server_online = current_status
        
        if server_online:
            status_text = "Server Online"
            if http_available:
                status_text += " (HTTP ✅)"
            else:
                status_text += " (HTTP ❌)"
                
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"Alpha Zentauri Base | {status_text}"
                ),
                status=discord.Status.online
            )
            logger.info(f"✅ FiveM Server ist online")
        else:
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Alpha Zentauri Base | Server Offline"
                ),
                status=discord.Status.idle
            )
            logger.warning("❌ FiveM Server ist offline")

@bot.event
async def on_member_update(before, after):
    if after.guild.id != GUILD_ID:
        return
        
    had_role = discord.utils.get(before.roles, id=ROLE_ID)
    has_role = discord.utils.get(after.roles, id=ROLE_ID)
    
    if not had_role and has_role:
        logger.info(f'✅ Rolle hinzugefügt für {after.name}#{after.discriminator}')
        
        account = create_account(str(after.id), f"{after.name}#{after.discriminator}")
        
        if account:
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
                value=f"1. **Starte FiveM**\n2. **Drücke F8** und gib ein:\n```connect {SERVER_IP}:{SERVER_PORT}```\n3. **Gib deine Zugangsdaten ein**\n4. **Erstelle deinen Charakter**",
                inline=False
            )
            
            embed.set_footer(text="Alpha Zentauri Base - Dein Premium GTA Roleplay Server")
            
            try:
                await after.send(embed=embed)
                logger.info(f"📨 Zugangsdaten an {after.name} gesendet")
            except discord.Forbidden:
                logger.warning(f"❌ Kann keine DM an {after.name} senden")

@bot.command(name='info')
async def bot_info(ctx):
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
        name="🌐 Server", 
        value=f"**IP:** {SERVER_IP}\n**Port:** {SERVER_PORT}\n**Connect:** `connect {SERVER_IP}:{SERVER_PORT}`", 
        inline=True
    )
    
    embed.set_footer(text="Alpha Zentauri Base - Entwickelt für das beste Roleplay")
    await ctx.send(embed=embed)

# Bot starten
if __name__ == "__main__":
    # HTTP-Server in separatem Thread starten
    http_thread = Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Überprüfe Umgebungsvariablen
    required_vars = ['DISCORD_TOKEN', 'GUILD_ID', 'ROLE_ID']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"❌ Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")
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
