import discord
from discord.ext import commands, tasks
import json
from yt_dlp import YoutubeDL, utils
import asyncio
import random
import nacl
from discord import FFmpegPCMAudio

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
TOKEN = 'MTA5MTM1MTgwNjE5OTc0NjYxMQ.G34uuF.7pOzDduzvzQ2dOOhGW_MxgwS3m8UFFTCMswma4'
queue = []
voice_channel = None


ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}


try:
    with open('sent_messages.json', 'r') as f:
        sent_messages = json.loads(f.read())
except FileNotFoundError:
    sent_messages = {}

with open('sent_messages.json', 'w') as f:
    f.write(json.dumps(sent_messages))


@bot.event
async def on_ready():

    for guild in bot.guilds:
        print(f'{bot.user.name} успешно подключился к Discord серверу: {guild.name}!')
        channel = discord.utils.get(guild.channels, name='основной')
        if channel and str(guild.id) in sent_messages:
            message = f"Я был успешно перерожден и готов к работе на сервере {guild.name}."
            sent_messages[str(guild.id)] = message
            await channel.send(message)

        elif channel:
            await channel.send(f'`Покажи мне свою мотивацию! \n'
                               f' "?help" для вызова помощи`')

        with open('sent_messages.json', 'w') as f:
            f.write(json.dumps(sent_messages))


ytdl = YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename


@bot.command(name='rand')
async def rand(ctx, *arg):
    await ctx.reply(random.randint(0, 100))


@bot.command(name='add')
async def add(ctx, url):
    queue.append(url)
    await ctx.reply('Добавлено в очередь')
    return


@bot.command(name='join')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f"{ctx.message.author.name} не подключен к голосовому каналу")
        return
    else:
        channel = ctx.message.author.voice.channel
        try:
            voice_client = ctx.message.guild.voice_client
            if voice_client.is_connected():
                await voice_client.disconnect()
        except Exception:
            pass
    await channel.connect()


@bot.command(name='leave')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("Бот не подключен к голосовому каналу")


@bot.command(name='com')
async def com(ctx):
    await ctx.reply('```Список команд: \n !com - вызов меню команд \n !add - добавить песню в очередь \
\n !play - начать воспроизведение очереди \n !stop - остановить воспроизведение \n !pause - поставить на паузу \
\n !res - возобновить песню \n !join - подключить бота к голосовому каналу```')


@bot.command(name='pause')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        voice_client.pause()
    else:
        await ctx.send("Бот не подключен к голосовому каналу")


@bot.command(name='res')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if not voice_client.is_playing():
        voice_client.resume()


@bot.event
async def on_voice_state_update(member, before, after):
    global voice_channel

    if member.id == bot.user.id and after.channel:
        voice_channel = after.channel.name
        print(f"Бот подключен к голосовому каналу: {voice_channel}")


@bot.command(name='stop')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("Бот ничего не играет")


@bot.command(name='queue')
async def queue_show(ctx):
    for i in queue:
        await ctx.send(f'```№{queue.index(i) + 1} \n {queue[queue.index(i)]}```')


@bot.command(name='play')
async def play(ctx, url):
    global queue
    if not ctx.message.guild.voice_client:
        if not ctx.message.author.voice:
            await ctx.send(f"{ctx.message.author.name} не подключен к голосовому каналу")
            return
        else:
            channel = ctx.message.author.voice.channel
            try:
                voice_client = ctx.message.guild.voice_client
                if voice_client.is_connected():
                    await voice_client.disconnect()
            except Exception:
                pass
        await channel.connect()
    queue.append(url)
    await ctx.reply('Добавлено в очередь')
    if voice_channel is not None:
        server = ctx.message.guild
        voice = server.voice_client
        if not voice.is_playing():
            if voice_channel is not None:

                async def playing_recursive():
                    global queue

                    if len(queue) > 0:
                        filename = await YTDLSource.from_url(queue[0], loop=bot.loop)
                        voice.play(FFmpegPCMAudio(executable="ffmpeg.exe", source=filename))
                        await ctx.send(f'Сейчас играет: {queue[0]}')
                        del queue[queue.index(queue[0])]

                        while voice.is_playing():
                            await asyncio.sleep(1)

                        await playing_recursive()

                await playing_recursive()

if __name__ == '__main__':
    bot.run(TOKEN)
