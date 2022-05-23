import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import discord.utils
import json
from keep_alive import keep_alive
import os
from dotenv import load_dotenv
import datetime
import time
import youtube_dl
import urllib.request
import re
import requests
import random
import asyncio
from functools import partial

#music player
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    #'download': False,
    'source_address':
    '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {'options': '-vn'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)


queue = {}
players = {}


# Bad word class
class BadWord:
    def __init__(self, name, wordList, responses):
        self.name = name
        self.wordList = wordList
        self.responses = responses


# Bad word lists
bad_words = [
    BadWord("N word", [
        "neger", "negro", "neeger", "nigger", "nigga", "黑鬼", "hei gui"
    ], [
        "Orh hor say N word I tell mummy",
        "Orh hor say N word u naughty naughty u teasing me",
        "Nigger, a contemptuous term for a black or dark-skinned person. Nigger is an infamous word in current English, so much so that when people are called upon to discuss it, they more often than not refer to it euphemistically as \"the N-word.\" In senses 1 and 2, the word ranks as almost certainly the most offensive and inflammatory racial slur in English, a term expressive of hatred and bigotry. Sense 3 is also now rarely used and is often considered offensive. The word's self-referential uses by and among Black people are not always intended or taken as offensive (although many object to those uses as well), but its use by a person who is not Black to refer to a Black person can only be regarded as a deliberate expression of contemptuous racism. First known use of the word \"Nigger\" you may ask. The answer? 1755",
        "Black people might sometimes address other of their black friends, \"My Nigger!\"",
        "This word is often derogatory and Whites are banned from using that word. The reason for this is that the history of the word \"Nigger\" dates back to when Blacks were still used as slaves and people would not treat them like normal human beings and call them \"Negro\".",
        "In the 1800s, there were human zoos showcasing black people (Niggers!)",
        "NIGGGAAAAAAAAAAAAAAAAAAAAAA"
    ]),
    BadWord("F word", ["fuck", "fucking", "fucker"], [
        "Orh hor say F word I tell mummy",
        "Orh hor say F word u naughty naughty u teasing me",
    ]),
    BadWord("Chink word", ["chink", "cheenk", "ching"], [
        "Chink, a English-language ethnic slur usually referring to a person of Chinese descent.",
        "A chink is usually defined from the person's facial appearance, such as having small eyes. (Aidan)",
        'The word that u have just used (Chink), is thought to have originated from ancient China as the Qing dynasty is sometimes pronounced as "Chink" in America',
        'When I came to the U.S. as an adopted child from Vietnam (Bill). I was playing on a swing set  when a kid my age walked out of his house and came up to me and said, "Hey chink, get off the swing I want to use it."  I didn\'t know what the word meant and went home and looked it up in the dictionary. [Definition of CHINK] : a narrow beam of light shining through a hole of a wall or building. I laughed so hard until my good friend Tyron Jamal Jones James Johnson explained to me that it means the same as the N word people applied to him. We both went back the next day and kicked the living racist "chink" out of his loathsome armor. "Words have many meanings, but hate has only one intention, to cut at a person\'s self worth so the user of that word can feel a false sense of worth."',
    ]),
    BadWord("Pinoy word", ["pinoy"], [
        "Pinoy more like penis (kidding)",
        "Pinoy, a person of Filipino origin or descent used with sometimes no negative connotations unlike Nigger or Chink. Pinoy is usually used referring to a Toxic Valorant Player who speaks in noodle language that baits the entire team and screams at them for not entrying, what's worse is that he uses a fork to eat mac n cheese on a plate!",
        "OI PINOYS STOP YELLING AND PLAYING VALORANT LAH U NO LIFER EAT ASS NOODLE LANGUAGE SPEAKING ASS, jk please dont sue me"
    ]),
    BadWord("Fat word",
            ["royce", "fat", "obese", "chunky", "thorston", "kamal"], [
                "little fat fuck", "royce kinda gay", "i love physics",
                "asian leaksss", "omg kamal yacob hehehehehehehor",
                "i hate tryhards LAZY EYE"
            ]),
    BadWord("Tryhard", ["tryhard", "aidan", "bill", "min qi", "minqi", "4a1"],
            [
                "eww tryhard go and study medicine lah",
                "tryhard.exe",
            ]),
    BadWord("Liverpool", ["lfc", "liverpool", "scouse", "scouser"], [
        "allez allez allez", "premier league champions 2021/22",
        "corner taken quickly ORIGIII", "mo salad"
    ])
]


