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
- bot owner (this is NOT the server owner, but whoever is hosting the bot) - has access to the `eval` command
- moderator - has access to everything
- helper - has access to everything except the blacklist

If you do not have a helper role in your server, set `helper_role_id` to the same value as `mod_role_id`. 

## Dependancies
Modmail requires the following Python packages to also be installed.

### bleach
https://github.com/mozilla/bleach. This is available in PyPI, so can be easily installed with pip. The latest version that has been tested as working is `5.0.0`.

### discord.py
https://github.com/Rapptz/discord.py. Modmail requires version `2.0.0a`, which is under active development and has relatively frequent breaking changes.
[This version](https://github.com/Rapptz/discord.py/tree/5892bbd8b44fc8cff6b5bd2e476249e0a3d313c5) is the latest commit that has been tested as working.
