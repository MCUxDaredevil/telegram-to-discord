import asyncio
import json
from copy import deepcopy

from discord_webhook import DiscordEmbed, AsyncDiscordWebhook
from telethon.sync import TelegramClient, events
from telethon.tl.types import InputChannel, MessageEntityBold, MessageEntityItalic, \
    MessageEntityStrike, MessageEntityCode, MessageEntityPre, MessageEntityMention, \
    MessageEntityMentionName, MessageEntityHashtag, MessageEntityTextUrl

with open("config.json", "r") as f:
    config = json.load(f)

telegram_client = TelegramClient(**config["telegram_settings"])

input_channels_entities = []
output_channels = {}


@telegram_client.on(events.NewMessage(chats=input_channels_entities))
async def handle_telegram_message(event):
    result = resolve_input_id(event.message.to_id.channel_id)
    if result is None:
        return
    channel_name, output_hooks = result

    message = event.message.message
    source_message = deepcopy(message)
    for entity in event.message.entities:
        message = decorate_message(message, source_message, entity)

    embed = DiscordEmbed(title=channel_name, description=message, color=0x00ff00)

    for webhook in output_hooks:
        webhook_reply = await send_webhook(embed, webhook)
        print(webhook_reply.status_code)


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
    if channel_id not in config["telegram_channels"].values():
        return None

    for stream in config["streams"]:
        if channel_id in stream["input_channels"]:
            return config["telegram_channels"][str(channel_id)], stream["output_hooks"]


def decorate_message(current_message, source_message, entity):
    start = entity.offset - 4
    end = entity.offset - 4 + entity.length
    target_text = source_message[start:end]

    decorators = {
        MessageEntityBold: ("**", "**"),
        MessageEntityItalic: ("*", "*"),
        MessageEntityStrike: ("~~", "~~"),
        MessageEntityCode: ("`", "`"),
        MessageEntityPre: ("```", "```"),
        MessageEntityMention: ("@", ""),
        MessageEntityMentionName: ("@", ""),
        MessageEntityHashtag: ("#", ""),
        MessageEntityTextUrl: (f"[{target_text}]({entity.url})", "")
    }

    for entity_type, (prefix, suffix) in decorators.items():
        if isinstance(entity, entity_type):
            current_message = current_message.replace(target_text, f"{prefix}{target_text}{suffix}", 1)

    return current_message


async def fetch_telegram_channels():
    async for d in telegram_client.iter_dialogs():
        if d.name in config["telegram_channels"] or d.entity.id in config["telegram_channels"].values():
            input_channels_entities.append(InputChannel(d.entity.id, d.entity.access_hash))


async def main():
    await telegram_client.start()

    if not input_channels_entities:
        await telegram_client.disconnect()
        return

    await fetch_telegram_channels()
    print(f"Listening on {len(input_channels_entities)} channels")

    await asyncio.gather(telegram_client.run_until_disconnected())


if __name__ == '__main__':
    asyncio.run(main())
