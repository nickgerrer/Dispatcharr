import logging
import requests

logger = logging.getLogger(__name__)

RUST_PROXY_URL = "http://127.0.0.1:8888"


def sync_all_channels():
    """Push all channel configs and account limits to Rust proxy."""
    from apps.channels.models import Channel, ChannelStream
    from apps.m3u.models import M3UAccount, M3UAccountProfile
    from apps.proxy.ts_proxy.url_utils import transform_url

    channels = {}
    for channel in Channel.objects.all():
        streams_config = []
        for cs in (
            ChannelStream.objects.filter(channel=channel)
            .order_by("order")
            .select_related("stream__m3u_account")
        ):
            stream = cs.stream
            urls = []
            account = stream.m3u_account
            if not account:
                continue
            for profile in account.profiles.filter(is_active=True).order_by(
                "-is_default"
            ):
                url = transform_url(
                    stream.url,
                    profile.search_pattern,
                    profile.replace_pattern,
                )
                urls.append(
                    {
                        "account_id": account.id,
                        "url": url,
                    }
                )
            if urls:
                streams_config.append(
                    {
                        "id": stream.id,
                        "urls": urls,
                    }
                )
        if streams_config:
            channels[str(channel.uuid)] = {"streams": streams_config}

    accounts = {}
    for profile in M3UAccountProfile.objects.filter(is_active=True):
        account_id = str(profile.m3u_account_id)
        accounts[account_id] = {
            "max_connections": profile.max_streams,
        }

    payload = {"channels": channels, "accounts": accounts}

    try:
        resp = requests.post(
            f"{RUST_PROXY_URL}/control/v1/sync",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(
            "Rust proxy sync: %d channels, %d accounts",
            len(channels),
            len(accounts),
        )
    except requests.RequestException as e:
        logger.error("Failed to sync with Rust proxy: %s", e)


def push_channel(channel):
    """Push a single channel's config to Rust proxy."""
    from apps.channels.models import ChannelStream
    from apps.proxy.ts_proxy.url_utils import transform_url

    streams_config = []
    for cs in (
        ChannelStream.objects.filter(channel=channel)
        .order_by("order")
        .select_related("stream__m3u_account")
    ):
        stream = cs.stream
        urls = []
        account = stream.m3u_account
        if not account:
            continue
        for profile in account.profiles.filter(is_active=True).order_by(
            "-is_default"
        ):
            url = transform_url(
                stream.url,
                profile.search_pattern,
                profile.replace_pattern,
            )
            urls.append(
                {
                    "account_id": account.id,
                    "url": url,
                }
            )
        if urls:
            streams_config.append({"id": stream.id, "urls": urls})

    try:
        resp = requests.put(
            f"{RUST_PROXY_URL}/control/v1/channels/{channel.uuid}",
            json={"streams": streams_config},
            timeout=5,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(
            "Failed to push channel %s to Rust proxy: %s", channel.uuid, e
        )


def remove_channel(channel_uuid):
    """Remove a channel from Rust proxy."""
    try:
        resp = requests.delete(
            f"{RUST_PROXY_URL}/control/v1/channels/{channel_uuid}",
            timeout=5,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(
            "Failed to remove channel %s from Rust proxy: %s",
            channel_uuid,
            e,
        )
