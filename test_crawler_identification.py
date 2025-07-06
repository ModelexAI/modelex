import pytest
from unittest.mock import Mock
from adapters.crawler_identification import CrawlerIdentifier, identify_crawler, get_crawler_info


class TestCrawlerIdentification:
    """Test server-managed crawler identification using IP addresses."""
    
    def setup_method(self):
        """Reset crawler identifier before each test."""
        from adapters.crawler_identification import crawler_identifier
        crawler_identifier._crawler_cache.clear()
        crawler_identifier._ip_to_crawler.clear()
    
    def test_new_crawler_identification(self):
        """Test identifying a new crawler by IP."""
        request = Mock()
        request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        crawler_id = identify_crawler(request)
        
        assert crawler_id.startswith("crawler_")
        assert len(crawler_id) > 20
        
        # Check crawler info
        info = get_crawler_info(crawler_id)
        assert info is not None
        if info:
            assert info["ip_address"] == "192.168.1.100"
            assert info["user_agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            assert info["request_count"] == 1
    
    def test_same_ip_returns_same_id(self):
        """Test that the same IP gets the same ID on subsequent requests."""
        request = Mock()
        request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        # First request
        crawler_id_1 = identify_crawler(request)
        
        # Second request (same IP, different user agent)
        request2 = Mock()
        request2.headers = {
            "User-Agent": "PerplexityBot/1.0"  # Different user agent
        }
        request2.client = Mock()
        request2.client.host = "192.168.1.100"  # Same IP
        
        crawler_id_2 = identify_crawler(request2)
        
        assert crawler_id_1 == crawler_id_2
        
        # Check that request count increased
        info = get_crawler_info(crawler_id_1)
        assert info is not None
        if info:
            assert info["request_count"] == 2
    
    def test_different_ips_get_different_ids(self):
        """Test that different IPs get different IDs."""
        # Crawler 1
        request1 = Mock()
        request1.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request1.client = Mock()
        request1.client.host = "192.168.1.100"
        
        # Crawler 2 (different IP)
        request2 = Mock()
        request2.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"  # Same user agent
        }
        request2.client = Mock()
        request2.client.host = "192.168.1.101"  # Different IP
        
        crawler_id_1 = identify_crawler(request1)
        crawler_id_2 = identify_crawler(request2)
        
        assert crawler_id_1 != crawler_id_2
    
    def test_proxy_ip_headers(self):
        """Test IP extraction from proxy headers."""
        request = Mock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"  # Proxy IP
        
        crawler_id = identify_crawler(request)
        
        # Should use the real client IP (203.0.113.1)
        info = get_crawler_info(crawler_id)
        assert info is not None
        if info:
            assert info["ip_address"] == "203.0.113.1"
    
    def test_no_ip_fallback(self):
        """Test fallback when no IP is available."""
        request = Mock()
        request.headers = {}
        request.client = None  # No client info
        
        crawler_id = identify_crawler(request)
        
        assert crawler_id == "unknown_crawler"
    
    def test_cloudflare_ip_header(self):
        """Test Cloudflare IP header extraction."""
        request = Mock()
        request.headers = {
            "CF-Connecting-IP": "203.0.113.2",
            "User-Agent": "PerplexityBot/1.0"
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"  # Proxy IP
        
        crawler_id = identify_crawler(request)
        
        # Should use Cloudflare's real IP
        info = get_crawler_info(crawler_id)
        assert info is not None
        if info:
            assert info["ip_address"] == "203.0.113.2"


def demonstrate_crawler_identification():
    """Demonstrate how IP-based crawler identification works."""
    print("=== IP-Based Crawler Identification Demo ===\n")
    
    # Reset for demo
    from adapters.crawler_identification import crawler_identifier
    crawler_identifier._crawler_cache.clear()
    crawler_identifier._ip_to_crawler.clear()
    
    # Simulate different crawlers
    crawlers = [
        {
            "name": "Chrome Browser",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "ip": "192.168.1.100"
        },
        {
            "name": "PerplexityBot (same IP)",
            "headers": {
                "User-Agent": "PerplexityBot/1.0"
            },
            "ip": "192.168.1.100"  # Same IP as first crawler
        },
        {
            "name": "Different IP",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "ip": "192.168.1.101"  # Different IP
        },
        {
            "name": "Behind Proxy",
            "headers": {
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "ip": "10.0.0.1"  # Proxy IP
        }
    ]
    
    for i, crawler in enumerate(crawlers, 1):
        print(f"Request {i}: {crawler['name']}")
        
        request = Mock()
        request.headers = crawler["headers"]
        request.client = Mock()
        request.client.host = crawler["ip"]
        
        crawler_id = identify_crawler(request)
        info = get_crawler_info(crawler_id)
        
        print(f"  Crawler ID: {crawler_id}")
        if info:
            print(f"  IP Address: {info['ip_address']}")
            print(f"  User Agent: {info['user_agent']}")
            print(f"  Request Count: {info['request_count']}")
        print()
    
    print("=== All Known Crawlers ===")
    all_crawlers = crawler_identifier.list_crawlers()
    for crawler_id, info in all_crawlers.items():
        print(f"Crawler ID: {crawler_id}")
        print(f"  IP: {info['ip_address']}")
        print(f"  Requests: {info['request_count']}")
        print(f"  First Seen: {info['first_seen']}")
        print()


if __name__ == "__main__":
    demonstrate_crawler_identification() 