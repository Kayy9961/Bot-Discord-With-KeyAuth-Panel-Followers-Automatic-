import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
import requests
import hashlib
import sys

from keyauth import api

def getchecksum():
    md5_hash = hashlib.md5()
    with open(''.join(sys.argv), "rb") as f:
        md5_hash.update(f.read())
    return md5_hash.hexdigest()

keyauthapp = api(
    name="RELLENAR",
    ownerid="RELLENAR",
    secret="RELLENAR",
    version="1.0",
    hash_to_check=getchecksum()
)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

canal_id = int(input("Por favor, ingresa el ID del canal donde deseas enviar el botón de crear ticket: "))
informacion_canal_id = 00000000000000000
ALLOWED_USER_ID = 000000000000000000

def realizar_pedido(url, seguidores, service_id, use_alternate_api=False):
    if use_alternate_api:
        api_endpoint = "API DE TU PANEL PRINCIPAL"
        api_key = "SECRET KEY DE TU PANEL PRINCIPAL"
    else:
        api_endpoint = "API DE TU PANEL SECUNDARIO"
        api_key = "SECRET KEY DE TU PANEL SECUNDARIO"

    headers = {"Content-Type": "application/json"}

    data = {
        "key": api_key,
        "action": "add",
        "service": service_id,
        "link": url,
        "quantity": seguidores
    }

    try:
        response = requests.post(api_endpoint, headers=headers, json=data)
        response.raise_for_status()
        return "success"
    except requests.exceptions.ConnectionError as e:
        return f"Error de conexión: {e}"
    except requests.exceptions.HTTPError as e:
        return f"Error HTTP: {e}"
    except requests.exceptions.RequestException as e:
        return f"Error durante la solicitud HTTP: {e}"

def check_key_in_file(key):
    try:
        with open("Keys.txt", "r") as file:
            keys = file.read().splitlines()
            return key in keys
    except FileNotFoundError:
        return False

def remove_key_from_file(key):
    try:
        with open("Keys.txt", "r") as file:
            keys = file.read().splitlines()

        keys = [k for k in keys if k != key]

        with open("Keys.txt", "w") as file:
            for k in keys:
                file.write(k + "\n")

        print(f"La Key {key} ha sido eliminada de Keys.txt.")
    except FileNotFoundError:
        print("El archivo Keys.txt no se encontró para editar.")
        pass

def parse_key(key):
    parts = key.split('-')
    if len(parts) == 5:
        return {
            "cantidad": int(parts[2]),
            "servicio": parts[3],
            "plataforma": parts[4]
        }
    return None

