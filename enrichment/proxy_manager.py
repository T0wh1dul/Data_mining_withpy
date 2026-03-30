"""
proxy_manager.py
────────────────
Handles proxy rotation and failover for HTTP/SOCKS requests.
Supports multiple proxy services with automatic fallback.
"""

import logging
import random
from typing import Optional, List, Dict
from urllib.parse import urlparse

from enrichment import proxy_config

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy provider selection, rotation, and failover."""
    
    def __init__(self):
        self.service = proxy_config.PROXY_SERVICE
        self.provider_order: List[str] = []
        self.provider_proxies: Dict[str, List[str]] = {}
        self.provider_failed: Dict[str, set] = {}
        self.active_provider_name = "none"
        self.current_proxy = None
        self._init_providers()
    
    def _init_providers(self):
        """Build provider map based on selected mode."""
        if self.service == "auto":
            providers = proxy_config.AUTO_PROVIDER_PRIORITY
        else:
            providers = [self.service]
            if proxy_config.PROXY_FALLBACK_TO_DIRECT and "none" not in providers:
                providers.append("none")

        valid = {"brightdata", "oxylabs", "smartproxy", "generic", "manual", "none"}
        self.provider_order = [p for p in providers if p in valid]
        if not self.provider_order:
            self.provider_order = ["none"]

        for provider in self.provider_order:
            proxies = self._build_provider_proxies(provider)
            self.provider_proxies[provider] = proxies
            self.provider_failed[provider] = set()

        logger.info(f"[PROXY] Mode={self.service} | Providers={self.provider_order}")
    
    def _build_brightdata_proxies(self) -> list:
        """Build Bright Data proxy URLs."""
        if not proxy_config.BRIGHTDATA_USERNAME or not proxy_config.BRIGHTDATA_PASSWORD:
            logger.warning("[PROXY] Bright Data credentials missing - using direct connection")
            return []
        
        username = proxy_config.BRIGHTDATA_USERNAME
        password = proxy_config.BRIGHTDATA_PASSWORD
        zone = proxy_config.BRIGHTDATA_ZONE
        
        # Bright Data format: socks5://username-zone:password@proxy.provider.com:port
        proxy_url = f"socks5://{username}-{zone}:{password}@proxy.brightdata.com:22225"
        return [proxy_url]
    
    def _build_oxylabs_proxies(self) -> list:
        """Build Oxylabs proxy URLs."""
        if not proxy_config.OXYLABS_USERNAME or not proxy_config.OXYLABS_PASSWORD:
            logger.warning("[PROXY] Oxylabs credentials missing - using direct connection")
            return []
        
        username = proxy_config.OXYLABS_USERNAME
        password = proxy_config.OXYLABS_PASSWORD
        proxy_url = f"http://{username}:{password}@{proxy_config.OXYLABS_PROXY}"
        return [proxy_url]
    
    def _build_smartproxy_proxies(self) -> list:
        """Build SmartProxy proxy URLs."""
        if not proxy_config.SMARTPROXY_USERNAME or not proxy_config.SMARTPROXY_PASSWORD:
            logger.warning("[PROXY] SmartProxy credentials missing - using direct connection")
            return []
        
        username = proxy_config.SMARTPROXY_USERNAME
        password = proxy_config.SMARTPROXY_PASSWORD
        proxy_url = f"http://{username}:{password}@{proxy_config.SMARTPROXY_PROXY}"
        return [proxy_url]

    def _build_provider_proxies(self, provider: str) -> List[str]:
        """Return proxy list for one provider."""
        if provider == "brightdata":
            return self._build_brightdata_proxies()
        if provider == "oxylabs":
            return self._build_oxylabs_proxies()
        if provider == "smartproxy":
            return self._build_smartproxy_proxies()
        if provider == "manual":
            return list(proxy_config.MANUAL_PROXIES)
        if provider == "generic":
            generic = list(proxy_config.GENERIC_PROXY_POOL)
            if proxy_config.GENERIC_PROXY_URL:
                generic.append(proxy_config.GENERIC_PROXY_URL)
            return generic
        return []
    
    def get_next_proxy(self) -> Optional[str]:
        """
        Get next proxy URL in rotation.
        Returns a proxy string URL for DDGS.
        Returns None for no proxy.
        """
        if not self.provider_order:
            self.active_provider_name = "none"
            return None

        start_idx = self.provider_order.index(self.active_provider_name) if self.active_provider_name in self.provider_order else 0
        total = len(self.provider_order)

        for offset in range(total):
            idx = (start_idx + offset) % total
            provider = self.provider_order[idx]
            if provider == "none":
                self.active_provider_name = "none"
                self.current_proxy = None
                return None

            proxies = self.provider_proxies.get(provider, [])
            failed = self.provider_failed.get(provider, set())
            available = [p for p in proxies if p not in failed]

            if not available:
                if proxy_config.PROXY_AUTO_SWITCH:
                    continue
                if proxy_config.PROXY_FALLBACK_TO_DIRECT:
                    self.active_provider_name = "none"
                    self.current_proxy = None
                    return None
                self.provider_failed[provider].clear()
                available = proxies

            if not available:
                continue

            self.active_provider_name = provider
            if proxy_config.PROXY_ROTATION_PER_ROW:
                self.current_proxy = random.choice(available)
            elif self.current_proxy not in available:
                self.current_proxy = available[0]

            logger.debug(
                f"[PROXY] Provider={provider} using {self._sanitize_url(self.current_proxy)}"
            )
            return self.current_proxy

        if proxy_config.PROXY_FALLBACK_TO_DIRECT:
            self.active_provider_name = "none"
            self.current_proxy = None
            logger.warning("[PROXY] No healthy proxies left. Falling back to direct connection")
            return None

        logger.warning("[PROXY] No healthy proxies available")
        return None
    
    def mark_proxy_failed(self, proxy: Optional[str]):
        """Mark a proxy as failed for this session."""
        if not proxy:
            return
        provider = self.active_provider_name
        if provider not in self.provider_failed:
            return

        self.provider_failed[provider].add(proxy)
        logger.warning(
            f"[PROXY] Marked failed: provider={provider} {self._sanitize_url(proxy)}"
        )
    
    def reset_failed_proxies(self):
        """Reset the failed proxy set."""
        for failed in self.provider_failed.values():
            failed.clear()
        logger.debug("[PROXY] Reset failed proxy list")
    
    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove credentials from URL for logging."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                host = parsed.hostname or "unknown-host"
                if parsed.port:
                    host = f"{host}:{parsed.port}"
                return f"{parsed.scheme}://***:***@{host}{parsed.path}"
            return url
        except:
            return url


# Global proxy manager instance
_proxy_manager = None


def get_proxy_manager() -> ProxyManager:
    """Get or create the global proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def get_next_proxy() -> Optional[str]:
    """Convenience function to get next proxy."""
    return get_proxy_manager().get_next_proxy()


def mark_proxy_failed(proxy: Optional[str]):
    """Convenience function to mark proxy as failed."""
    get_proxy_manager().mark_proxy_failed(proxy)


def get_active_provider() -> str:
    """Return active provider name for monitoring/logging."""
    return get_proxy_manager().active_provider_name
