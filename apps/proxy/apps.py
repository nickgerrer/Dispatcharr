import sys
from django.apps import AppConfig

class ProxyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.proxy'
    verbose_name = "Stream Proxies"

    def ready(self):
        """Initialize proxy servers when Django starts"""
        if 'manage.py' not in sys.argv:
            from .hls_proxy.server import ProxyServer as HLSProxyServer
            from .ts_proxy.server import ProxyServer as TSProxyServer

            # Initialize proxy servers
            self.hls_proxy = HLSProxyServer()
            self.ts_proxy = TSProxyServer()

            # Sync channel configs to Rust proxy after startup
            import threading
            from .rust_proxy_client import sync_all_channels
            threading.Timer(5.0, sync_all_channels).start()
