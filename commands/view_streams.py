import requests


async def execute(event, client, *args):
    if args:
        await event.reply(f"Just use {client.prefix}view_streams")
        return

    if not client.config["streams"]:
        await event.respond("No streams found!")
        return

    msg = await event.respond("Loading...")

    message = "**Streams:**\n```"
    for stream in client.config["streams"]:
        input_channels = ", ".join(
            [client.config["telegram_channels"][channel]
             for channel in stream["input_channels"]]
        )
        output_hooks = ", ".join(
            [requests.get(url).json()["name"]
             if requests.get(url).status_code == 200
             else f"..{url[-5:]}"
             for url in stream["output_hooks"]]
        )
        message += f"Input channels: {input_channels}\nOutput hooks: {output_hooks}\n\n"

    message += "```\n**Telegram channels:**\n```"
    for channel_id, channel_name in client.config["telegram_channels"].items():
        message += f"{channel_id}: {channel_name}\n"
    message += "```"

    await msg.edit(message)
