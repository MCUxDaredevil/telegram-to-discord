import json
import os
import sys
from copy import deepcopy
from importlib import import_module

from mimetypes import guess_extension

from discord_webhook import DiscordEmbed, AsyncDiscordWebhook
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import InputChannel, MessageEntityCashtag, MessageEntityTextUrl, DocumentAttributeFilename


async def send_webhook(embed, webhook, *files):
    webhook_reply = AsyncDiscordWebhook(
        url=webhook,
        rate_limit_retry=True
    )
    webhook_reply.add_embed(embed)

    if files:
        for idx, (file, ext) in enumerate(files):
            webhook_reply.add_file(file, f"file{idx}.{ext}")

    return await webhook_reply.execute()


def resolve_input_id(config, channel_id):
    if channel_id not in config["telegram_channels"]:
        return None

    for stream in config["streams"]:
        if channel_id in stream["input_channels"]:
            return config["telegram_channels"][channel_id], stream["output_hooks"]


def decorate_message(current_message, source_message, entity, parity_offset):
    begin = entity.offset - parity_offset
    end = entity.offset - parity_offset + entity.length
    target_text = source_message[begin:end]
    decorated_message = current_message

    if isinstance(entity, MessageEntityTextUrl):
        decorated_message = current_message.replace(target_text, f"[{target_text}]({entity.url})", 1)

    return decorated_message


def get_channel_entities(client):
    return [
        InputChannel(d.entity.id, d.entity.access_hash)
        for d in client.iter_dialogs()
        if (
                d.name in client.config["telegram_channels"].values()
                or str(d.entity.id) in client.config["telegram_channels"]
                or str(d.entity.id) in client.config["commands"]["channels"]
        )
    ]


def load_commands(client):
    commands = {}
    command_folder = "commands"

    for filename in os.listdir(command_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            command_name = os.path.splitext(filename)[0]
            command = import_module(f"{command_folder}.{command_name}")
            commands[command_name] = command.execute

            print(f"Loaded command {command_name}")

    client.commands = commands


async def handle_command(event, client):
    message = event.message.message
    if not message.startswith(client.config["commands"]["prefix"]):
        return

    command = message[1:].split(" ")
    if command[0] not in client.commands:
        return

    if len(command) == 1:
        await client.commands[command[0]](event, client)
    else:
        await client.commands[command[0]](event, client, *command[1:])


def load_config(client):
    if len(sys.argv) == 2 and sys.argv[1] == "dev":
        print("Running in dev mode")
        with open("dev_config.json", "r") as f:
            client.config = json.load(f)
    else:
        with open("config.json", "r") as f:
            client.config = json.load(f)

    client.prefix = client.config["commands"]["prefix"]


def update_config(client):
    if sys.argv[1] == "dev":
        with open("dev_config.json", "w") as f:
            json.dump(client.config, f, indent=2)
    else:
        with open("config.json", "w") as f:
            json.dump(client.config, f, indent=2)

    load_config(client)


def start():
    client = TelegramClient(os.getenv("SESSION_NAME"), int(os.getenv("API_ID")), os.getenv("API_HASH"))
    client.start()
    load_commands(client)
    load_config(client)
    client.update_config = update_config

    input_channels_entities = get_channel_entities(client)

    if not input_channels_entities:
        print("Could not find any input channels in the user's dialogs")
        sys.exit(1)

    print(f"Listening on {len(input_channels_entities)} channels")

    @client.on(events.NewMessage(chats=input_channels_entities))
    async def handler(event):
        channel_id = str(event.message.to_id.channel_id)
        if channel_id in client.config["commands"]["channels"]:
            await handle_command(event, client)
            return
        result = resolve_input_id(client.config, channel_id)
        if result is None:
            return
        channel_name, output_hooks = result

        media_files = []
        if event.message.media:
            media = await event.message.download_media(file=bytes)
            ext = guess_extension(event.message.media.document.mime_type) if hasattr(event.message.media, 'document') else '.jpg'
            media_files.append((media, ext))

        message = event.message.message
        message_entities = event.message.entities or []

        if message_entities:
            offset = next((e.offset for e in message_entities if isinstance(e, MessageEntityCashtag)), -1) + 1

            source_message = deepcopy(message)
            print(offset)
            for entity in message_entities:
                message = decorate_message(message, source_message, entity, offset)

        embed = DiscordEmbed(title=channel_name, description=message, color=0x00ff00)

        for webhook in output_hooks:
            webhook_reply = await send_webhook(embed, webhook, *media_files)
            print(f"Sent message to {webhook_reply.url}")

    client.run_until_disconnected()


if __name__ == "__main__":
    load_dotenv()
    start()
