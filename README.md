# ModMail
A Modmail bot for Discord.

I originally made this as a custom project for the official Chivalry 2 Discord server, but it is now server-agnostic.
Although it is not a fork of the widely-used [Modmail bot made by Kyber](https://github.com/kyb3r/modmail), 
its user experience is heavily inspired by it and will be very similar, with some improvements and additional features (but also a few missing ones).

Please note that I am not hosting this bot. If you want to use it, you will have to host it yourself. Oracle Cloud
and Google Cloud both have free tiers that provide sufficiently-resourced instances.

## Configuration
This is simple. Fill out the `config.json` file and put it in the same directory as the main script.

The bot has three permission levels:
- bot owner (this is NOT the server owner, but whoever is hosting the bot) - has access to the `eval` command
- moderator - has access to everything
- helper - has access to everything except the blacklist

If you do not have a helper role in your server, set `helper_role_id` to the same value as `mod_role_id`. 