#bot init and prefixes
def get_prefix(client, ctx):
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    return prefixes[str(ctx.guild.id)]


intents = discord.Intents.all()
client = commands.Bot(command_prefix=get_prefix, intents=intents)
client.remove_command('help')


@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online,
                                 activity=discord.Game('bhelp'))
    print('Bot is ready')


@client.event
async def on_guild_join(guild):
    with open('prefixes.json', 'r') as f:
        prefix = json.load(f)

    prefix[str(guild.id)] = 'b'

    with open('prefixes.json', 'w') as f:
        json.dump(prefix, f, indent=4)


@client.event
async def on_guild_remove(guild):
    with open('prefixes.json', 'r') as f:
        prefix = json.load(f)

    prefix.pop(str(guild.id))


@client.event
async def on_member_join(member):
    channel = client.get_channel(792718122226417704)
    id = f"<@{member.id}>"
    await channel.send("Welcome to the BaldSMP, %s" % id)
    role = discord.utils.get(member.guild.roles, name="Bald")
    await member.add_roles(role)


# Bad word count
@client.event
async def on_message(message):
    if message.author.bot:
        return

    with open("word_count.json", "r") as f:
        data = json.load(f)
        f.close()

    msg = message.content.lower()
    for swear in bad_words:
        for bad_word in swear.wordList:
            if bad_word in msg:
                try:
                    data[swear.name] += 1
                except KeyError:
                    data[swear.name] = 1

                await message.channel.send(random.choice(swear.responses))
                time.sleep(1)
                await message.channel.send(swear.name + " count: " + str(data[swear.name]))

    with open("word_count.json", "w") as f:
        json.dump(data)
        f.close()

    await client.process_commands(message)


#commands
@client.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency: **{round(client.latency * 1000)}**ms')


@client.command()
async def help(ctx):
    embed = discord.Embed(title="Help", color=0x00ffb7)
    embed.set_thumbnail(
        url=
        "https://cdn.discordapp.com/attachments/791588775456800802/792709248349503488/20201224_171052.jpg"
    )
    embed.set_footer(text=f"Requested by: {ctx.message.author.name}",
                     icon_url=f"{ctx.message.author.avatar_url}")
    embed.add_field(name="sourceCode:",
                    value="Sends the link of the source code.",
                    inline=False)
    embed.add_field(name="ping:",
                    value="Returns the latency of the bot.",
                    inline=False)
    embed.add_field(name="time:",
                    value="Gets the time you have spent in this server.",
                    inline=False)
    embed.add_field(name="getBaldRole:",
                    value="Work in progress.",
                    inline=False)
    await ctx.send(embed=embed)


@client.command(aliases=["time"])
async def getTimeInServer(ctx, member: discord.Member = None):
    if member is None:
        user = ctx.message.author.joined_at
    else:
        user = member.joined_at
    daysInServer = await getDaysInServer(user)
    await ctx.send(f"Days in server: **{daysInServer}**")


@client.command()
async def getBaldRole(ctx):
    user = ctx.message.author.joined_at
    daysInServer = getDaysInServer(user)
    if daysInServer >= 5:
        pass
    else:
        pass


@client.command(aliases=["sourcecode", "sc"])
async def sourceCode(ctx):
    await ctx.send("Source code: https://github.com/EpikStuff/BaldBot")


@client.command(aliases=["bal"])
async def balance(ctx):
    await checkBankAcc(str(ctx.message.author.id))
    with open('data.json', 'r') as f:
        data = json.load(f)
    for x in data[str(ctx.message.author.id)]:
        walletBal = x['wallet']
        bankBal = x['bank']
    embed = discord.Embed(title=f"{ctx.message.author.name}'s Account Balance",
                          color=0x66ff00)
    embed.set_thumbnail(url=ctx.message.author.avatar_url)
    embed.set_footer(text=f"Bank balance of: {ctx.message.author.name}")
    embed.add_field(name="Bank:", value=str(bankBal), inline=False)
    embed.add_field(name="Wallet:", value=str(walletBal), inline=False)
    await ctx.send(embed=embed)


