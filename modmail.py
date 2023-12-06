import discord
from discord.ext import commands
import bleach
import datetime
import os
import textwrap
import io
import contextlib
import traceback
import json
import mimetypes
import sys
import functools
import dataclasses
import sqlite3
import aiohttp


class YesNoButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, *args):
        self.value = True
        self.stop()

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def no(self, *args):
        self.value = False
        self.stop()


class HelpCommand(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__(command_attrs={'checks': [is_helper]})
        self.no_category = 'Commands'
        self.width = 100

    def get_ending_note(self) -> str:
        return f'Type {config.prefix}help command for more info on a command.'


@dataclasses.dataclass
class Config:
    token: str
    guild_id: int
    category_id: int
    log_channel_id: int
    helper_role_id: int
    mod_role_id: int
    bot_owner_id: int
    prefix: str
    open_message: str
    close_message: str
    anonymous_tickets: bool

    def update(self, new: dict):
        for key, value in new.items():
            setattr(self, key, value)


with open('config.json', 'r') as config_file:
    config = Config(**json.load(config_file))

try:
    with open('snippets.json', 'r') as snippets_file:
        snippets = json.load(snippets_file)
except FileNotFoundError:
    snippets = {}
    with open('snippets.json', 'w') as snippets_file:
        json.dump(snippets, snippets_file)

try:
    with open('blacklist.json', 'r') as blacklist_file:
        blacklist_list = json.load(blacklist_file)
except FileNotFoundError:
    blacklist = []
    with open('blacklist.json', 'w') as blacklist_file:
        json.dump(blacklist, blacklist_file)

try:
    with open('counter.txt', 'r') as counter_file:
        counter = int(counter_file.read())
except FileNotFoundError:
    with open('counter.txt', 'w') as counter_file:
        counter_file.write('0')
        counter = 0

with sqlite3.connect('logs.db') as connection:
    cursor = connection.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS logs (user_id, timestamp, txt_log_url, htm_log_url)')
    connection.commit()


html_sanitiser = bleach.sanitizer.Cleaner()
html_linkifier = bleach.sanitizer.Cleaner(filters=[functools.partial(bleach.linkifier.LinkifyFilter, callbacks=[])])

tickets = {}


async def load_tickets():
    category = bot.get_channel(config.category_id)
    tickets.clear()
    for channel in category.text_channels:
        if channel.topic is not None:
            try:
                tickets[int(channel.topic.split()[0])] = channel.id
            except ValueError:
                await channel.send(embed=embed_creator('Ticket is Broken', f"Please change this channel's topic to the user's ID, then use `{config.prefix}refresh`", 'e'))


def embed_creator(title, message, colour=None, subject=None, author=None, anon=True, time=False):
    embed = discord.Embed()
    embed.title = title
    embed.description = message
    if author is not None:
        if anon:
            embed.set_author(name=f'{author.name} (Anonymous)', icon_url=author.display_avatar.url)
        else:
            embed.set_author(name=author.name, icon_url=author.display_avatar.url)
    if subject is not None:
        if isinstance(subject, discord.User):
            embed.set_footer(text=f'{subject.name}', icon_url=subject.display_avatar.url)
        elif isinstance(subject, discord.Guild):
            embed.set_footer(text=f'{subject.name}', icon_url=subject.icon)
    match colour:
        case 'r':
            embed.colour = discord.Colour(0xed581f)
            time = True
        case 'g':
            embed.colour = discord.Colour(0x6ff943)
            time = True
        case 'b':
            embed.colour = discord.Colour(0x458ef9)
        case 'e':
            embed.colour = discord.Colour(0xf03c1c)
    if time:
        embed.timestamp = datetime.datetime.now()
    return embed


def is_helper(ctx):
    return ctx.guild is not None and ctx.author.top_role >= ctx.guild.get_role(config.helper_role_id)


def is_mod(ctx):
    return ctx.guild is not None and ctx.author.top_role >= ctx.guild.get_role(config.mod_role_id)


def is_modmail_channel(ctx):
    return isinstance(ctx.channel, discord.TextChannel) and ctx.channel.category.id == config.category_id and ctx.channel.topic


bot = commands.Bot(command_prefix=config.prefix, intents=discord.Intents.all(), activity=discord.Game('DM to Contact Mods'),
                   help_command=HelpCommand())


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    print(f'{bot.user.name} has connected to Discord!')
    await load_tickets()


async def error_handler(error, message=None):

    if isinstance(error, commands.CommandInvokeError):
        error = error.original

    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        try:
            await message.channel.send(embed=embed_creator('', f'Missing required argument: `{str(error.param).split(":", 1)[0]}`', 'e'))
        except:
            pass
        return
    if isinstance(error, commands.UserNotFound):
        try:
            await message.channel.send(embed=embed_creator('', f'User `{error.argument}` not found.', 'e'))
        except:
            pass
        return

    if isinstance(error, discord.HTTPException) and 'Maximum number of channels in category reached' in error.text:
        try:
            await message.channel.send(embed=embed_creator('Failed to Send', f'Sorry, {bot.user.name}\'s inbox is currently full. Please try again later or DM a mod if your problem is urgent.', 'e', bot.get_guild(config.guild_id)))
            return
        except:
            pass

    try:
        await message.channel.send(embed=embed_creator(error.__class__.__name__, str(error), 'e'))
    except:
        pass

    if isinstance(error, commands.UserInputError):
        return

    if message is not None:
        embed = embed_creator('Message', message.content, time=True)
        embed.add_field(name='Link', value=message.jump_url)
        embed.add_field(name='Author', value=f'{message.author} ({message.author.id})', inline=False)
    else:
        embed = None

    tb = "".join(traceback.format_exception(error))
    if len(tb) > 2000:
        with open('error.txt', 'w') as tb_file:
            tb_file.write(tb)
        await bot.get_user(config.bot_owner_id).send(file=discord.File(io.BytesIO(tb.encode('utf-8')), filename='error.txt'), embed=embed)
    else:
        await bot.get_user(config.bot_owner_id).send(f'```py\n{tb}```', embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    if event == 'on_message':
        await error_handler(sys.exc_info()[1], args[0])
    else:
        await error_handler(sys.exc_info()[1])


@bot.event
async def on_command_error(ctx, error):
    await error_handler(error, ctx.message)


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.content and len(message.stickers) >= 1:
        return

    await bot.process_commands(message)

    # Message from user to mod.
    if message.guild is None:

        if message.author.id in blacklist_list:
            return

        guild = bot.get_guild(config.guild_id)
        ticket_id = tickets.get(message.author.id)
        if ticket_id == 0:
            return
        ticket_create = False
        if ticket_id is None:
            ticket_create = True
            tickets[message.author.id] = 0
            try:
                if config.anonymous_tickets:
                    global counter
                    ticket_name = f'ticket {str(counter).rjust(4, "0")}'
                    counter += 1
                    if counter == 10000:
                        counter = 0
                    with open('counter.txt', 'w') as file:
                        file.write(str(counter))
                else:
                    ticket_name = f'{message.author.name}'
                channel = await guild.create_text_channel(ticket_name, category=bot.get_channel(config.category_id),
                                                          topic=f'{message.author.id} (User ID, do not change)')
            except discord.HTTPException as e:
                del tickets[message.author.id]
                if 'Contains words not allowed for servers in Server Discovery' in e.text:
                    channel = await guild.create_text_channel('ticket', category=bot.get_channel(config.category_id),
                                                              topic=f'{message.author.id} (User ID, do not change)')
                else:
                    raise e from None
            await bot.get_channel(config.log_channel_id).send(embed=embed_creator('New Ticket', '', 'g', message.author))
            embed = embed_creator('New Ticket',
                                  f'Replies are anonymous by default, and messages starting with `{config.prefix}` are ignored (although using the discussion thread is preferable). Use `{config.prefix}reply` to send a non-anonymous reply. Use `{config.prefix}close` to close anonymously.',
                                  'b', message.author, time=True)
            embed.add_field(name='User', value=f'{message.author.mention} ({message.author.id})')
            header = await channel.send(embed=embed)
            if 'SEVEN_DAY_THREAD_ARCHIVE' in guild.features:
                duration = 10080
            elif 'THREE_DAY_THREAD_ARCHIVE' in guild.features:
                duration = 4320
            else:
                duration = 1440
            await header.create_thread(name=f'Discussion for {message.author.name}',
                                       auto_archive_duration=duration)
            tickets[message.author.id] = channel.id
        else:
            channel = bot.get_channel(ticket_id)
            if channel is None:
                del tickets[message.author.id]
                await on_message(message)
                return

        confirmation_message = await message.channel.send(embed=embed_creator('Sending Message...', '', 'g', guild))
        ticket_embed = embed_creator('Message Received', message.content, 'g', message.author)
        user_embed = embed_creator('Message Sent', message.content, 'g', guild)
        files = []
        n = 0
        if message.attachments:
            await confirmation_message.edit(embed=embed_creator('Sending Message...', 'This may take a few minutes.', 'g', guild))
            for attachment in message.attachments:
                if attachment.size <= guild.filesize_limit:
                    files.append(await attachment.to_file())
                n += 1
                ticket_embed.add_field(name=f'Attachment {n}', value=attachment.url, inline=False)
            user_embed.add_field(name='Attachment(s) Sent Successfully', value=len(message.attachments))
        await channel.send(embed=ticket_embed, files=files)
        await confirmation_message.edit(embed=user_embed)
        if ticket_create:
            await message.channel.send(embed=embed_creator('Ticket Created', config.open_message, 'b', guild))

    # Message from mod to user.
    elif is_modmail_channel(message) and not (len(message.content) > 0 and message.content.startswith(config.prefix)):

        user_id = message.channel.topic.split()[0]
        try:
            user_id = int(user_id)
        except ValueError:
            await message.channel.send(embed=embed_creator('Failed to Send', f"User ID retrieved from channel topic as `{user_id}`. This is not a valid ID, please change the channel's topic to just the user's ID, then use `{config.prefix}refresh`", 'e'))
            return
        user = bot.get_user(user_id)
        if user is not None:
            if message.guild not in user.mutual_guilds:
                await message.channel.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
                return
        else:
            try:
                await bot.fetch_user(user_id)
            except discord.NotFound:
                await message.channel.send(embed=embed_creator('Failed to Send', f"User with ID retrieved from channel topic, `{user_id}`, not found. Try changing the channel's topic to just the user's ID, then use `{config.prefix}refresh`. Otherwise, the user may have deleted their account.", 'e'))
            else:
                await message.channel.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
            return

        channel_embed = embed_creator('Message Sent', message.content, 'r', user, message.author)
        user_embed = embed_creator('Message Received', message.content, 'r', message.guild)
        files = []
        files_to_send = []
        for attachment in message.attachments:
            if attachment.size > 8000000:
                await message.channel.send(embed=embed_creator('Failed to Send', 'One or more attachments are larger than 8 MB.', 'e'))
                return
            file = io.BytesIO(await attachment.read())
            file.seek(0)
            files.append((file, attachment.filename))
            files_to_send.append(discord.File(file, attachment.filename))
        try:
            user_message = await user.send(embed=user_embed, files=files_to_send)
        except discord.Forbidden:
            await message.channel.send(embed=embed_creator('Failed to Send', f'User has server DMs disabled or has blocked {bot.user.name}.', 'e'))
            return
        for index, attachment in enumerate(user_message.attachments):
            channel_embed.add_field(name=f'Attachment {index + 1}', value=attachment.url, inline=False)
        await message.delete()
        # Must be rebuilt because a discord.File object can only be used once.
        files_to_send = []
        for file in files:
            file[0].seek(0)
            files_to_send.append(discord.File(file[0], file[1]))
        await message.channel.send(embed=channel_embed, files=files_to_send)


@bot.command()
@commands.check(is_helper)
async def reply(ctx, *, message: str = ''):
    """Sends a non-anonymous message"""

    if not is_modmail_channel(ctx):
        await ctx.send(embed=embed_creator('', 'This channel is not a ticket.', 'e'))
        return

    user_id = ctx.channel.topic.split()[0]
    try:
        user_id = int(user_id)
    except ValueError:
        await ctx.send(embed=embed_creator('Failed to Send', f"User ID found from channel topic: `{user_id}`. This is not a valid ID, please change the channel's topic to just the user's ID, then use `{config.prefix}refresh`", 'e'))
        return
    user = bot.get_user(user_id)
    if user is not None:
        if ctx.guild not in user.mutual_guilds:
            await ctx.channel.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
            return
    else:
        try:
            await bot.fetch_user(user_id)
        except discord.NotFound:
            await ctx.channel.send(embed=embed_creator('Failed to Send', f"User with ID from channel topic, `{user_id}`, not found. Try changing the channel's topic to just the user's ID, then use `{config.prefix}refresh`. Otherwise, the user have may deleted their account.", 'e'))
        else:
            await ctx.channel.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
        return

    channel_embed = embed_creator('Message Sent', message, 'r', user, ctx.author, anon=False)
    user_embed = embed_creator('Message Received', message, 'r', ctx.guild, ctx.author, anon=False)
    files = []
    files_to_send = []
    for attachment in ctx.message.attachments:
        if attachment.size > 8000000:
            await ctx.send(embed=embed_creator('Failed to Send', 'One or more attachments are larger than 8 MB.', 'e'))
            return
        file = io.BytesIO(await attachment.read())
        file.seek(0)
        files.append((file, attachment.filename))
        files_to_send.append(discord.File(file, attachment.filename))
    try:
        user_message = await user.send(embed=user_embed, files=files_to_send)
    except discord.Forbidden:
        await ctx.send(embed=embed_creator('Failed to Send', f'User has server DMs disabled or has blocked {bot.user.name}.', 'e'))
        return
    for index, attachment in enumerate(user_message.attachments):
        channel_embed.add_field(name=f'Attachment {index + 1}', value=attachment.url, inline=False)
    await ctx.message.delete()
    # Must be rebuilt because a discord.File object can only be used once.
    files_to_send = []
    for file in files:
        file[0].seek(0)
        files_to_send.append(discord.File(file[0], file[1]))
    await ctx.send(embed=channel_embed, files=files_to_send)


@bot.command()
@commands.check(is_helper)
async def send(ctx, user: discord.User, *, message: str = ''):
    """Creates a ticket for a user and sends them an anonymous message"""

    if user == bot.user:
        await ctx.send(embed=embed_creator('', 'I cannot DM myself!', 'e'))
        return

    ticket_id = tickets.get(user.id)
    if ticket_id is not None:
        await ctx.send(embed=embed_creator('', f'A ticket for this user already exists: <#{ticket_id}>', 'e'))
        return

    if ctx.guild not in user.mutual_guilds:
        await ctx.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
        return

    user_embed = embed_creator('Message Received', message, 'r', ctx.guild)
    files = []
    files_to_send = []
    for attachment in ctx.message.attachments:
        if attachment.size > 8000000:
            await ctx.send(embed=embed_creator('Failed to Send', 'One or more attachments are larger than 8 MB.', 'e'))
            return
        file = io.BytesIO(await attachment.read())
        file.seek(0)
        files.append((file, attachment.filename))
        files_to_send.append(discord.File(file, attachment.filename))
    try:
        user_message = await user.send(embed=user_embed, files=files_to_send)
    except discord.Forbidden:
        await ctx.send(embed=embed_creator('Failed to Send', f'User has server DMs disabled or has blocked {bot.user.name}.', 'e'))
        return

    channel_embed = embed_creator('Message Sent', message, 'r', user, ctx.author)
    for index, attachment in enumerate(user_message.attachments):
        channel_embed.add_field(name=f'Attachment {index + 1}', value=attachment.url, inline=False)

    channel = await ctx.guild.create_text_channel(f'{user.name}',
                                                  category=bot.get_channel(config.category_id),
                                                  topic=f'{user.id} (User ID, do not change)')
    tickets[user.id] = channel.id
    await bot.get_channel(config.log_channel_id).send(embed=embed_creator('Ticket Created', '', 'r', user, ctx.author, anon=False))

    embed = embed_creator('Ticket Created by Moderator',
                          f'Replies are anonymous by default, and messages starting with `{config.prefix}` are ignored (although using the discussion thread is preferable). Use `{config.prefix}reply` to send a non-anonymous reply. Use `{config.prefix}close` to close anonymously.',
                          'b', user, time=True)
    embed.add_field(name='User', value=f'{user.mention} ({user.id})')
    header = await channel.send(embed=embed)

    if 'SEVEN_DAY_THREAD_ARCHIVE' in ctx.guild.features:
        duration = 10080
    elif 'THREE_DAY_THREAD_ARCHIVE' in ctx.guild.features:
        duration = 4320
    else:
        duration = 1440
    await header.create_thread(name=f'Discussion for {user.name}', auto_archive_duration=duration)

    files_to_send = []
    for file in files:
        file[0].seek(0)
        files_to_send.append(discord.File(file[0], file[1]))
    await channel.send(embed=channel_embed, files=files_to_send)
    await ctx.channel.send(embed=embed_creator('New Message Sent', f'Ticket: {channel.mention}', 'r', time=False))


@bot.command()
@commands.check(is_helper)
async def close(ctx, *, reason: str = ''):
    """Anonymously closes and logs a ticket"""

    if not is_modmail_channel(ctx):
        await ctx.send(embed=embed_creator('', 'This channel is not a valid ticket.', 'e'))
        return

    if len(reason) > 1024:
        await ctx.send(embed=embed_creator('', f'Reason too long: `{len(reason)}` characters. The maximum length for closing reasons is 1024.', 'e'))
        return

    user_id = ctx.channel.topic.split()[0]
    try:
        user_id = int(user_id)
        user = bot.get_user(user_id)
        if user is None:
            user = await bot.fetch_user(user_id)
    except (ValueError, discord.NotFound):
        user = None
        buttons = YesNoButtons()
        confirmation = await ctx.send(embed=embed_creator('User Not Found',
                                                          f"ID retrieved from channel topic as `{user_id}`. Try changing the channel's topic to just the user's ID. Otherwise, the user may have deleted their account.\n\nWould you still like to close the ticket?",
                                                          'b'), view=buttons)
        await buttons.wait()
        if buttons.value is None:
            await confirmation.edit(embed=embed_creator('User Not Found',
                                                        f"ID retrieved from channel topic as `{user_id}`. Try changing the channel's topic to just the user's ID. Otherwise, the user may have deleted their account.\n\nClosing cancelled due to timeout.",
                                                        'b'), view=None)
            return
        elif not buttons.value:
            await confirmation.edit(embed=embed_creator('User Not Found',
                                                        f"ID retrieved from channel topic as `{user_id}`. Try changing the channel's topic to just the user's ID. Otherwise, the user may have deleted their account.\n\nClosing cancelled by moderator.",
                                                        'b'), view=None)
            return
        else:
            await confirmation.edit(view=None)

    try:
        del tickets[user_id]
    except KeyError:
        pass

    await ctx.send(embed=embed_creator('Closing Ticket...', '', 'b'))

    # Logging

    try:
        channel_messages = [message async for message in ctx.channel.history(limit=1024, oldest_first=True)]
    except IndexError:
        channel_messages = []
    if len(ctx.channel.threads) >= 0:
        try:
            thread_messages = [message async for message in ctx.channel.threads[0].history(limit=1024, oldest_first=True)][1:]
        except IndexError:
            thread_messages = []
    else:
        archived_threads = await ctx.channel.archived_threads(limit=1)
        if len(archived_threads == 0):
            thread_messages = []
        else:
            try:
                thread_messages = [message async for message in archived_threads[0].history(limit=1024, oldest_first=True)][1:]
            except IndexError:
                thread_messages = []

    with open(f'{user_id}.txt', 'w') as txt_log:
        for message in channel_messages:
            if len(message.embeds) == 1:

                if message.embeds[0].description is None:
                    content = ''
                else:
                    content = message.embeds[0].description

                if message.embeds[0].title == 'Message Received':
                    txt_log.write(f'[{message.created_at.strftime("%y-%m-%d %H:%M")}] {message.embeds[0].footer.text} '
                                  f'(User): {content}')
                elif message.embeds[0].title == 'Message Sent':
                    txt_log.write(f'[{message.created_at.strftime("%y-%m-%d %H:%M")}] '
                                  f'{message.embeds[0].author.name.strip(" (Anonymous)")} (Mod): {content}')
                else:
                    continue

                for field in message.embeds[0].fields:
                    txt_log.write(f'\n{field.value}')

            else:
                txt_log.write(f'[{message.created_at.strftime("%y-%m-%d %H:%M")}] {message.author.name} (Comment): '
                              f'{message.content}')
            txt_log.write('\n')
        for message in thread_messages:
            txt_log.write(f'\n[{message.created_at.strftime("%y-%m-%d %H:%M")}] {message.author.name}: '
                          f'{message.content}')

    with open(f'{user_id}.htm', 'w') as htm_log:
        htm_log.write(
            '''
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>'''+bot.user.name+'''Log</title>
<style type="text/css">
    html { }
    body { font-size:16px; max-width:1000px; margin: 20px auto; padding:0; font-family:sans-serif; color:white; background:#2D2F33; }
    main { font-size:1em; line-height:1.3em; }
    p { white-space:pre-line; }
    div { }
    h1 { margin:25px 20px; font-weight:normal; font-size:3em; }
    h2 { margin:5px; font-size:1em; line-height:1.3em; }
    li.user h2 { color:lime; }
    li.staff h2 { color:orangered; }
    li.comment h2 { color:#6C757D; }
    span.datetime { color:#8898AA; font-weight:normal; }
    p { margin:5px; padding:0; }
    ul { margin-bottom: 50px; padding:0; list-style-type:none; }
    li { margin:5px; padding:15px; list-style-type:none; background:#222529; border-radius:5px; }
    img { max-width:100%; }
    video { max-width:100%; }
</style>
<script async src='/cdn-cgi/bm/cv/669835187/api.js'></script></head>
<body>
<h1>'''+bot.user.name+'''</h1>
<main>        
    <ul>
            '''
        )
        for message in channel_messages:
            if len(message.embeds) == 1:
                if message.embeds[0].title == 'Message Received':
                    htm_class = 'user'
                    name = html_sanitiser.clean(message.embeds[0].footer.text)
                elif message.embeds[0].title == 'Message Sent':
                    htm_class = 'staff'
                    name = html_sanitiser.clean(message.embeds[0].author.name.removesuffix(' (Anonymous)'))
                else:
                    continue
                if message.embeds[0].description is None:
                    content = ''
                else:
                    content = html_linkifier.clean(message.embeds[0].description)
                for i in range(len(message.embeds[0].fields)):
                    value = message.embeds[0].fields[i].value
                    mimetype = mimetypes.guess_type(value)[0]
                    if mimetype is not None:
                        filetype = mimetype.split('/', 1)[0]
                    else:
                        filetype = None
                    if i > 0 or content != '':
                        content += '<br></br>'
                    if filetype == 'image':
                        content += f'<img src="{value}" alt="{value}">'
                    elif filetype == 'video':
                        content += f'<video controls><source src="{value}" type="{mimetype}"><a href="{value}">{value}</a></video>'
                    else:
                        content += f'<a href="{value}">{value}</a>'
            else:
                htm_class = 'comment'
                name = html_sanitiser.clean(message.author.name)
                content = html_sanitiser.clean(message.content)
            htm_log.write(
                f'''
                <li class="{htm_class}">
                <h2>
                    <span class="name">
                        {name}
                    </span>
                    <span class="datetime">
                        {html_sanitiser.clean(message.created_at.strftime("%y-%m-%d %H:%M"))}
                    </span>
                </h2>
                <p>{content}</p>
                </li>
                '''
            )
        htm_log.write('</ul><ul>')
        for message in thread_messages:
            htm_log.write(
                f'''
                <li class="comment">
                <h2>
                    <span class="name">
                        {html_sanitiser.clean(message.author.name)}
                    </span>
                    <span class="datetime">
                        {html_sanitiser.clean(message.created_at.strftime("%y-%m-%d %H:%M"))}
                    </span>
                </h2>
                <p>{html_linkifier.clean(message.content)}</p>
                </li>
                '''
            )
        htm_log.write(
            '''
            </ul>
            </main>
            <script type="text/javascript">(function(){window['__CF$cv$params']={r:'6da5e8aa0d2172b5',m:'5dLd8.V25IY9gxywoWGKAj7j56QuVn7rur_rHLA1vRY-1644334327-0-AVXmbc6H8HGCfutFMct5cXfa2ZWp0QzIf62ZswYauMCDY5i6r0yH+dRdT2hMg/cTdi9wztDqs4wX3uYu3jlk2xaN/6gYwMbw57+MdRSBJvnkIxd2V2D/VEqQMEfedSczOkFaueNElC0lK5ZgSXq8SKW8U04f95BRGScgpFlUSozUEGpQFejg6K2xskUm4J/77g==',s:[0xf5207b6be0,0xa06951a27f],}})();
            </script>
            </body>
            </html>
            '''
        )
    embed_user = embed_creator('Ticket Closed', config.close_message, 'b', ctx.guild, time=True)
    embed_guild = embed_creator('Ticket Closed', '', 'r', user, ctx.author, anon=False)
    if reason:
        embed_user.add_field(name='Reason', value=reason)
        embed_guild.add_field(name='Reason', value=reason)
    embed_guild.add_field(name='User', value=f'<@{user_id}> ({user_id})', inline=False)
    log = await bot.get_channel(config.log_channel_id).send(embed=embed_guild, files=[discord.File(f'{user_id}.txt', filename=f'Log {ctx.channel.id}.txt'),
                                                                                      discord.File(f'{user_id}.htm', filename=f'Log {ctx.channel.id}.htm')])

    with sqlite3.connect('logs.db') as conn:
        curs = conn.cursor()
        curs.execute(f'INSERT INTO logs VALUES (?, ?, ?, ?)',
                     (user_id, int(ctx.channel.created_at.timestamp()), log.attachments[0].url, log.attachments[1].url))
        conn.commit()

    await ctx.channel.delete()
    os.remove(f'{user_id}.txt')
    os.remove(f'{user_id}.htm')
    if user is not None:
        try:
            await user.send(embed=embed_user)
        except discord.Forbidden:
            pass


@bot.group(invoke_without_command=True, aliases=['snippets'])
@commands.check(is_helper)
async def snippet(ctx, name: str):
    """Anonymously sends a snippet. Use sub-commands (!help snippet) to manage"""

    if not is_modmail_channel(ctx):
        await ctx.send(embed=embed_creator('', 'This channel is not a ticket.', 'e'))
        return

    name = name.lower()
    content = snippets.get(name)
    if content is not None:

        user_id = ctx.channel.topic.split()[0]
        try:
            user_id = int(user_id)
        except ValueError:
            await ctx.send(embed=embed_creator('Failed to Send', f"User ID found from channel topic: `{user_id}`. This is not a valid ID, please change the channel's topic to just the user's ID, then use `{config.prefix}refresh`", 'e'))
            return
        user = bot.get_user(user_id)
        if user is not None:
            if ctx.guild not in user.mutual_guilds:
                await ctx.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
                return
        else:
            try:
                await bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send(embed=embed_creator('Failed to Send', f"User with ID from channel topic, `{user_id}`, not found. Try changing the channel's topic to just the user's ID, then use `{config.prefix}refresh`. Otherwise, the user may have deleted their account.", 'e'))
            else:
                await ctx.send(embed=embed_creator('Failed to Send', 'User not in server.', 'e'))
            return

        await user.send(embed=embed_creator('Message Received', content, 'r', ctx.guild))
        await ctx.message.delete()
        await ctx.send(embed=embed_creator('Message Sent', content, 'r', user, ctx.author))
    else:
        await ctx.send(embed=embed_creator('', f'Snippet `{name}` does not exist.', 'e'))


@snippet.command()
async def view(ctx, name: str = ''):
    """Shows a named snippet, or all snippets if no name is given"""

    if name:
        name = name.lower()
        if name in snippets:
            embed = embed_creator('Snippet', '', 'b')
            embed.add_field(name='Name', value=name)
            embed.add_field(name='Content', value=snippets[name], inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed_creator('', f'Snippet `{name}` not found.', 'e'))
    else:
        embed = embed_creator('Snippets', '', 'b')
        for key, value in snippets.items():
            if len(value) > 103:
                embed.add_field(name=key, value=f'{value[:100]}...', inline=False)
            else:
                embed.add_field(name=key, value=value, inline=False)
        await ctx.send(embed=embed)


@snippet.command()
async def add(ctx, name: str, *, content: str):

    name = name.lower()
    if len(snippets) >= 25:
        await ctx.send(embed=embed_creator('', 'Maximum number of snippets already reached: 25.', 'e'))
        return
    if name in snippets:
        await ctx.send(embed=embed_creator('', f'Snippet `{name}` already exists. Use `{config.prefix}snippet edit {name} ...` to change it.', 'e'))
        return
    if name in ('view', 'add', 'edit', 'remove'):
        await ctx.send(embed=embed_creator('', 'Snippets cannot be named `view`, `add`, `edit` or `remove`.', 'e'))
        return
    if len(content) > 1024:
        await ctx.send(embed=embed_creator('', f'Content too long: `{len(content)}` characters. The maximum length of snippets is 1024.', 'e'))
        return
    if len(name) > 32:
        await ctx.send(embed=embed_creator('', f'Name too long: `{len(name)}` characters. The maximum length of snippet names is 32.', 'e'))
        return

    snippets.update({name: content})
    with open('snippets.json', 'w') as file:
        json.dump(snippets, file)
    embed = embed_creator('Snippet Added', '', 'b')
    embed.add_field(name='Name', value=name)
    embed.add_field(name='Content', value=content, inline=False)
    await ctx.send(embed=embed)


@snippet.command()
async def edit(ctx, name: str, *, content: str):

    name = name.lower()
    if name in snippets:
        snippets.update({name: content})
        with open('snippets.json', 'w') as file:
            json.dump(snippets, file)
        embed = embed_creator('Snippet Edited', '', 'b')
        embed.add_field(name='Name', value=name)
        embed.add_field(name='Content', value=content, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=embed_creator('', f'Snippet `{name}` not found.', 'e'))


@snippet.command()
async def remove(ctx, name: str):

    name = name.lower()
    if name in snippets:
        content = snippets.pop(name)
        with open('snippets.json', 'w') as file:
            json.dump(snippets, file)
        embed = embed_creator('Snippet Removed', '', 'b')
        embed.add_field(name='Name', value=name)
        embed.add_field(name='Content', value=content, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=embed_creator('', f'Snippet `{name}` not found.', 'e'))


@bot.group(invoke_without_command=True)
@commands.check(is_mod)
async def blacklist(ctx):
    """Use sub-commands (!help blacklist) to manage"""
    await ctx.send(embed=embed_creator('', 'Please specify `view`, `check`, `add` or `remove` as an additional argument.', 'e'))


@blacklist.command()
async def view(ctx):
    """Shows all blacklisted users"""

    content = ''
    for user_id in blacklist_list:
        content += f'<@{user_id}>\n'
    await ctx.send(embed=embed_creator('Blacklist', content, 'b'))


@blacklist.command()
async def check(ctx, user: discord.User):
    """Checks if a user is blacklisted"""

    if user.id in blacklist_list:
        await ctx.send(embed=embed_creator('', f'\u2714 **{user}** is blacklisted.', 'b'))
    else:
        await ctx.send(embed=embed_creator('', f'\u274e **{user}** is NOT blacklisted.', 'b'))


@blacklist.command()
async def add(ctx, user: discord.User, *, reason: str = ''):
    """Blacklists a user"""

    if user.id in blacklist_list:
        await ctx.send(embed=embed_creator('', 'User is already blacklisted.', 'e'))
        return
    if len(reason) > 1024:
        await ctx.send(embed=embed_creator('', f'Reason too long: {len(reason)} characters. The maximum length for blacklist reasons is 1024.', 'e'))
        return

    if ctx.guild in user.mutual_guilds:
        query_msg = f'Are you sure you want to blacklist **{user}** from {bot.user.name}? They will be messaged with the reason given.'
    else:
        query_msg = f'Are you sure you want to blacklist **{user}**? They are not in this server, and will not receive a notifying message.'

    buttons = YesNoButtons()
    confirmation = await ctx.send(embed=embed_creator('Confirmation', query_msg, 'b'), view=buttons)
    await buttons.wait()
    if buttons.value is None:
        await confirmation.edit(embed=embed_creator('', 'Blacklisting cancelled due to timeout.', 'b'), view=None)
        return
    if not buttons.value:
        await confirmation.edit(embed=embed_creator('', 'Blacklisting cancelled by moderator.', 'b'), view=None)
        return
    blacklist_list.append(user.id)
    with open('blacklist.json', 'w') as file:
        json.dump(blacklist_list, file)

    embed_user = embed_creator('Access Revoked', f'Your access to {bot.user.name} has been revoked by the moderators. You will no longer be able to send messages here.', 'r', ctx.guild)
    confirmation_msg = f'**{user}** has been blacklisted. They will no longer be able to message {bot.user.name}. User notified by direct message.'
    if reason:
        embed_user.add_field(name='Reason', value=reason)
    if ctx.guild in user.mutual_guilds:
        try:
            await user.send(embed=embed_user)
        except discord.Forbidden:
            confirmation_msg = f'**{user}** has been blacklisted. They will no longer be able to message {bot.user.name}. Failed to message user: DMs blocked.'
    else:
        confirmation_msg = f'**{user}** has been blacklisted. They will no longer be able to message {bot.user.name}. Failed to message user: not in server.'
    embed_guild = embed_creator('Blacklist Updated', confirmation_msg, 'b')
    if reason:
        embed_guild.add_field(name='Reason', value=reason)
    await confirmation.edit(embed=embed_guild, view=None)


@blacklist.command()
async def remove(ctx, user_id: int):
    """Un-blacklists a user"""

    if user_id in blacklist_list:
        blacklist_list.remove(user_id)
        with open('blacklist.json', 'w') as file:
            json.dump(blacklist_list, file)
        await ctx.send(embed=embed_creator('Blacklist Updated', f'User with ID `{user_id}` has been un-blacklisted. They can now message {bot.user.name}.', 'b'))
    else:
        await ctx.send(embed=embed_creator('', f'User with ID `{user_id}` is not blacklisted.', 'e'))


@bot.command()
@commands.check(is_helper)
async def search(ctx, user: discord.User, *, search_term: str = ''):
    """Displays a user's previous tickets, or only those containing a search term"""

    if search_term:
        search_term = search_term.lower()
        searching = await ctx.send(embed=embed_creator('Searching...', 'This may take a while.', 'b'))
    else:
        searching = None

    embeds = [embed_creator(f'Tickets for {user}', '', 'b')]
    with sqlite3.connect('logs.db') as conn:
        curs = conn.cursor()
        curs.execute(f'SELECT timestamp, txt_log_url, htm_log_url FROM logs WHERE user_id = ?', (user.id,))

    async with aiohttp.ClientSession() as session:
        for timestamp, txt_log_url, htm_log_url in curs.fetchall():
            if search_term:
                async with session.get(txt_log_url) as response:
                    text_log = await response.read()
                    if search_term not in text_log.decode('utf-8').lower():
                        continue

            if len(embeds[-1].description) > 3900:
                embeds.append(embed_creator('', '', 'b'))

            embeds[-1].description += f'• <t:{int(timestamp)}:D> {htm_log_url}\n'

    if searching is not None:
        await searching.delete()
    for embed in embeds:
        await ctx.send(embed=embed)


@bot.command()
@commands.check(is_helper)
async def ping(ctx):
    await ctx.send(embed=embed_creator('Pong!', f'{round(bot.latency * 1000)} ms', 'b'))


@bot.command()
@commands.check(is_helper)
async def refresh(ctx):
    """Re-reads the external config file, and may fix some ticket-related issues"""

    with open('config.json', 'r') as file:
        config.update(json.load(file))
    await load_tickets()
    await ctx.message.add_reaction('\u2705')


@bot.command()
@commands.is_owner()
async def eval(ctx, *, body: str):
    # Copied from Danny's bot, R. Danny, with a few small changes.

    env = {
        'ctx': ctx
    }
    env.update(globals())

    stdout = io.StringIO()

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

    func = env['func']
    try:
        with contextlib.redirect_stdout(stdout):
            ret = await func()
    except:
        value = stdout.getvalue()
        try:
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        except discord.HTTPException:
            await bot.get_user(config.bot_owner_id).send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        try:
            await ctx.message.add_reaction('\u2705')
        except:
            pass

        if ret is None:
            if value:
                await ctx.send(f'```py\n{value}\n```')
        else:
            await ctx.send(f'```py\n{value}{ret}\n```')


bot.run(config.token, log_handler=None)
