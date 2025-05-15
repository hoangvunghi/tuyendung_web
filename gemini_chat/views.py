from django.shortcuts import render
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .serializers import GeminiChatSessionSerializer, GeminiChatMessageSerializer, ChatRequestSerializer
from .models import GeminiChatSession, GeminiChatMessage
from .services import GeminiChatService

import uuid
import google.generativeai as genai
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ChatSessionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

@swagger_auto_schema(
    method='post',
    operation_description="Gửi tin nhắn và nhận phản hồi từ Gemini AI",
    request_body=ChatRequestSerializer,
    responses={
        200: openapi.Response(
            description="Successful response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'session_id': openapi.Schema(type=openapi.TYPE_STRING),
                            'response': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """API endpoint để gửi tin nhắn tới Gemini chatbot và nhận phản hồi"""
    serializer = ChatRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'message': 'Dữ liệu không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    message = serializer.validated_data['message']
    session_id = serializer.validated_data.get('session_id')
    
    # Khởi tạo service
    chat_service = GeminiChatService()
    
    try:
        # Gửi tin nhắn và nhận phản hồi
        result = chat_service.send_message(request.user, message, session_id)
        
        # Trả về kết quả
        return Response({
            'message': 'Gửi tin nhắn thành công',
            'status': status.HTTP_200_OK,
            'data': {
                'session_id': str(result['session_id']),
                'response': result['assistant_message']['content']
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'message': f'Lỗi khi xử lý tin nhắn: {str(e)}',
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách phiên chat",
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng phiên mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_sessions(request):
    """API endpoint để lấy danh sách phiên chat của người dùng"""
    sessions = GeminiChatSession.objects.filter(user=request.user)
    
    # Phân trang
    paginator = ChatSessionPagination()
    paginated_sessions = paginator.paginate_queryset(sessions, request)
    
    serializer = GeminiChatSessionSerializer(paginated_sessions, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy chi tiết phiên chat và tin nhắn",
    responses={
        200: openapi.Response(
            description="Successful response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="Phiên chat không tồn tại",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_session(request, session_id):
    """API endpoint để lấy chi tiết phiên chat và tin nhắn"""
    # Đảm bảo session_id hợp lệ
    if session_id == 'undefined' or session_id is None:
        return Response({
            'message': 'ID phiên chat không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # Nếu session_id là ID số nguyên (từ DB cũ), chuyển đổi
        try:
            # Cố gắng parse thành số nguyên nếu là kiểu cũ
            id_value = int(session_id)
            session = GeminiChatSession.objects.get(id=id_value, user=request.user)
        except (ValueError, TypeError):
            # Nếu không phải số nguyên, sử dụng trực tiếp
            session = GeminiChatSession.objects.get(id=session_id, user=request.user)
    except GeminiChatSession.DoesNotExist:
        return Response({
            'message': 'Phiên chat không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = GeminiChatSessionSerializer(session)
    return Response({
        'message': 'Lấy chi tiết phiên chat thành công',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo phiên chat mới",
    responses={
        201: openapi.Response(
            description="Phiên chat được tạo thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """API endpoint để tạo phiên chat mới"""
    chat_service = GeminiChatService()
    session = chat_service.create_chat_session(request.user)
    
    serializer = GeminiChatSessionSerializer(session)
    return Response({
        'message': 'Tạo phiên chat mới thành công',
        'status': status.HTTP_201_CREATED,
        'data': serializer.data
    }, status=status.HTTP_201_CREATED)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa phiên chat",
    responses={
        204: openapi.Response(
            description="Phiên chat đã được xóa thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Phiên chat không tồn tại",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chat_session(request, session_id):
    """API endpoint để xóa phiên chat"""
    try:
        session = GeminiChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
        return Response({
            'message': 'Xóa phiên chat thành công',
            'status': status.HTTP_204_NO_CONTENT
        }, status=status.HTTP_204_NO_CONTENT)
    except GeminiChatSession.DoesNotExist:
        return Response({
            'message': 'Phiên chat không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='post',
    operation_description="Đóng phiên chat (đánh dấu không còn hoạt động)",
    responses={
        200: openapi.Response(
            description="Phiên chat đã được đóng thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="Phiên chat không tồn tại",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_chat_session(request, session_id):
    """API endpoint để đóng phiên chat (đánh dấu không còn hoạt động)"""
    try:
        session = GeminiChatSession.objects.get(id=session_id, user=request.user)
        session.is_active = False
        session.save()
        
        serializer = GeminiChatSessionSerializer(session)
        return Response({
            'message': 'Đóng phiên chat thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except GeminiChatSession.DoesNotExist:
        return Response({
            'message': 'Phiên chat không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật tiêu đề phiên chat",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Tiêu đề mới cho phiên chat"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Tiêu đề đã được cập nhật thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Dữ liệu không hợp lệ",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_chat_session_title(request, pk):
    """API endpoint để cập nhật tiêu đề phiên chat"""
    try:
        chat_session = GeminiChatSession.objects.get(id=pk, user=request.user)
    except GeminiChatSession.DoesNotExist:
        return Response({
            'message': 'Phiên chat không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    title = request.data.get('title', '').strip()
    
    if not title:
        return Response({
            'message': 'Tiêu đề không được để trống',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': {'title': ['Tiêu đề không được để trống']}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Tối ưu tiêu đề nếu quá dài
    if len(title) > 100:
        words = title.split()
        if len(words) > 15:
            title = ' '.join(words[:15]) + '...'
        else:
            title = title[:100] + '...'
    
    chat_session.title = title
    chat_session.save()
    
    serializer = GeminiChatSessionSerializer(chat_session)
    
    return Response({
        'message': 'Cập nhật tiêu đề thành công',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    }, status=status.HTTP_200_OK)