@client.command(aliases=["dep"])
async def deposit(ctx, *, amt):
    user = ctx.message.author
    await checkBankAcc(str(user.id))

    if str(amt) == "all":
        with open("data.json", "r") as f:
            data = json.load(f)
        for x in data[str(user.id)]:
            if x["wallet"] == 0:
                await ctx.send(":x:How am I supposed to deposit **0** bucks?")
                break
            else:
                x["bank"] += x["wallet"]
                await ctx.send(
                    f':white_check_mark: {x["wallet"]}<:emerald:793835417471418368> deposited in bank!'
                )
                x["wallet"] = 0
        with open("data.json", "w") as f:
            json.dump(data, f, indent=4)
    else:
        try:
            amt = int(amt)
            with open("data.json", "r") as f:
                data = json.load(f)
            for x in data[str(user.id)]:

                if amt > x["wallet"]:
                    await ctx.send(":x:You have not enough kash u broke guy")
                elif amt == 0:
                    await ctx.send(
                        ":x:How am I supposed to deposit **0** bucks?")
                else:
                    x["wallet"] -= amt
                    x["bank"] += amt
                    with open("data.json", "w") as f:
                        json.dump(data, f, indent=4)
                    await ctx.send(
                        f":white_check_mark: {amt}<:emerald:793835417471418368> deposited in bank!"
                    )
        except:
            await ctx.send(":x:You have to provide a number you dimwit")


@client.command(aliases=["with"])
async def withdraw(ctx, *, amt):
    user = ctx.message.author
    await checkBankAcc(str(user.id))

    if str(amt) == "all":
        with open("data.json", "r") as f:
            data = json.load(f)
        for x in data[str(user.id)]:
            if x["bank"] == 0:
                await ctx.send(":x:How am I supposed to withdraw **0** bucks?")
                break
            else:
                x["wallet"] += x["bank"]
                await ctx.send(
                    f':white_check_mark: {x["bank"]}<:emerald:793835417471418368> withdrawn into wallet!'
                )
                x["bank"] = 0
        with open("data.json", "w") as f:
            json.dump(data, f, indent=4)
    else:
        try:
            amt = int(amt)
            with open("data.json", "r") as f:
                data = json.load(f)
            for x in data[str(user.id)]:

                if amt > x["bank"]:
                    await ctx.send(":x:You have not enough cash u broke guy")
                elif amt == 0:
                    await ctx.send(
                        ":x:How am I supposed to withdraw **0** bucks?")
                else:
                    x["bank"] -= amt
                    x["wallet"] += amt
                    with open("data.json", "w") as f:
                        json.dump(data, f, indent=4)
                    await ctx.send(
                        f":white_check_mark: {amt}<:emerald:793835417471418368> withdrawn into wallet!"
                    )
        except:
            await ctx.send(":x:You have to provide a number you dimwit")


@client.command()
async def debug(ctx):
    await ctx.send("ur mom")


@client.command()
async def joined(ctx):
    duration = datetime.datetime.now() - ctx

    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    await ctx.send(f"Joined {days}days ago")


@client.command(aliases=['purge'], pass_context=True)
@has_permissions(manage_messages=True)
async def clear(ctx, amount=1):
    await ctx.channel.purge(limit=amount + 1)


@client.command()
async def join(ctx):
    if ctx.message.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
        queue[str(ctx.guild.id)] = []
        embed = discord.Embed(
            title=f'Successfully joined: **{str(channel.name)}**',
            color=0x00FF00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title='You must be in a voice channel to use this command!',
            color=0xFF0000)
        await ctx.send(embed=embed)


@client.command(aliases=['stop'])
async def leave(ctx):
    global queue
    try:
        voice_client = ctx.message.guild.voice_client
        await voice_client.disconnect()
        queue[str(ctx.guild.id)] = []
        embed = discord.Embed(
            title=
            f'Disconnected from **{str(ctx.message.author.voice.channel.name)}**',
            color=0x00FF00)
        await ctx.send(embed=embed)
    except:
        embed = discord.Embed(title='Bot was not in a voice channel!',
                              color=0xFF0000)
        await ctx.send(embed=embed)


