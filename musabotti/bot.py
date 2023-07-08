import os
import hikari
import lightbulb
import lavaplay
import asyncio

bot = lightbulb.BotApp(
    os.environ["TOKEN"],
    default_enabled_guilds=int(os.environ["GUILD_ID"]),
    help_slash_command=True,
    intents=hikari.Intents.ALL,
    logs="INFO"
)

LAVALINK_PASSWORD = os.environ["LAVALINK_PASSWORD"]
# create a lavaplay client
lavalink = lavaplay.Lavalink()

node = lavalink.create_node(
    host="localhost",  # your lavalink host
    port=2333,  # your lavalink port
    password=LAVALINK_PASSWORD,  # your lavalink password
    user_id=0  # Will change later on the started event
)

TEXT_ID = int(os.environ["TEXT_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# the started event is called when the client is ready
@bot.listen(hikari.StartedEvent)
async def started_event(event):
    # change the bot user id
    node.user_id = bot.get_me().id
    # connect the lavaplay client to the hikari client
    node.connect()

async def disconnect_after_timeout(ctx, player):
    time = 0
    while True:
        await asyncio.sleep(1)
        time = time + 1
        if player.is_playing:
            time = 0
        if time == 600: # 600 seconds = 10 minutes
            await bot.update_voice_state(ctx.guild_id, None)
            # destroy the player
            await player.destroy()
            # remove player from node.players
            del node.players[ctx.guild_id]
            await ctx.respond(f"Disconnected from <#{CHANNEL_ID}>")
            print("Disconnected from voice channel with timeout")
            break

#Join voice channel this is called in the play command
async def join(ctx) -> None:
    print("Joining voice channel")
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await ctx.respond("You are not in a voice channel")
        return
    
    # check if the bot is already connected to a voice channel
    if ctx.guild_id in node.players:
        return

    # connect to the voice channel
    channel_id = state.channel_id

     # check if the channel_id is the specified one
    if channel_id != CHANNEL_ID:
        await ctx.respond(f"I am only allowed to join <#{CHANNEL_ID}>")
        return
    
    # create a player for the guild
    player = node.create_player(ctx.guild_id)
    await bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)
    await ctx.respond(f"Connected to <#{channel_id}>")
    print("Joined voice channel")

@bot.command()
@lightbulb.command("disconnect", "Leave from your voice channel")
@lightbulb.implements(lightbulb.SlashCommand)
async def disconnect(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # check if the bot is connected to a voice channel
    if ctx.guild_id not in node.players:
        return
    
    # create a player for the guild
    player = node.create_player(ctx.guild_id)
    await player.destroy()
    await bot.update_voice_state(ctx.guild_id, None)
    # remove player from node.players
    del node.players[ctx.guild_id]
    await ctx.respond(f"Disconnected from <#{CHANNEL_ID}>")

@bot.command()
@lightbulb.option("str", "Youtube URL or name of song", required=True)
@lightbulb.command("play", "Play song from youtube link")
@lightbulb.implements(lightbulb.SlashCommand)
async def play(ctx: lightbulb.SlashContext) -> None:   
    print("Play command called")

    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != TEXT_ID:
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    await join(ctx)
    print("Joined voice channel with play command")

    # get the query from url
    try:
        query = ctx.options.str
    except IndexError:
        await ctx.respond("Please check that your comment follows the format `!play <query>`")
        return
    
    # check if the query is empty
    if not query:
        await ctx.respond("Please provide a track to play")
        return

    # Search for the query
    try:
        result = await node.auto_search_tracks(query)
    except lavaplay.TrackLoadFailed:   # check if not found results
        await ctx.respond("Failed to load the track")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Play the first result
    await player.play(result[0])
    if (len(player.queue) > 1):
        await ctx.respond(f"Added {result[0].title} to the queue")
    else:
        await ctx.respond(f"Playing {result[0].title}")
    
    # Call the function to start the timeout loop
    await disconnect_after_timeout(ctx, player)

@bot.command()
@lightbulb.command("pause", "Pause the current song")
@lightbulb.implements(lightbulb.SlashCommand)
async def pause(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != TEXT_ID:
        return
 
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Pause the player
    await player.pause(True)
    await ctx.respond(f"Paused {player.queue[0].title}")

@bot.command()
@lightbulb.command("resume", "Resume the current song")
@lightbulb.implements(lightbulb.SlashCommand)
async def resume(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != TEXT_ID:
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Resume the player
    await player.pause(False)
    await ctx.respond(f"Resumed {player.queue[0].title}")

@bot.command()
@lightbulb.command("skip", "Skip the current song")
@lightbulb.implements(lightbulb.SlashCommand)
async def skip(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Skip the player
    await player.skip()
    await ctx.respond(f"Skipped {player.queue[0].title}")

@bot.command()
@lightbulb.command("queue", "Show the current queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def queue(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Get the queue
    queue = player.queue

    # Create the queue message
    queue_message = "\n".join([f"{index + 1}. {track.title}" for index, track in enumerate(queue)])

    # Send the queue message
    await ctx.respond(queue_message)

@bot.command()
@lightbulb.command("clear", "Clear the current queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def clear(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Clear the queue
    player.queue.clear()

    # Send the queue message
    await ctx.respond("Cleared the queue")

@bot.command()
@lightbulb.option("int", "Index of the song to remove", required=True)
@lightbulb.command("remove", "Remove a song from the queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def remove(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)
    index = int(ctx.options.int)
    # Remove the song from the queue
    try:
        if (index > 1):
            track = player.queue.pop(index - 1)
            # Send the queue message
            await ctx.respond(f"Removed {track.title}")
    except IndexError:
        await ctx.respond("Invalid index")
        return


@bot.command()
@lightbulb.command("current", "Show the current song")
@lightbulb.implements(lightbulb.SlashCommand)
async def current(ctx: lightbulb.SlashContext) -> None:
    # Ignore messages sent in channels other than the one with id stored in TEXT_ID
    if ctx.channel_id != int(TEXT_ID):
        return
    
    # get the voice channel
    state = bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)

    # check if the author is in a voice channel
    if not state:
        await bot.respond("You are not in a voice channel")
        return

    # Get the player
    player = node.get_player(ctx.guild_id)

    # Get the current song
    current = player.queue[0]

    # Send the current song message
    await ctx.respond(f"Current song is {current.title}")

# the voice_state_update event is called when a user changes voice channel
@bot.listen(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent):
    player = node.get_player(event.guild_id)
    if player is not None:
        # Update the voice state of the player
        await player.raw_voice_state_update(event.state.user_id, event.state.session_id, event.state.channel_id)
    else:
        # Handle the case where player is None
        print(f"Player is None for guild {event.guild_id}")

    # Check if the bot is connected to the voice channel with id stored in CHANNEL_ID
    if not event.state.guild_id or not bot.cache.get_voice_state(event.state.guild_id, bot.get_me().id) or bot.cache.get_voice_state(event.state.guild_id, bot.get_me().id).channel_id != CHANNEL_ID:
        return

    # Get the voice channel that the bot is connected to
    voice_channel = bot.cache.get_guild_channel(bot.cache.get_voice_state(event.state.guild_id, bot.get_me().id).channel_id)

    # Check if the bot is the only member in the voice channel
    if len(bot.cache.get_voice_states_view_for_channel(event.state.guild_id, voice_channel.id)) == 1:
        print("Bot is alone in the voice channel. Disconnecting...")
        # Disconnect the bot from the voice channel and destroy the player
        await player.destroy()
        await bot.update_voice_state(event.state.guild_id, None)
        # remove player from node.players
        del node.players[event.state.guild_id]
        print("Bot disconnected")

# the voice_server_update event is called when a user changes voice channel
@bot.listen(hikari.VoiceServerUpdateEvent)
async def voice_server_update(event: hikari.VoiceServerUpdateEvent):
    player = node.get_player(event.guild_id)
    # Update the voice server information of the player
    await player.raw_voice_server_update(event.raw_endpoint, event.token)

def run():
    bot.run()