class ConfirmationView(View):
    def __init__(self, service_info, ticket_channel):
        super().__init__(timeout=None)
        self.service_info = service_info
        self.ticket_channel = ticket_channel
        self.confirm_button = Button(label="Sí, todo está correcto", style=discord.ButtonStyle.success, custom_id="confirm")
        self.retry_button = Button(label="No, empezar de nuevo", style=discord.ButtonStyle.danger, custom_id="retry")

        self.confirm_button.callback = self.confirm
        self.retry_button.callback = self.retry

        self.add_item(self.confirm_button)
        self.add_item(self.retry_button)

    async def confirm(self, interaction: discord.Interaction):
        service_ids = {
            "Instagram": {
                "Seguidores": 5488,
                "Likes": 6770,
                "Visitas": 5463
            },
            "TikTok": {
                "Seguidores": 5524,
                "Likes": 5383,
                "Visitas": 5084
            }
        }

        service_id = service_ids.get(self.service_info["category"], {}).get(self.service_info["service"])
        if service_id is None:
            await interaction.response.send_message("Servicio no válido.", ephemeral=True)
            return

        use_alternate_api = (self.service_info["category"] == "TikTok" or
                             (self.service_info["category"] == "Instagram" and self.service_info["service"] != "Likes"))
        resultado = realizar_pedido(
            url=self.service_info["link"],
            seguidores=self.service_info["quantity"],
            service_id=service_id,
            use_alternate_api=use_alternate_api
        )

        if resultado == "success":
            embed_success = discord.Embed(
                title="Pedido Realizado Exitosamente",
                description=f"El pedido ha sido procesado para {interaction.user.mention}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed_success, ephemeral=True)

            embed_accepted = discord.Embed(
                title="¡Solicitud Aceptada!",
                description="Tu pedido ha sido aceptado y procesado. Aquí están los detalles:",
                color=discord.Color.green()
            )
            embed_accepted.add_field(name="Plataforma", value=self.service_info["category"], inline=False)
            embed_accepted.add_field(name="Servicio", value=self.service_info["service"], inline=False)
            embed_accepted.add_field(name="Cantidad", value=self.service_info["quantity"], inline=False)
            embed_accepted.add_field(name="Enlace", value=self.service_info["link"], inline=False)
            
            await interaction.channel.send(embed=embed_accepted)

            embed_info = discord.Embed(
                title="Información",
                description=(
                    "- Tu pedido ya está listo y no tienes que hacer nada. \n"
                    "- Solo tienes que esperar.\n"
                    "- El tiempo puede variar.\n"
                    "- No te preocupes, todo llega, solo debes esperar.\n"
                    "- Si no llega en 24 horas, crea otro ticket en <#1263922105217450054>."
                ),
                color=discord.Color.blue()
            )
            await interaction.channel.send(embed=embed_info)
        else:
            await interaction.response.send_message(f"Error al realizar el pedido: {resultado}", ephemeral=True)

    async def retry(self, interaction: discord.Interaction):
        await interaction.channel.purge(limit=100)
        await interaction.channel.send("Vamos a empezar de nuevo. Por favor, envía el enlace para completar el pedido:")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        link_msg = await bot.wait_for('message', check=check)
        link = link_msg.content

        embed_order = discord.Embed(
            title="Resumen del Pedido",
            description="A continuación se muestra la información que has proporcionado:",
            color=discord.Color.blue()
        )
        embed_order.add_field(name="Usuario", value=interaction.user.mention, inline=False)
        embed_order.add_field(name="Plataforma", value=self.service_info['category'], inline=False)
        embed_order.add_field(name="Servicio", value=self.service_info['service'], inline=False)
        embed_order.add_field(name="Cantidad", value=self.service_info['quantity'], inline=False)
        embed_order.add_field(name="Enlace", value=link, inline=False)

        self.service_info['link'] = link  

        await interaction.channel.send(embed=embed_order, view=self)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="💰 Comprar Cuenta", value="buy_account"),
            discord.SelectOption(label="🔑 Comprar Seguidores Con Key", value="followers_paid"),
            discord.SelectOption(label="💸 Discord Nitro Barato", value="buy_nitro"),
            discord.SelectOption(label="❓ Otra cosa", value="other")
        ]
        super().__init__(placeholder='Selecciona una opción', min_values=1, max_values=1, options=options, custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        ticket_channel = await guild.create_text_channel(f"ticket-{member.name}", overwrites=overwrites)

        embed_ticket = discord.Embed(
            title="Kayy Shop",
            description=f"Hola {member.mention}, este es tu ticket.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed_ticket)

        await interaction.response.send_message(f"Ticket creado: {ticket_channel.mention}", ephemeral=True)

        if self.values[0] == "followers_paid":
            embed_info = discord.Embed(
                title="Información sobre la compra de seguidores",
                description=(
                    "- Compra tu Key en https://kayyshop.sellauth.com \n"
                    "- Pon tu correo electrónico correctamente.\n"
                    "- Una vez pagado recibirás un correo con tu Key.\n"
                    "- **Suele llegar el correo a la carpeta de 'SPAM'**.\n"
                    "- Si no llega ningún correo en 20 minutos, abre otro ticket en <#1263922105217450054>.\n"
                    "- **Por favor, al enviar el enlace de su perfil/video revise que esté bien.**"
                ),
                color=discord.Color.blue()
            )
            await ticket_channel.send(embed=embed_info)

            await ticket_channel.send("Por favor, ingresa tu Key para continuar:")

            def check(m):
                return m.author == member and m.channel == ticket_channel

            mensaje = await bot.wait_for('message', check=check)
            key = mensaje.content
            if check_key_in_file(key):
                keyauthapp.license(key)
                if keyauthapp.check():
                    parsed_key = parse_key(key)
                    if parsed_key:
                        await ticket_channel.send("Por favor, envía el enlace para completar el pedido.")
                        remove_key_from_file(key)

                        link_msg = await bot.wait_for('message', check=check)
                        link = link_msg.content

                        embed_order = discord.Embed(
                            title="Resumen del Pedido",
                            description="A continuación se muestra la información que has proporcionado:",
                            color=discord.Color.blue()
                        )
                        embed_order.add_field(name="Usuario", value=member.mention, inline=False)
                        embed_order.add_field(name="Plataforma", value=parsed_key['plataforma'], inline=False)
                        embed_order.add_field(name="Servicio", value=parsed_key['servicio'], inline=False)
                        embed_order.add_field(name="Cantidad", value=parsed_key['cantidad'], inline=False)
                        embed_order.add_field(name="Enlace", value=link, inline=False)

                        confirmation_view = ConfirmationView({
                            "category": parsed_key['plataforma'],
                            "service": parsed_key['servicio'],
                            "quantity": parsed_key['cantidad'],
                            "link": link
                        }, ticket_channel)

                        await ticket_channel.send(embed=embed_order, view=confirmation_view)

                    else:
                        await ticket_channel.send("Formato de Key no válido. Cerrando ticket...")
                        await ticket_channel.delete()
                else:
                    await ticket_channel.send("Clave incorrecta o inválida en KeyAuth. Por favor, verifica la clave e inténtalo de nuevo.")
                    await ticket_channel.delete()
            else:
                await ticket_channel.send("Clave no encontrada en el sistema. Cerrando ticket...")
                await ticket_channel.delete()
        else:
            close_ticket_button = Button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_general")
            close_ticket_view = View(timeout=None)
            close_ticket_view.add_item(close_ticket_button)

            async def close_ticket(interaction: discord.Interaction):
                await interaction.response.defer()
                await ticket_channel.delete()

            close_ticket_button.callback = close_ticket
            await ticket_channel.send("Un moderador atenderá su ticket lo más rápido posible")
            await ticket_channel.send("Usa este botón para cerrar el ticket cuando hayas terminado o necesites ayuda.", view=close_ticket_view)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    canal = bot.get_channel(canal_id)
    if canal is None:
        print("Canal no encontrado. Asegúrate de que el ID es correcto.")
        return

    embed_intro = discord.Embed(
        title="Kayy Shop | Tickets",
        description="Abre ticket si deseas comprar una cuenta o tienes cualquier duda.",
        color=discord.Color.green()
    )
    embed_intro.set_footer(text="Ticket Tool Created By Kayy")

    view = TicketView()
    bot.add_view(view)

    await canal.send(embed=embed_intro, view=view)
    print(f"Botón de creación de ticket enviado al canal: {canal.name}")

bot.run('TOKEN DE TU BOT')
