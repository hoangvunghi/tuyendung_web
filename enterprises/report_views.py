from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import ReportPostSerializer
from .models import ReportPostEntity, PostEntity
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='post',
    operation_description="Báo cáo bài đăng vi phạm",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['post', 'reason'],
        properties={
            'post': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của bài đăng"),
            'reason': openapi.Schema(type=openapi.TYPE_STRING, description="Lý do báo cáo"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Báo cáo đã được gửi thành công",
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
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_post(request):
    """
    API cho phép người dùng báo cáo bài đăng vi phạm
    """
    serializer = ReportPostSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # Kiểm tra xem người dùng đã báo cáo bài đăng này chưa
        post_id = serializer.validated_data.get('post').id
        user = request.user
        
        existing_report = ReportPostEntity.objects.filter(post_id=post_id, user=user).exists()
        if existing_report:
            return Response({
                'message': 'Bạn đã báo cáo bài đăng này trước đó',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Lưu báo cáo mới
        report = serializer.save()
        
        return Response({
            'message': 'Báo cáo đã được gửi thành công',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'message': 'Dữ liệu không hợp lệ',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# API để lấy danh sách báo cáo của người dùng
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách báo cáo của người dùng",
    responses={
        200: openapi.Response(
            description="Danh sách báo cáo",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        ),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_reports(request):
    """
    API để lấy danh sách báo cáo của người dùng
    """
    reports = ReportPostEntity.objects.filter(user=request.user).order_by('-created_at')
    serializer = ReportPostSerializer(reports, many=True)
    
    return Response({
        'message': 'Lấy danh sách báo cáo thành công',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    }, status=status.HTTP_200_OK)
