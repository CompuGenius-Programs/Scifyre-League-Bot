import os

import discord
import emoji
import youtube_dl
from dotenv import load_dotenv

load_dotenv()
bot = discord.Bot(intents=discord.Intents.all())

chat_channel = 698961123097051181
music_channel = 776824386950397992
log_channel = 727334906333626369
bot_channel = 776827982332297216
welcome_channel = 698961469848682538

server = 698961122513911848

music_messages = []
header_messages = []
playing_messages = []

songs = {}

ffmpeg_options = {'options': '-vn'}
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                       'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False,
                       'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto',
                       'source_address': '0.0.0.0'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.25):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url):
        data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))

        if 'entries' in data:
            data = data['entries'][0]

        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


async def play(react_msg, emoji_name, voice_client):
    if voice_client is None:
        await bot.get_channel(music_channel).connect()

    url = songs[emoji_name]["url"]

    async with bot.get_channel(bot_channel).typing():
        player = await YTDLSource.from_url(url)
        voice_client.play(player, after=lambda e: bot.loop.create_task(handle_done_playing(react_msg, voice_client)))

    msg = await bot.get_channel(bot_channel).send("**Playing now:** *%s*" % url)
    playing_messages.append(msg)


async def prepare_player(member):
    bot_text_channel = bot.get_channel(bot_channel)

    display_titles = []

    for song in songs:
        display_titles.append("%s - %s" % (emoji.emojize(song), songs[song]["title"]))

    description = '''
    What soundtrack would you like to play?
    %s
    ''' % '\n'.join(display_titles)

    embed = create_embed(title="Scifyre League Soundtracks", description=description, color=discord.Color.green(),
                         footer="All soundtracks are under the copyright of CompuGenius Programs.",
                         url="https://www.youtube.com/channel/UCW7RfG26VQTchAmw_fgMV9g")

    head_msg = await bot_text_channel.send("<@%s>, please select a track below:" % member.id)
    msg = await bot_text_channel.send(embed=embed)

    for song in songs:
        await msg.add_reaction(emoji.emojize(song))
    await msg.add_reaction(emoji.emojize(":cross_mark:"))

    header_messages.append(head_msg)
    music_messages.append(msg)


async def handle_done_playing(react_msg, voice_client):
    if voice_client.is_connected():
        for message in playing_messages:
            await message.delete()
        playing_messages.clear()

        await react_msg.clear_reactions()

        for song in songs:
            await react_msg.add_reaction(emoji.emojize(song))
        await react_msg.add_reaction(emoji.emojize(":cross_mark:"))


@bot.event
async def on_member_join(member):
    description = '''
    Welcome %s to the %s server!
    Please make sure to check out <#%d>.
    Enjoy your stay!
    ''' % (member.mention, bot.get_guild(server).name, welcome_channel)

    embed = create_embed(title="Welcome %s!" % member.display_name, description=description, color=discord.Color.blue(),
                         footer="© CompuGenius Programs. All rights reserved.", image=member.avatar_url)
    await bot.get_channel(chat_channel).send(embed=embed)


@bot.event
async def on_reaction_add(reaction, user):
    emoji_name = emoji.demojize(reaction.emoji)

    react_msg = reaction.message

    if not user.bot:
        if react_msg in music_messages:
            voice_client = discord.utils.get(bot.voice_clients, guild=bot.get_guild(server))
            if emoji_name in songs:
                await play(react_msg, emoji_name, voice_client)
            elif emoji_name == ":cross_mark:":
                await voice_client.disconnect(force=True)
                await user.move_to(None)
                for message in header_messages + playing_messages:
                    await message.delete()
                playing_messages.clear()
                header_messages.clear()

                await react_msg.delete()


@bot.event
async def on_voice_state_update(member, _, after):
    music_voice_channel = bot.get_channel(music_channel)
    voice_client = discord.utils.get(bot.voice_clients, guild=bot.get_guild(server))
    if not member.bot:
        if after.channel == music_voice_channel:
            if voice_client is None:
                await music_voice_channel.connect()

                await prepare_player(member)

    if len(music_voice_channel.members) <= 1:
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect(force=True)
            for message in header_messages + music_messages + playing_messages:
                await message.delete()
            playing_messages.clear()
            header_messages.clear()
            music_messages.clear()


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Scifyre League"))


def create_embed(title, description, color, footer, image="", *, url="", author="", author_url=""):
    embed = discord.Embed(title=title, description=description, url=url, color=color)
    embed.set_footer(text=footer)
    embed.set_thumbnail(url=image)
    embed.set_author(name=author, url=author_url)
    return embed


token = os.getenv("TOKEN")
bot.run()
