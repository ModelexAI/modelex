import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from adapters.decorators import (
    modelex_paywall,
    _extract_user_id,
    _extract_auth_token,
    _verify_payment_cached,
    _check_rate_limit,
    _track_usage,
    PaymentRequiredResponse,
    RateLimitResponse,
    PhoneVerificationResponse,
    _payment_cache,
    _usage_tracking,
    _rate_limit_tracker
)


class TestModelexPaywall:
    """Test suite for modelex_paywall decorator and related functions."""
    
    def setup_method(self):
        """Reset global state before each test."""
        _payment_cache.clear()
        _usage_tracking.clear()
        _rate_limit_tracker.clear()
    
    def test_extract_auth_token_with_bearer(self):
        """Test extracting auth token with Bearer prefix."""
        request = Mock()
        request.headers = {"Authorization": "Bearer test_token_123"}
        
        result = _extract_auth_token(request)
        assert result == "test_token_123"
    
    def test_extract_auth_token_without_bearer(self):
        """Test extracting auth token without Bearer prefix."""
        request = Mock()
        request.headers = {"Authorization": "test_token_123"}
        
        result = _extract_auth_token(request)
        assert result == "test_token_123"
    
    def test_extract_auth_token_missing(self):
        """Test extracting auth token when missing."""
        request = Mock()
        request.headers = {}
        
        result = _extract_auth_token(request)
        assert result is None
    
    def test_extract_user_id_from_header(self):
        """Test extracting user ID from X-User-ID header."""
        request = Mock()
        request.headers = {"X-User-ID": "user_123"}
        
        result = _extract_user_id(request)
        assert result == "user_123"
    
    def test_extract_user_id_from_jwt(self):
        """Test extracting user ID from JWT token."""
        request = Mock()
        request.headers = {"Authorization": "Bearer jwt_token_456"}
        
        result = _extract_user_id(request)
        assert result.startswith("user_")
        assert len(result) > 10
    
    def test_extract_user_id_from_wallet(self):
        """Test extracting user ID from wallet address."""
        request = Mock()
        request.headers = {"X-Wallet-Address": "0x1234567890abcdef"}
        
        result = _extract_user_id(request)
        assert result == "wallet_0x123456"
    
    def test_extract_user_id_none(self):
        """Test extracting user ID when no identifiers present."""
        request = Mock()
        request.headers = {}
        
        result = _extract_user_id(request)
        assert result is None
    
    def test_check_rate_limit_within_limit(self):
        """Test rate limiting when within allowed limit."""
        user_id = "test_user"
        max_requests = 5
        
        # Make 4 requests (within limit)
        for i in range(4):
            result = _check_rate_limit(user_id, max_requests)
            assert result is True
        
        # Should still be within limit
        assert len(_rate_limit_tracker[user_id]) == 4
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limiting when limit exceeded."""
        user_id = "test_user"
        max_requests = 3
        
        # Make 3 requests (at limit)
        for i in range(3):
            result = _check_rate_limit(user_id, max_requests)
            assert result is True
        
        # 4th request should be blocked
        result = _check_rate_limit(user_id, max_requests)
        assert result is False
    
    def test_check_rate_limit_expires_old_requests(self):
        """Test that old requests are removed from rate limit tracking."""
        user_id = "test_user"
        max_requests = 2
        
        # Add old request (more than 60 seconds ago)
        old_time = time.time() - 70
        _rate_limit_tracker[user_id] = [old_time]
        
        # Should allow new request (old one removed)
        result = _check_rate_limit(user_id, max_requests)
        assert result is True
        assert len(_rate_limit_tracker[user_id]) == 1
    
    @patch('adapters.decorators.verify_jwt')
    def test_verify_payment_cached_jwt_success(self, mock_verify_jwt):
        """Test payment verification with JWT token (success)."""
        mock_verify_jwt.return_value = True
        
        result = asyncio.run(_verify_payment_cached(
            token="test_jwt",
            wallet=None,
            min_amount=0.01,
            user_id="test_user",
            cache_ttl=300
        ))
        
        assert result is True
        mock_verify_jwt.assert_called_once_with("test_jwt", min_amount=0.01)
    
    @patch('adapters.decorators.verify_onchain')
    def test_verify_payment_cached_wallet_success(self, mock_verify_onchain):
        """Test payment verification with wallet (success)."""
        mock_verify_onchain.return_value = True
        
        result = asyncio.run(_verify_payment_cached(
            token=None,
            wallet="0x1234567890abcdef",
            min_amount=0.01,
            user_id="test_user",
            cache_ttl=300
        ))
        
        assert result is True
        mock_verify_onchain.assert_called_once_with("0x1234567890abcdef", min_amount=0.01)
    
    def test_verify_payment_cached_no_credentials(self):
        """Test payment verification with no credentials."""
        result = asyncio.run(_verify_payment_cached(
            token=None,
            wallet=None,
            min_amount=0.01,
            user_id="test_user",
            cache_ttl=300
        ))
        
        assert result is False
    
    @patch('adapters.decorators.verify_jwt')
    def test_verify_payment_cached_uses_cache(self, mock_verify_jwt):
        """Test that payment verification uses cached results."""
        mock_verify_jwt.return_value = True
        
        # First call - should verify and cache
        result1 = asyncio.run(_verify_payment_cached(
            token="test_jwt",
            wallet=None,
            min_amount=0.01,
            user_id="test_user",
            cache_ttl=300
        ))
        
        # Second call - should use cache
        result2 = asyncio.run(_verify_payment_cached(
            token="test_jwt",
            wallet=None,
            min_amount=0.01,
            user_id="test_user",
            cache_ttl=300
        ))
        
        assert result1 is True
        assert result2 is True
        # Should only call verify_jwt once (first time)
        assert mock_verify_jwt.call_count == 1
    
    def test_track_usage(self):
        """Test usage tracking functionality."""
        user_id = "test_user"
        endpoint = "test_endpoint"
        amount = 0.01
        
        _track_usage(user_id, endpoint, amount)
        
        assert _usage_tracking[user_id][endpoint] == 0.01
        
        # Track another usage
        _track_usage(user_id, endpoint, amount)
        assert _usage_tracking[user_id][endpoint] == 0.02
    
    @patch('adapters.decorators.verify_jwt')
    @patch('adapters.decorators.check_phone_verified')
    async def test_modelex_paywall_success(self, mock_phone_verified, mock_verify_jwt):
        """Test successful payment verification and request processing."""
        mock_verify_jwt.return_value = True
        mock_phone_verified.return_value = True
        
        @modelex_paywall(price=0.01, currency="TRUSD")
        async def test_endpoint():
            return {"message": "success"}
        
        request = Mock()
        request.headers = {
            "Authorization": "Bearer test_jwt",
            "X-User-ID": "test_user"
        }
        
        result = await test_endpoint(request=request)
        
        assert result == {"message": "success"}
        mock_verify_jwt.assert_called_once_with("test_jwt", min_amount=0.01)
    
    @patch('adapters.decorators.verify_jwt')
    async def test_modelex_paywall_payment_required(self, mock_verify_jwt):
        """Test payment required response when payment fails."""
        mock_verify_jwt.return_value = False
        
        @modelex_paywall(price=0.01, currency="TRUSD")
        async def test_endpoint():
            return {"message": "success"}
        
        request = Mock()
        request.headers = {
            "Authorization": "Bearer test_jwt",
            "X-User-ID": "test_user"
        }
        
        result = await test_endpoint(request=request)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 402
        content = result.body.decode()
        assert "Payment required" in content
        assert "0.01" in content
        assert "TRUSD" in content
    
    async def test_modelex_paywall_rate_limit_exceeded(self):
        """Test rate limit exceeded response."""
        @modelex_paywall(price=0.01, rate_limit=1)
        async def test_endpoint():
            return {"message": "success"}
        
        request = Mock()
        request.headers = {"X-User-ID": "test_user"}
        
        # First request should succeed (no payment, but rate limit allows)
        result1 = await test_endpoint(request=request)
        assert isinstance(result1, JSONResponse)
        assert result1.status_code == 402  # Payment required
        
        # Second request should be rate limited
        result2 = await test_endpoint(request=request)
        assert isinstance(result2, JSONResponse)
        assert result2.status_code == 429  # Rate limit exceeded
    
    @patch('adapters.decorators.check_phone_verified')
    async def test_modelex_paywall_phone_verification_required(self, mock_phone_verified):
        """Test phone verification required response."""
        mock_phone_verified.return_value = False
        
        @modelex_paywall(price=0.01, phone_required=True)
        async def test_endpoint():
            return {"message": "success"}
        
        request = Mock()
        request.headers = {
            "Authorization": "Bearer test_jwt",
            "X-User-ID": "test_user"
        }
        
        # Mock successful payment verification
        with patch('adapters.decorators.verify_jwt', return_value=True):
            result = await test_endpoint(request=request)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 402
        content = result.body.decode()
        assert "Phone verification required" in content
    
    def test_payment_required_response_model(self):
        """Test PaymentRequiredResponse model validation."""
        response = PaymentRequiredResponse(
            price=0.01,
            currency="TRUSD"
        )
        
        assert response.error == "Payment required"
        assert response.price == 0.01
        assert response.currency == "TRUSD"
        assert response.payment_endpoint == "https://pay.modelex.ai/pay"
        assert response.phone_required is False
    
    def test_rate_limit_response_model(self):
        """Test RateLimitResponse model validation."""
        response = RateLimitResponse(
            retry_after=60,
            requests_per_minute=10
        )
        
        assert response.error == "Rate limit exceeded"
        assert response.retry_after == 60
        assert response.requests_per_minute == 10
    
    def test_phone_verification_response_model(self):
        """Test PhoneVerificationResponse model validation."""
        response = PhoneVerificationResponse(
            verify_url="https://custom.verify.com"
        )
        
        assert response.error == "Phone verification required"
        assert response.verify_url == "https://custom.verify.com"


class TestModelexPaywallIntegration:
    """Integration tests for modelex_paywall decorator."""
    
    def setup_method(self):
        """Reset global state before each test."""
        _payment_cache.clear()
        _usage_tracking.clear()
        _rate_limit_tracker.clear()
    
    @patch('adapters.decorators.verify_jwt')
    @patch('adapters.decorators.check_phone_verified')
    async def test_full_payment_flow(self, mock_phone_verified, mock_verify_jwt):
        """Test complete payment flow with caching and usage tracking."""
        mock_verify_jwt.return_value = True
        mock_phone_verified.return_value = True
        
        @modelex_paywall(
            price=0.01,
            currency="TRUSD",
            rate_limit=10,
            cache_ttl=300
        )
        async def test_endpoint():
            return {"message": "success"}
        
        request = Mock()
        request.headers = {
            "Authorization": "Bearer test_jwt",
            "X-User-ID": "test_user"
        }
        
        # First request
        result1 = await test_endpoint(request=request)
        assert result1 == {"message": "success"}
        
        # Second request (should use cache)
        result2 = await test_endpoint(request=request)
        assert result2 == {"message": "success"}
        
        # Verify JWT was only called once (cached on second call)
        assert mock_verify_jwt.call_count == 1
        
        # Verify usage was tracked
        assert _usage_tracking["test_user"]["test_endpoint"] == 0.02
    
    async def test_multiple_users_rate_limiting(self):
        """Test that rate limiting works independently for different users."""
        @modelex_paywall(price=0.01, rate_limit=2)
        async def test_endpoint():
            return {"message": "success"}
        
        # User 1 makes 2 requests
        request1 = Mock()
        request1.headers = {"X-User-ID": "user1"}
        
        result1 = await test_endpoint(request=request1)
        result2 = await test_endpoint(request=request1)
        
        # User 2 makes 2 requests (should be allowed)
        request2 = Mock()
        request2.headers = {"X-User-ID": "user2"}
        
        result3 = await test_endpoint(request=request2)
        result4 = await test_endpoint(request=request2)
        
        # All should be payment required (no actual payment), not rate limited
        assert result1.status_code == 402
        assert result2.status_code == 402
        assert result3.status_code == 402
        assert result4.status_code == 402


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 