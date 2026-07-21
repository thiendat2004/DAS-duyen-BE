# Mock API cho tính năng Thông báo (Notifications)
# Hỗ trợ giao diện NotificationBell phía Frontend hoạt động mà không bị lỗi 404

from fastapi import APIRouter, Depends
from typing import List

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/notifications/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    """Lấy số lượng thông báo chưa đọc (Mock API)"""
    return {"count": 0}


@router.get("/notifications")
async def get_notifications(limit: int = 10, current_user: User = Depends(get_current_user)):
    """Lấy danh sách thông báo gần đây (Mock API)"""
    return []


@router.patch("/notifications/mark-read")
async def mark_all_as_read(current_user: User = Depends(get_current_user)):
    """Đánh dấu tất cả thông báo là đã đọc (Mock API)"""
    return {"success": True}
