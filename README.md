# ModMail
A Modmail bot for Discord.

I originally made this as a custom project for the official Chivalry 2 Discord server, but it is now server-agnostic.
Although it is not a fork of the widely-used [Modmail bot made by Kyber](https://github.com/kyb3r/modmail), 
its user experience is heavily inspired by it and will be very similar, with some improvements and additional features (but also a few missing ones).

Please note that I am not hosting this bot. If you want to use it, you will have to host it yourself. Oracle Cloud
and Google Cloud both have free tiers that provide sufficiently-resourced instances.

## Configuration
This is simple. Fill out the `config.json` file in `templates` and put it in the same directory as the main script, along with the other `.json` files.

The bot has three permission levels:
- bot owner - has access to the `eval` command. This is independant of `bot_owner_id` in the config, which determines the user to send error tracebacks to.
- moderator - has access to everything
- helper - has access to everything except the blacklist

If you do not have a helper role in your server, set `helper_role_id` to the same value as `mod_role_id`. 

## Dependancies
Modmail requires Python 3.10+ as well as the following Python packages.

### bleach
https://github.com/mozilla/bleach. This is available in PyPI, so can be easily installed with pip. The latest version that has been tested as working is `5.0.0`.

### discord.py
https://github.com/Rapptz/discord.py. Modmail requires version `2.0.0a`, which is under active development and has relatively frequent breaking changes.
This fork is the latest version that has been tested as working with the latest version of ModMail: https://github.com/TobiWan54/discord.py.