@client.command()
async def play(ctx, *, search):
    global players, queue
    if ctx.message.author.voice and not ctx.message.guild.voice_client:
        await join(ctx)

    elif ctx.message.author.voice == None:
        embed = discord.Embed(
            title='You must be in a voice channel to use this command!',
            color=0xFF0000)
        await ctx.send(embed=embed)
        return None

    server = ctx.message.guild
    voice_channel = server.voice_client

    if not voice_channel.is_playing():
        try:
            async with ctx.typing():
                url = await getUrlFromQuery(search)
                player = await YTDLSource.from_url(url,
                                                   loop=client.loop,
                                                   stream=True)
                players[server.id] = player
                voice_channel.play(player,
                                   after=partial(checkPlaylist, ctx,
                                                 ctx.guild.id))
                await ctx.send(
                    f':white_check_mark: Now playing: **{player.title}**')
        except Exception as e:  #ClientException:
            await ctx.send(f':x: Error while playing audio\nError: {e}')
    elif voice_channel.is_playing():
        async with ctx.typing():
            url = await getUrlFromQuery(search)
            player = await YTDLSource.from_url(url, loop=client.loop)
            queue[str(ctx.guild.id)].append(search)
            await ctx.send(
                f':white_check_mark: **{player.title}** added to queue.')


@client.command()
async def skip(ctx):
    global queue
    voice_channel = ctx.message.guild.voice_client
    if not ctx.message.author.voice:
        await ctx.send(':x: You are not in a voice channel >:(')
    elif voice_channel == None:
        await ctx.send(':x: I\'m not in a vc :|')
    if not voice_channel.is_playing():
        await ctx.send(
            f':x: There is no music playing in **{ctx.message.author.voice.channel.name}** you dimwit.'
        )
    elif voice_channel.is_playing():
        voice_channel.stop()
        if len(queue[str(ctx.guild.id)]) > 1:
            await play(ctx, search=queue[str(ctx.guild.id)].pop(0))
        else:
            pass


@client.command(aliases=['challengeAns'])
async def kahootChallengeAnswers(ctx, link=None):
    if link == None:
        await ctx.send(':x: Usage: bkahootChallengeAnswers {challenge link}')
        return None
    challengeId = link.split('/')[-1]
    r = requests.get(
        f'https://kahoot.it/rest/challenges/{challengeId}?includeKahoot=true')
    data = r.json()
    if 'error' in data:
        await ctx.send(':x: Could not find quiz ID.')
        return None
    await ctx.send(
        f':white_check_mark: Quiz Found\nQuiz Name: **{data["title"]}**\nAnswers:'
    )
    for i in range(len(data['kahoot']['questions'])):
        for j in data['kahoot']['questions'][i]['choices']:
            if j['correct']:
                await ctx.send(str(i + 1) + ': ' + j['answer'])


async def getUrlFromQuery(query):
    if "https://youtube.com" in query:
        target = query
    else:
        query = query.replace(" ", "+")
        html = urllib.request.urlopen(
            "https://www.youtube.com/results?search_query=" + query)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        target = video_ids[0]
        target = "https://www.youtube.com/watch?v=" + target
    return target


async def checkBankAcc(user):
    with open("data.json", "r") as f:
        data = f.read()

    if user not in data:
        await openAcc(user)
    else:
        return True


async def openAcc(user):
    with open("data.json", "r") as f:
        data = json.load(f)
    data[user] = []
    data[user].append({'wallet': 500, 'bank': 0})
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)


async def getDaysInServer(user):
    duration = datetime.datetime.now() - user

    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    return days


def checkPlaylist(ctx, id, tmp):
    global queue
    lst = queue[str(id)]
    if len(lst) == 0:
        return 0
    else:
        asyncio.run_coroutine_threadsafe(
            play(ctx=ctx, search=queue[str(id)].pop(0), loop=client.loop))


#random connec stuff
keep_alive()
load_dotenv()
client.run(os.getenv('DISCORD_TOKEN'))
