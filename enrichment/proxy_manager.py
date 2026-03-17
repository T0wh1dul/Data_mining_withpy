"""
proxy_manager.py
────────────────
Handles proxy rotation and failover for HTTP/SOCKS requests.
Supports multiple proxy services with automatic fallback.
"""

import logging
import random
from typing import Optional, Dict
from urllib.parse import urlparse

from enrichment import proxy_config

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages rotating proxy selection and failover."""
    
    def __init__(self):
        self.service = proxy_config.PROXY_SERVICE
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = set()
        self._init_proxies()
    
    def _init_proxies(self):
        """Initialize proxy list based on configured service."""
        if self.service == "brightdata":
            self.proxies = self._build_brightdata_proxies()
        elif self.service == "oxylabs":
            self.proxies = self._build_oxylabs_proxies()
        elif self.service == "smartproxy":
            self.proxies = self._build_smartproxy_proxies()
        elif self.service == "manual":
            self.proxies = proxy_config.MANUAL_PROXIES
        else:
            self.proxies = []  # No proxy
        
        if self.proxies:
            logger.info(f"[PROXY] Service: {self.service} | Proxies: {len(self.proxies)}")
        else:
            logger.info("[PROXY] No proxy configured - using direct connection")
    
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
    
    def get_next_proxy(self) -> Optional[Dict]:
        """
        Get next proxy in rotation.
        Returns dict with 'http' and 'https' keys for requests library.
        Returns None for no proxy.
        """
        if not self.proxies:
            return None
        
        # Filter out failed proxies
        available = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not available:
            logger.warning("[PROXY] All proxies failed - falling back to direct connection")
            if proxy_config.PROXY_FALLBACK_TO_DIRECT:
                self.failed_proxies.clear()
                return None
            # Reset failed proxies and try again
            self.failed_proxies.clear()
            available = self.proxies
        
        proxy = random.choice(available)
        self.current_index = self.proxies.index(proxy)
        
        logger.debug(f"[PROXY] Using proxy: {self._sanitize_url(proxy)}")
        
        return {
            "http": proxy,
            "https": proxy,
        }
    
    def mark_proxy_failed(self, proxy: Optional[Dict]):
        """Mark a proxy as failed for this session."""
        if proxy and "http" in proxy:
            self.failed_proxies.add(proxy["http"])
            logger.warning(f"[PROXY] Marked failed: {self._sanitize_url(proxy['http'])}")
    
    def reset_failed_proxies(self):
        """Reset the failed proxy set."""
        self.failed_proxies.clear()
        logger.debug("[PROXY] Reset failed proxy list")
    
    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove credentials from URL for logging."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                return f"{parsed.scheme}://***:***@{parsed.netloc}{parsed.path}"
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


def get_next_proxy() -> Optional[Dict]:
    """Convenience function to get next proxy."""
    return get_proxy_manager().get_next_proxy()


def mark_proxy_failed(proxy: Optional[Dict]):
    """Convenience function to mark proxy as failed."""
    get_proxy_manager().mark_proxy_failed(proxy)
