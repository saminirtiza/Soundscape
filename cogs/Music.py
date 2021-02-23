import discord
import subprocess
import shlex
import signal
import asyncio
import nacl
from discord.ext import commands
from discord.utils import get
import os
import ffmpeg
import youtube_dl
from streamlink import Streamlink
import requests
from youtube_dl import YoutubeDL

class Music(commands.Cog):
  def __init__(self,client):
    self.client=client
    self.volume = 0.15
    self.Queue={"title":[],"url":[],"web_url":[],"is_live":[]}
    self.repeat_state='none'
    self.playIdx=0
    self.playspeed=1.0

  @commands.command(aliases=["j"])
  async def join(self,ctx):
      try:
          userChannel = ctx.message.author.voice.channel
      except AttributeError:
          await ctx.send(
              "You have to connect to a voice channel to use this command")
      voice = get(self.client.voice_clients, guild=ctx.guild)
      if voice and voice.is_connected():
          if userChannel is not voice.channel:
              await ctx.send(f"Moved To `{userChannel}`")
              await voice.move_to(userChannel)
              print(f"The bot has connected to {userChannel}")
          else:
              await ctx.send(f"The bot is already in `{userChannel}`")
              print("Attempted to connect in the same voice channel")
      else:
          await ctx.send(f"Joined `{userChannel}`")
          voice = await userChannel.connect()
          if voice.is_connected():
            print(f"The bot has connected to {userChannel}")
      return voice


  @commands.command(aliases=["lv", "dc", "disconnect", "fuckoff","goaway"])
  async def leave(self,ctx):
      try:
          userChannel = ctx.message.author.voice.channel
      except AttributeError:
          await ctx.send(
              "You have to connect to a voice channel to use this command")
      voice = get(self.client.voice_clients, guild=ctx.guild)
      if voice and voice.is_connected():
          await ctx.send(f"Left `{userChannel}`")
          self.playIdx=0
          self.repeat_state='none'
          self.Queue.clear()
          self.Queue={"title":[],"url":[],"web_url":[],"is_live":[]}
          await voice.disconnect()
          print(f"The bot has left {userChannel}")
      else:
          print("The bot was told to leave a voice channel but was not in one")
          await ctx.send("Are you blind? I'm not in a voice channel!!!")
      return


  async def add_Queue(self,ctx,args):
    try:
      ydl_opts = { #setting ytdl options
      'format':'bestaudio/best',
      'noplaylist':'True',
      'extractaudio':'True',
      'audioformat': 'mp3',
      'default_search': 'auto',
      }
      with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            requests.get(args) #parsing url/keywords
        except:
            song_info = ydl.extract_info(f"ytsearch:{args}",
                                        download=False)['entries'][0]
        else:
            song_info = ydl.extract_info(args, download=False)
        song_name = song_info['title']
        self.Queue["title"].append(song_name)
        self.Queue['url'].append(f"{song_info['formats'][0]['url']}")
        self.Queue['web_url'].append(f"{song_info['webpage_url']}")
        self.Queue['is_live'].append(song_info['is_live'])
    except:
      await self.check_next(ctx,self.Queue)
    return self.Queue


  async def check_next(self,ctx,currQ,thrd=None):
    try:
        try:
          thrd.terminate()
        except AttributeError:
          pass
        print(f"{currQ['title'][self.playIdx]} has finished playing")
        if self.repeat_state == 'none':
          currQ['url'].pop(0)
          currQ['title'].pop(0)
          currQ['web_url'].pop(0)
          currQ['is_live'].pop(0)
          if len(currQ['title'])==0:
            return
        elif self.repeat_state == 'queue':
          self.playIdx=(self.playIdx+1)%len(currQ['title'])
        self.Queue=currQ
        voice = get(self.client.voice_clients, guild=ctx.guild)
        beforeArgs = "-seekable 1 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        opt=f"-filter:a 'atempo={self.playspeed}'"
        loop = asyncio.get_event_loop()
        if currQ['is_live'][self.playIdx] is True:
            t1=self.play_live(currQ['web_url'][self.playIdx])
            await ctx.send("You're playing a Livestream. Some features may be inapplicable")
            flist=os.listdir()
            if "output.ts" in flist:
              os.remove("output.ts")
            while True:
              flist=os.listdir()
              if "output.ts" in flist:
                break
            voice.play(discord.FFmpegPCMAudio("output.ts",options="-vn"),after=lambda e: loop.create_task(self.check_next(ctx,currQ,t1)))
            song_name=currQ['title'][self.playIdx]
            print(f"{song_name} is Playing")
            await ctx.send(f"Now Playing **{song_name}**")
            voice.source = discord.PCMVolumeTransformer(voice.source)
            voice.source.volume = self.volume
        else:
            voice.play(discord.FFmpegPCMAudio(currQ['url'][self.playIdx],
            before_options=beforeArgs,options=opt),after=lambda e: loop.create_task(self.check_next(ctx,currQ)))
            song_name=currQ['title'][self.playIdx]
            print(f"{song_name} is Playing")
            await ctx.send(f"Now Playing **{song_name}**")
            voice.source = discord.PCMVolumeTransformer(voice.source)
            voice.source.volume =self.volume
    except youtube_dl.utils.DownloadError:
        await ctx.send("The requested audio is unavailable")
        await self.check_next(ctx,currQ)
    except IndexError:
        print("No more song left in Queue")
    except KeyError:
        print("Queue has stopped and cleared")
    return


  @commands.command(aliases=["cl"])
  async def clear(self,ctx):
      self.Queue.clear()
      self.Queue={"title":[],"url":[],"web_url":[],"is_live":[]}
      await ctx.send("The queue has been cleared")
      return

  @commands.command(aliases=["p"])
  async def play(self,ctx, *, args):
      voice = get(self.client.voice_clients, guild=ctx.guild)
      if not (voice and voice.is_connected()):
          self.volume=0.15
          voice = await self.join(ctx)
      #song is added to the queue
      if voice.is_playing() or voice.is_paused():
        current_queue=await self.add_Queue(ctx,args)
        self.Queue=current_queue
        await ctx.send(f"**{current_queue['title'][-1]}** has been added to the Queue")
        return
      else:
        current_queue=await self.add_Queue(ctx,args)
        try:
            beforeArgs = "-seekable 1 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            loop = asyncio.get_event_loop()
            opt = f"-filter:a 'atempo={self.playspeed}'"
            if current_queue['is_live'][0] is True:
                t1=self.play_live(current_queue['web_url'][0])
                await ctx.send("You're playing a Livestream. Some features may be inapplicable")
                flist=os.listdir()
                if "output.ts" in flist:
                  os.remove("output.ts")
                while True:
                  flist=os.listdir()
                  if "output.ts" in flist:
                    break
                voice.play(discord.FFmpegPCMAudio("output.ts",options="-vn"),after=lambda e: loop.create_task(self.check_next(ctx,current_queue,t1)))
                song_name=current_queue['title'][0]
                print(f"{song_name} is Playing")
                await ctx.send(f"Now Playing **{song_name}**")
                voice.source = discord.PCMVolumeTransformer(voice.source)
                voice.source.volume = self.volume
            else:
                voice.play(discord.FFmpegPCMAudio(current_queue['url'][0],before_options=beforeArgs,options=opt),after=lambda e: loop.create_task(self.check_next(ctx,current_queue)))
                song_name=current_queue['title'][0]
                await ctx.send(f"Now Playing **{song_name}**")
                print(f"{song_name} is Playing")
                voice.source = discord.PCMVolumeTransformer(voice.source)
                voice.source.volume = self.volume
        except youtube_dl.utils.DownloadError:
            await ctx.send("The requested audio is unavailable")
            await self.check_next(ctx,current_queue)
      return

  def play_live(sefl,link):
      command=shlex.split(f"streamlink -f -o output.ts {link} 480p")
      process=subprocess.Popen(command)
      return process
  #Handling Missing URL/keywords error.
  @play.error
  async def clear_error(self,ctx, error):
      if isinstance(error, commands.MissingRequiredArgument):
          await ctx.send("Please Enter a song name/URL with play command")
      else:
        raise error
      return

  @commands.command(aliases=["sp"])
  async def speed(self,ctx,args):
    if float(args)>=0.5 and float(args)<=2.0:
      self.playspeed=float(args)
      await ctx.send(f"Playback speed changed to **{self.playspeed}x**")
    else:
      await ctx.send("Speed can be only in between **0.5x** and **2x**")
    return

  @speed.error
  async def speed_error(self,ctx,error):
    if isinstance(error,ValueError):
      await ctx.send("Speed can be only in between **0.5x** and **2x**")
    else:
      raise error
    return

  @commands.command(aliases=["sk"])
  async def skip(self,ctx):
    voice = get(self.client.voice_clients, guild=ctx.guild)

    if voice and (voice.is_playing() or voice.is_paused()):
        print("Audio skipped")
        await ctx.send(f"**{self.Queue['title'][self.playIdx]}** has been skipped")
        voice.stop()
    else:
        print("No Audio playing failed to stop")
        await ctx.send("No Audio playing failed to stop")
    return
  @skip.error
  async def skip_error(self,ctx,error):
    if isinstance(error,IndexError):
      print("Queue has been cleared before skipping")
      await ctx.send("Queue was cleared before skipping")
    else:
      raise error
    return
    
  @commands.command(aliases=["pa"])
  async def pause(self,ctx):
      voice = get(self.client.voice_clients, guild=ctx.guild)
      if voice and voice.is_playing():
          print("Audio paused")
          voice.pause()
          await ctx.send("Audio paused")
      else:
          print("Audio not playing failed pause")
          await ctx.send("Audio not playing failed pause")
      return


  @commands.command(aliases=["res"])
  async def resume(self,ctx):
      voice = get(self.client.voice_clients, guild=ctx.guild)

      if voice and voice.is_paused():
          print("Resumed Audio")
          voice.resume()
          await ctx.send("Resumed Audio")
      else:
          print("Audio is not paused")
          await ctx.send("Audio is not paused")
      return


  @commands.command(aliases=["st", "s"])
  async def stop(self,ctx):
      voice = get(self.client.voice_clients, guild=ctx.guild)

      if voice and (voice.is_playing() or voice.is_paused()):
          print("Audio stopped")
          self.playIdx=0
          self.Queue.clear()
          self.Queue={"title":[],"url":[],"web_url":[],"is_live":[]}
          voice.stop()
          await ctx.send("Audio stopped and queue has been cleared")
      else:
          print("No Audio playing failed to stop")
          await ctx.send("No Audio playing failed to stop")
      return


  @commands.command()
  async def ping(self,ctx):
      print(f"Latency is: {self.client.latency*1000} ms")
      await ctx.send(f"Pong! **{(self.client.latency*1000):.3f} ms**")
      return


  @commands.command(aliases=["vol", "v"])
  async def volume(self,ctx, vol):
      try:
          userChannel = ctx.message.author.voice.channel
      except AttributeError:
          await ctx.send(
              "You have to connect to a voice channel in order to use this command"
          )
      voice = get(self.client.voice_clients, guild=ctx.guild)
      new_volume = float(voice.source.volume)
      try:
          new_volume = float(vol)
      except ValueError:
          await ctx.send("Enter a value between 1 and 100")
          return
      if new_volume < 1 or new_volume > 100:
          await ctx.send("Enter a value between 1 and 100")
      else:
          if voice and voice.is_connected():
              voice.source.volume = new_volume / 500
              self.volume = float(voice.source.volume)
              await ctx.send(f"New Volume set to **{int(new_volume)}%**")
          else:
              await ctx.send("The bot is not in a voice channel")
      return

  @volume.error
  async def volume_error(self,ctx, error):
      if isinstance(error, AttributeError):
          await ctx.send(
              "Nothing is playing as such, this option is currently unavailable")
      elif isinstance(error, commands.MissingRequiredArgument):
          await ctx.send("No value has been set")
      else:
        raise error
      return

  @commands.command(aliases=["re","loop"])
  async def repeat(self,ctx,args):
    if args == 'none':
      self.repeat_state='none'
      await ctx.send("Repeat has been set to **none**")
    elif args == 'one':
      self.repeat_state='one'
      await ctx.send("Repeat has been set to **one**")
    elif args == 'queue':
      self.repeat_state='queue'
      await ctx.send("Repeat has been set to **queue**")
    else:
      await ctx.send("Value can only be **none**,**one** or **queue**")
  @repeat.error
  async def repeat_error(self,ctx,error):
    if isinstance(error,commands.MissingRequiredArgument):
      await ctx.send("Value can only be **none**,**one** or **queue**")
    else:
      raise error
    return

  @commands.command(aliases=["q"])
  async def queue(self,ctx):

    try:
      string=f"Now Playing Track No. **{self.playIdx+1}.** __**[{self.Queue['title'][self.playIdx]}]({self.Queue['web_url'][self.playIdx]})**__\n"
      for i in range(0,len(self.Queue['title'])):
        if i != self.playIdx:
          string+=f"**{i+1}.** __**[{self.Queue['title'][i]}]({self.Queue['web_url'][i]})**__\n"

      if len(string) != 0:
        emb=discord.Embed(title="Tracks Currently in Queue:",
        description=string,
        colour=discord.Colour.blue())
        await ctx.send(embed=emb)
      else:
        await ctx.send("No track left in Queue")
    except IndexError:
      print("Queue was empty")
      await ctx.send("Queue is empty")
    return


  @commands.command(aliases=["rm"])
  async def remove(self,ctx,args: int):
    if type(args) is int and args<=len(self.Queue['title']):
      await ctx.send(f"**{self.Queue['title'][args-1]}** has been removed")
      self.Queue['title'].pop(args-1)
      self.Queue['url'].pop(args-1)
    else:
      await ctx.send("Please put a valid value")
    return
  @remove.error
  async def remove_error(self,ctx,error):
    if isinstance(error,discord.ext.commands.errors.BadArgument):
      await ctx.send("Please put a valid value")
    else:
      raise error
    return

def setup(client):
  client.add_cog(Music(client))
  return