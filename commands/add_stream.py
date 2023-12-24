async def execute(event, client, *args):
    if len(args) != 2:
        print(args)
        await event.reply(f"Usage: {client.prefix}add_stream <input_channel_id> <webhook_url>")
        return

    input_channel_id = args[0]
    if not input_channel_id.isdigit():
        await event.reply(f"Usage: {client.prefix}add_stream <input_channel_id> <webhook_url>")
        return

    webhook_url = args[1]
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        await event.reply(f"Usage: {client.prefix}add_stream <input_channel_id> <webhook_url>")
        return

    if input_channel_id not in client.config["telegram_channels"]:
        await event.reply("What's the name of that channel?")
        reply = await client.wait_for("message", timeout=60)
        if not reply:
            await event.reply("Timed out!")
            return
        else:
            client.config["telegram_channels"][input_channel_id] = reply.message
            client.update_config(client)

    for stream in client.config["streams"]:
        if input_channel_id in stream["input_channels"]:
            stream["output_hooks"].append(webhook_url)
            break

        elif webhook_url in stream["output_hooks"]:
            stream["input_channels"].append(input_channel_id)
            break
    else:
        client.config["streams"].append({
            "input_channels": [input_channel_id],
            "output_hooks": [webhook_url]
        })

    client.update_config(client)
    await event.reply("Stream added successfully!")

