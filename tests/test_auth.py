import unittest
import asyncio
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    verify_token,
)


class TestAuthService(unittest.TestCase):
    """Lớp kiểm thử các chức năng của dịch vụ xác thực"""

    def setUp(self):
        self.plain_password = "SecurePassword123!"
        self.plain_token = "some-long-refresh-token-value-here"

    def test_password_hashing_and_verification(self):
        """Kiểm tra mã hóa và xác thực mật khẩu"""
        hashed = hash_password(self.plain_password)
        self.assertNotEqual(self.plain_password, hashed)
        self.assertTrue(verify_password(self.plain_password, hashed))
        self.assertFalse(verify_password("WrongPassword123!", hashed))

    def test_token_hashing_and_verification(self):
        """Kiểm tra mã hóa và xác thực refresh token"""
        hashed = hash_token(self.plain_token)
        self.assertNotEqual(self.plain_token, hashed)
        self.assertTrue(verify_token(self.plain_token, hashed))
        self.assertFalse(verify_token("wrong-token-value", hashed))

    def test_access_token_creation_and_decoding(self):
        """Kiểm tra tạo và giải mã Access Token JWT"""
        data = {"sub": "user-12345", "role": "ADMIN"}
        token = create_access_token(data=data, expires_delta=timedelta(minutes=5))
        
        # Giải mã và so sánh payload
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "user-12345")
        self.assertEqual(payload["role"], "ADMIN")
        self.assertIn("exp", payload)

    def test_refresh_token_creation_and_decoding(self):
        """Kiểm tra tạo và giải mã Refresh Token JWT"""
        data = {"sub": "user-12345"}
        token = create_refresh_token(data=data, expires_delta=timedelta(days=1))
        
        # Giải mã và so sánh payload
        payload = decode_refresh_token(token)
        self.assertEqual(payload["sub"], "user-12345")
        self.assertIn("exp", payload)


if __name__ == "__main__":
    unittest.main()
