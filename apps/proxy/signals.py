from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='channels.ChannelStream')
def on_channel_stream_save(sender, instance, **kwargs):
    from apps.proxy.rust_proxy_client import push_channel
    push_channel(instance.channel)


@receiver(post_delete, sender='channels.ChannelStream')
def on_channel_stream_delete(sender, instance, **kwargs):
    from apps.proxy.rust_proxy_client import push_channel
    push_channel(instance.channel)

@receiver(pre_delete)
def cleanup_proxy_servers(sender, **kwargs):
    """Clean up proxy servers when Django shuts down"""
    try:
        proxy_app = apps.get_app_config('proxy')
        for channel_id in list(proxy_app.hls_proxy.stream_managers.keys()):
            proxy_app.hls_proxy.stop_channel(channel_id)
        for channel_id in list(proxy_app.ts_proxy.stream_managers.keys()):
            proxy_app.ts_proxy.stop_channel(channel_id)
        logger.info("Proxy servers cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during proxy server cleanup: {e}")