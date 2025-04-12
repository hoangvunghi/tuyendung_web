# notifications/consumers.py
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()
logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        logger.info(f"WebSocket kết nối mới: {self.scope['client']}")
        
        # Tạm thời chấp nhận kết nối, xác thực sẽ được xử lý sau
        await self.accept()
        
        # Lưu user_id để sử dụng sau
        self.user_id = None
        self.authenticated = False
        
        # Gửi thông báo yêu cầu xác thực
        await self.send_json({
            'type': 'auth_required',
            'message': 'Please authenticate using JWT token'
        })
        logger.info(f"Đã gửi yêu cầu xác thực tới client: {self.scope['client']}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket ngắt kết nối: {self.scope['client']} với mã {close_code}")
        
        if self.authenticated and self.user_id:
            # Chỉ rời nhóm nếu đã xác thực thành công
            try:
                logger.info(f"Rời channel_layer group cho user: {self.user_id}")
                await self.channel_layer.group_discard(
                    f"user_{self.user_id}",
                    self.channel_name
                )
            except Exception as e:
                logger.error(f"Lỗi khi rời nhóm: {str(e)}")

    async def receive_json(self, content):
        logger.info(f"Đã nhận JSON message từ client {self.scope['client']}: {content}")
        
        if not self.authenticated:
            # Xử lý xác thực
            if content.get('type') == 'authenticate':
                token = content.get('token', '')
                logger.info(f"Đang xác thực token: {token[:10]}...")
                
                try:
                    user_id = await self.get_user_from_token(token)
                    
                    if user_id:
                        self.user_id = user_id
                        self.authenticated = True
                        
                        # Đăng ký channel vào group cho user
                        try:
                            logger.info(f"Thêm vào channel_layer group cho user: {self.user_id}")
                            await self.channel_layer.group_add(
                                f"user_{self.user_id}",
                                self.channel_name
                            )
                            
                            # Thông báo xác thực thành công
                            await self.send_json({
                                'type': 'auth_success',
                                'message': 'Authentication successful'
                            })
                            logger.info(f"Xác thực thành công cho user: {self.user_id}")
                        except Exception as e:
                            logger.error(f"Lỗi khi thêm vào group: {str(e)}")
                            await self.send_json({
                                'type': 'auth_error',
                                'message': f'Server error: {str(e)}'
                            })
                    else:
                        # Thông báo xác thực thất bại
                        await self.send_json({
                            'type': 'auth_fail',
                            'message': 'Invalid token'
                        })
                        logger.warning(f"Token không hợp lệ: {token[:10]}...")
                except Exception as e:
                    logger.error(f"Lỗi xác thực: {str(e)}")
                    await self.send_json({
                        'type': 'auth_error',
                        'message': f'Authentication error: {str(e)}'
                    })
        else:
            # Đã xác thực, xử lý các message khác
            logger.info(f"Nhận message từ user đã xác thực {self.user_id}: {content}")

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Xác thực JWT token và trả về user_id"""
        try:
            # Xác thực token
            token_obj = AccessToken(token)
            user_id = token_obj['user_id']
            
            # Kiểm tra user có tồn tại
            user = User.objects.filter(id=user_id).first()
            if user:
                return user.id
            return None
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Lỗi token không hợp lệ: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Lỗi xác thực token không xác định: {str(e)}")
            return None

    async def notify(self, event):
        """Gửi thông báo tới client"""
        if self.authenticated:
            logger.info(f"Gửi thông báo tới user {self.user_id}: {event}")
            await self.send_json(event['data'])