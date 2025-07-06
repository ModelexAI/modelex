import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import Request
from collections import defaultdict


class CrawlerIdentifier:
    """Server-managed crawler identification using IP addresses."""
    
    def __init__(self):
        self._crawler_cache: Dict[str, Dict[str, Any]] = {}
        self._ip_to_crawler: Dict[str, str] = {}
    
    def identify_crawler(self, request: Request) -> str:
        """
        Identify crawler using IP address.
        
        Returns:
            str: Unique crawler ID that persists across requests
        """
        # Get client IP address
        ip_address = self._get_client_ip(request)
        if not ip_address:
            # Fallback to a default ID if no IP available
            return "unknown_crawler"
        
        # Check if we've seen this IP before
        if ip_address in self._ip_to_crawler:
            crawler_id = self._ip_to_crawler[ip_address]
            self._update_crawler_info(crawler_id, request)
            return crawler_id
        
        # Create new crawler ID for this IP
        crawler_id = self._create_new_crawler_id(request, ip_address)
        return crawler_id
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check various headers for real IP (behind proxy/load balancer)
        ip_headers = [
            "X-Forwarded-For",
            "X-Real-IP", 
            "X-Client-IP",
            "CF-Connecting-IP",  # Cloudflare
            "X-Forwarded",
            "Forwarded-For",
            "Forwarded"
        ]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # Take first IP if multiple (X-Forwarded-For can have multiple)
                return ip.split(",")[0].strip()
        
        # Fallback to direct client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None
    
    def _create_new_crawler_id(self, request: Request, ip_address: str) -> str:
        """Create new crawler ID and store metadata."""
        # Generate unique ID based on IP and timestamp
        timestamp = int(time.time() * 1000)  # milliseconds
        ip_hash = hashlib.md5(ip_address.encode()).hexdigest()[:8]
        crawler_id = f"crawler_{ip_hash}_{timestamp}"
        
        # Store crawler information
        crawler_info = {
            "id": crawler_id,
            "ip_address": ip_address,
            "user_agent": request.headers.get("User-Agent", ""),
            "first_seen": timestamp,
            "last_seen": timestamp,
            "request_count": 1,
            "headers": dict(request.headers)
        }
        
        # Update mappings
        self._crawler_cache[crawler_id] = crawler_info
        self._ip_to_crawler[ip_address] = crawler_id
        
        return crawler_id
    
    def _update_crawler_info(self, crawler_id: str, request: Request) -> None:
        """Update existing crawler information."""
        if crawler_id in self._crawler_cache:
            self._crawler_cache[crawler_id]["last_seen"] = int(time.time() * 1000)
            self._crawler_cache[crawler_id]["request_count"] += 1
    
    def get_crawler_info(self, crawler_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific crawler."""
        return self._crawler_cache.get(crawler_id)
    
    def list_crawlers(self) -> Dict[str, Dict[str, Any]]:
        """Get all known crawlers."""
        return self._crawler_cache.copy()
    
    def cleanup_old_crawlers(self, max_age_hours: int = 24) -> int:
        """Remove crawlers that haven't been seen recently."""
        cutoff_time = int(time.time() * 1000) - (max_age_hours * 3600 * 1000)
        removed_count = 0
        
        crawlers_to_remove = []
        for crawler_id, info in self._crawler_cache.items():
            if info["last_seen"] < cutoff_time:
                crawlers_to_remove.append(crawler_id)
        
        for crawler_id in crawlers_to_remove:
            info = self._crawler_cache[crawler_id]
            # Remove from IP mapping
            if info["ip_address"] in self._ip_to_crawler:
                del self._ip_to_crawler[info["ip_address"]]
            # Remove from cache
            del self._crawler_cache[crawler_id]
            removed_count += 1
        
        return removed_count


# Global instance
crawler_identifier = CrawlerIdentifier()


def identify_crawler(request: Request) -> str:
    """Convenience function to identify crawler from request."""
    return crawler_identifier.identify_crawler(request)


def get_crawler_info(crawler_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific crawler."""
    return crawler_identifier.get_crawler_info(crawler_id) 