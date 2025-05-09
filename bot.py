import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Game state (in-memory)
game_state = {
    "active": False,
    "channel_id": None,
    "initiator_id": None,
    "opted_in": set(),
    "opted_out": set(),
    "confirmed_time": None,
    "game_id": None,
    "continent": None,
    "codename": None
}

MAX_PLAYERS = 5
TEST_CHANNEL_ID = 1370472320195498104
CET_TIME = "9 PM CET"
EST_TIME = "3 PM EST"

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start_game", description="Start a new game coordination.")
    async def start_game(self, interaction: discord.Interaction):
        if game_state["active"]:
            await interaction.response.send_message("A game coordination is already in progress.", ephemeral=True)
            return

        game_state.update({
            "active": True,
            "channel_id": interaction.channel.id,
            "initiator_id": interaction.user.id,
            "opted_in": set(),
            "opted_out": set(),
            "confirmed_time": None,
            "game_id": None,
            "continent": None,
            "codename": None
        })

        await interaction.response.send_message(
            f"New game coordination started by {interaction.user.mention}!\n\n"
            f"Players can now opt in using /opt_in.\n"
            f"Time slots will be 3 PM EST or 9 PM CET.",
            allowed_mentions=discord.AllowedMentions(users=True)
        )

    @app_commands.command(name="opt_in", description="Opt in to the current game.")
    async def opt_in(self, interaction: discord.Interaction):
        if not game_state["active"]:
            await interaction.response.send_message("No game coordination in progress.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in game_state["opted_in"]:
            await interaction.response.send_message("You already opted in.", ephemeral=True)
            return

        if len(game_state["opted_in"]) >= MAX_PLAYERS:
            await interaction.response.send_message("Opt-in is already full (5 players).", ephemeral=True)
            return

        game_state["opted_in"].add(user_id)
        await interaction.response.send_message(f"{interaction.user.mention} opted in. ({len(game_state['opted_in'])}/5)")

    @app_commands.command(name="opt_out", description="Opt out of the current game.")
    async def opt_out(self, interaction: discord.Interaction):
        if not game_state["active"]:
            await interaction.response.send_message("No game coordination in progress.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in game_state["opted_in"]:
            game_state["opted_in"].remove(user_id)

        game_state["opted_out"].add(user_id)
        await interaction.response.send_message(f"{interaction.user.mention} opted out.")

    @app_commands.command(name="finish_optin", description="Finish the opt-in phase before 5 players are reached.")
    async def finish_optin(self, interaction: discord.Interaction):
        if interaction.user.id != game_state["initiator_id"]:
            await interaction.response.send_message("Only the game initiator can finish the opt-in phase.", ephemeral=True)
            return

        await interaction.response.send_message("Opt-in phase closed. Initiator can now assign a game ID using /set_game_id.")

    @app_commands.command(name="set_game_id", description="Set the game ID and create a dedicated channel.")
    @app_commands.describe(game_id="The full game ID (e.g., 2053)", continent="Continent (e.g., Europe)", codename="Military codename (e.g., Eagle)")
    async def set_game_id(self, interaction: discord.Interaction, game_id: str, continent: str, codename: str):
        if interaction.user.id != game_state["initiator_id"]:
            await interaction.response.send_message("Only the initiator can set the game ID.", ephemeral=True)
            return

        game_state["game_id"] = game_id
        game_state["continent"] = continent
        game_state["codename"] = codename

        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            **{guild.get_member(uid): discord.PermissionOverwrite(read_messages=True, send_messages=True) for uid in game_state["opted_in"]}
        }
        name = f"gm{game_id[-2:]}-{continent.lower()}-{codename.lower()}"
        category = discord.utils.get(guild.categories, id=1196228313555927102)
        new_channel = await guild.create_text_channel(name=name, overwrites=overwrites, category=category)

        await interaction.response.send_message(f"Game ID set. Created game channel {new_channel.mention}.")

        coord_channel = guild.get_channel(TEST_CHANNEL_ID)
        mentions = " ".join(f"<@{uid}>" for uid in game_state["opted_in"])
        await coord_channel.send(
            f"✅ Game coordination complete: {new_channel.mention}\n"
            f"Game ID: `{game_id}`\nContinent: `{continent}`\nCodename: `{codename}`\nParticipants: {mentions}"
        )

        game_state["active"] = False

    @app_commands.command(name="cancel_game", description="Cancel the ongoing game coordination.")
    async def cancel_game(self, interaction: discord.Interaction):
        if interaction.user.id != game_state["initiator_id"]:
            await interaction.response.send_message("Only the initiator can cancel the game coordination.", ephemeral=True)
            return

        game_state["active"] = False
        await interaction.response.send_message("❌ Game coordination has been cancelled.")


async def setup():
    await bot.add_cog(Game(bot))
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await setup()

bot.run("YOUR_BOT_TOKEN")
