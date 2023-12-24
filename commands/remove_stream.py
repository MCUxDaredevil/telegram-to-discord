async def execute(event, client, *args):
    if len(args) != 2:
        await event.reply(f"Usage: {client.prefix}remove_stream <input_channel_id> <webhook_url>")
        return

    input_channel_id = args[0]
    if not input_channel_id.isdigit():
        await event.reply(f"Usage: {client.prefix}remove_stream <input_channel_id> <webhook_url>")
        return

    webhook_url = args[1]
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        await event.reply(f"Usage: {client.prefix}remove_stream <input_channel_id> <webhook_url>")
        return

    for stream in client.config["streams"]:
        if input_channel_id in stream["input_channels"] and webhook_url in stream["output_hooks"]:
            if len(stream["input_channels"]) == 1 and len(stream["output_hooks"]) == 1:
                client.config["streams"].remove(stream)
                break

            if len(stream["input_channels"]) == 1 ^ len(stream["output_hooks"]) == 1:
                await event.reply("This stream is not complete!")
                return

            stream["input_channels"].remove(input_channel_id)
            stream["output_hooks"].remove(webhook_url)
            break
    else:
        await event.reply("Stream not found!")
        return

    client.update_config(client)
    await event.reply("Stream removed successfully!")
