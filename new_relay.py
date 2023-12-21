import json
import sys
from copy import deepcopy

from discord_webhook import DiscordEmbed, AsyncDiscordWebhook
from telethon import TelegramClient, events
from telethon.tl.types import InputChannel
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, \
    MessageEntityStrike, MessageEntityCode, MessageEntityPre, MessageEntityMention, \
    MessageEntityMentionName, MessageEntityHashtag, MessageEntityTextUrl


async def send_webhook(embed, webhook):
    avatar_url = webhook.get("avatar_url", None)
    webhook_reply = AsyncDiscordWebhook(
        url=webhook["url"],
        rate_limit_retry=True,
        avatar_url=avatar_url
    )
    webhook_reply.add_embed(embed)
    return await webhook_reply.execute()


def resolve_input_id(channel_id):
    if channel_id not in config["telegram_channels"]:
        return None

    for stream in config["streams"]:
        if channel_id in stream["input_channels"]:
            return config["telegram_channels"][channel_id], stream["output_hooks"]


def decorate_message(current_message, source_message, entity):
    begin = entity.offset - 4
    end = entity.offset - 4 + entity.length
    target_text = source_message[begin:end]
    decorated_message = current_message

    if isinstance(entity, MessageEntityBold):
        decorated_message = current_message.replace(target_text, f"**{target_text}**", 1)
    elif isinstance(entity, MessageEntityItalic):
        decorated_message = current_message.replace(target_text, f"*{target_text}*", 1)
    elif isinstance(entity, MessageEntityStrike):
        decorated_message = current_message.replace(target_text, f"~~{target_text}~~", 1)
    elif isinstance(entity, MessageEntityCode):
        decorated_message = current_message.replace(target_text, f"`{target_text}`", 1)
    elif isinstance(entity, MessageEntityPre):
        decorated_message = current_message.replace(target_text, f"```{target_text}```", 1)
    elif isinstance(entity, MessageEntityMention):
        decorated_message = current_message.replace(target_text, f"@{target_text}", 1)
    elif isinstance(entity, MessageEntityMentionName):
        decorated_message = current_message.replace(target_text, f"@{target_text}", 1)
    elif isinstance(entity, MessageEntityHashtag):
        decorated_message = current_message.replace(target_text, f"#{target_text}", 1)
    elif isinstance(entity, MessageEntityTextUrl):
        decorated_message = current_message.replace(target_text, f"[{target_text}]({entity.url})", 1)

    return decorated_message


def start():
    client = TelegramClient(**config["telegram_settings"])
    client.start()

    input_channels_entities = []

    for d in client.iter_dialogs():
        if (
                d.name in config["telegram_channels"].values()
                or d.entity.id in config["telegram_channels"]
        ):
            input_channels_entities.append(
                InputChannel(d.entity.id, d.entity.access_hash)
            )

    if not input_channels_entities:
        print("Could not find any input channels in the user's dialogs")
        sys.exit(1)

    print(f"Listening on {len(input_channels_entities)} channels")

    @client.on(events.NewMessage(chats=input_channels_entities))
    async def handler(event):
        result = resolve_input_id(str(event.message.to_id.channel_id))
        if result is None:
            return
        channel_name, output_hooks = result

        message = event.message.message
        if event.message.entities is not None:
            source_message = deepcopy(message)
            for entity in event.message.entities:
                message = decorate_message(message, source_message, entity)

        embed = DiscordEmbed(title=channel_name, description=message, color=0x00ff00)

        for webhook in output_hooks:
            webhook_reply = await send_webhook(embed, webhook)
            print(f"Sent message to {webhook_reply.url}")

    client.run_until_disconnected()


with open("config.json", "r") as f:
    config = json.load(f)

start()
