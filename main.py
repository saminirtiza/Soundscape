import discord
import os
from keep_alive import keep_alive
from discord.ext import commands

client=commands.Bot(command_prefix='%')

#loading cogs
for fName in os.listdir('./cogs'):
  if fName.endswith('.py'):
    client.load_extension(f"cogs.{fName[:-3]}")
    
#admin check
def is_me(ctx):
  return ctx.author.id==01234567890 #admin discord ID


@client.event
async def on_ready():
  await client.change_presence(status=discord.Status.online,activity=discord.Game('Hide N Skip'))
  print(f"{client.user} says Let's JAM!")
  return

@client.command()
@commands.check(is_me)
async def load(ctx,extension):
  client.load_extension(f"cogs.{extension}")
  await ctx.send("Loaded Successfully")

@client.command()
@commands.check(is_me)
async def unload(ctx,extension):
  client.unload_extension(f"cogs.{extension}")
  await ctx.send("Unloaded Successfully")

@client.command()
@commands.check(is_me)
async def reload(ctx,extension):
  client.unload_extension(f"cogs.{extension}")
  client.load_extension(f"cogs.{extension}")
  await ctx.send("Reloaded Successfully")


keep_alive()
client.run(os.getenv("SCTOK"))