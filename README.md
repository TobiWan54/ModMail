# ModMail
A Modmail bot for Discord.

I originally made this as a custom project for the official Chivalry 2 Discord server, but it is now server-agnostic.
Although it is not a fork of the widely-used Modmail bot made by Kyber: https://github.com/kyb3r/modmail, the experience will be very similar.

Message me on Discord if you have any questions, or if you need any help with using it.

## Features
When a user messages the bot, a new channel is created in a category in your server, representing a ticket. As you would expect from a Modmail bot, 
all the messages in the ticket are logged when the ticket is closed. You can also blacklist users for misuse, and set pre-defined snippets which can 
be sent with a single command.

However, this bot has a few additional features that make it unique:

- **Discussion Threads:**  Each ticket channel has a thread automatically created which is also logged when the ticket is closed.
This allows mods to discuss freely, without the risk of accidentally sending a rude message to the user!

- **!search:** Allows you to retrieve the logs of a user's previous tickets, and to search for specific phrases within those tickets.

- **!send:** Creates a new ticket and sends an anonymous message to a user that does not already have a ticket open.

Once you have the bot running, the !help command will show you a list of all the available commands and their sub-commands.

## Setup

To use this bot, you will have to create a bot account for it on the [Discord Developer Portal](https://discord.com/developers)
and host the script yourself. Oracle Cloud and Google Cloud both have free tiers that provide sufficiently-resourced instances 
(virtual machines) for hosting.

The script requires Python 3.10 or higher and the packages listed under Dependancies.

### Configuration
Fill out the `config.json` file in [templates](https://github.com/TobiWan54/ModMail/tree/main/templates) and put it in the same 
directory as `modmail.py`. Then add the other `.json` files - there is no need to change these.
When that's all done you can run the script, and your bot will be online!

#### config.json

- `token` is your bot account's token from the Discord Developer Portal.
- `guild_id` is your server's ID.
- `category_id` is the ID of the category that tickets to be created in. You will have to create this yourself.
- `log_channel_id` is the ID of the channel that ticket logs will be sent in.
You will have to create this yourself - if it is the tickets category, make sure it has no topic or it will break the bot.
- `helper_role_id` is the ID of your server's helper role, which can use everything except the blacklist.
If you do not have a helper role, set this to the same value as `mod_role_id`.
- `mod_role_id` is the ID of your server's moderator role, which can use everything.
- `bot_owner_id` is the ID of the user that error tracebacks will be DM'd to. Access to the !eval command, which allows you to run code,
is given to the bot owner(s) in the Discord Developer Portal, not this user (although they will likely be the same user).
- `prefix` is the bot's prefix.
- `open_message` is the text that users will receive under "Ticket Created" when they open a ticket.
- `close_message` is the text that users will receive under "Ticket Closed" when a mod closes their ticket.

The !refresh command will make the script re-read the config file, so you can change these values without restarting the bot.

### Dependancies

#### [bleach](https://github.com/mozilla/bleach)
This is in PyPI so is simple to install: `pip install bleach`. The latest version that has been tested is 5.0.0, 
although future versions are very likely to carry on working.

#### [discord.py](https://github.com/Rapptz/discord.py)
Modmail requires version 2.0, which must be installed from github: `pip install -U git+https://github.com/Rapptz/discord.py`.
Since this is under active development there are relatively frequent breaking changes. This fork is of an unchanged version that has been
tested as working, and will be updated so that it always works with the latest version of ModMail: https://github.com/TobiWan54/discord.py
