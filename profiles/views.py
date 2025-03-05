from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from .models import UserInfo, Cv
from .serializers import UserInfoSerializer, CvSerializer
from base.permissions import IsProfileOwner, IsCvOwner, CanManageCv
from base.pagination import CustomPagination


# Create your views here.
@api_view(["POST"])
@permission_classes([AllowAny])
def create_user_info(request):
    serializer = UserInfoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "UserInfo created successfully",
            "status": status.HTTP_201_CREATED,
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        "message": "Failed to create UserInfo",
        "status": status.HTTP_400_BAD_REQUEST,
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfileOwner])
def get_profile(request):
    profile = get_object_or_404(UserInfo, user=request.user)
    serializer = UserInfoSerializer(profile)
    return Response({
        'message': 'Profile retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsProfileOwner])
def update_profile(request):
    profile = get_object_or_404(UserInfo, user=request.user)
    serializer = UserInfoSerializer(profile, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profile updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Profile update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# @api_view(["DELETE"])
# @permission_classes([AllowAny])
# def delete_user_info(request, pk):
#     try:
#         user_info = UserInfo.objects.get(pk=pk)
#         user_info.delete()
#         return Response({
#             "message": "UserInfo deleted successfully",
#             "status": status.HTTP_204_NO_CONTENT
#         }, status=status.HTTP_204_NO_CONTENT)
#     except UserInfo.DoesNotExist:
#         return Response({
#             "message": "UserInfo not found",
#             "status": status.HTTP_404_NOT_FOUND
#         }, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_cvs(request):
    cvs = Cv.objects.filter(user=request.user)
    serializer = CvSerializer(cvs, many=True)
    return Response({
        'message': 'CVs retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, CanManageCv])
def get_cv_detail(request, pk):
    cv = get_object_or_404(Cv, pk=pk)
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cv(request):
    serializer = CvSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'CV created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'CV creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsCvOwner])
def update_cv(request, pk):
    cv = get_object_or_404(Cv, pk=pk, user=request.user)
    serializer = CvSerializer(cv, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'CV updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'CV update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, CanManageCv])
def update_cv_status(request, pk):
    cv = get_object_or_404(Cv, pk=pk)
    status_value = request.data.get('status')
    note = request.data.get('note', '')
    
    if status_value not in ['pending', 'approved', 'rejected']:
        return Response({
            'message': 'Invalid status value',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    cv.status = status_value
    cv.note = note
    cv.save()
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV status updated successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_cv(request, pk):
    try:
        cv = Cv.objects.get(pk=pk)
        cv.delete()
        return Response({
            "message": "Cv deleted successfully",
            "status": status.HTTP_204_NO_CONTENT
        }, status=status.HTTP_204_NO_CONTENT)
    except Cv.DoesNotExist:
        return Response({
            "message": "Cv not found",
            "status": status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
# profiles/views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cv(request):
    """Tạo CV mới"""
    serializer = CvSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'CV created successfully',
            'data': serializer.data
        }, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_cvs(request):
    cvs = Cv.objects.filter(user=request.user)
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvSerializer(paginated_cvs, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cv(request):
    serializer = CvSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'CV created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'CV creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# mark_cv
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_cv(request, pk):
    """Đánh dấu CV"""
    cv = get_object_or_404(Cv, pk=pk)
    cv.is_marked = not cv.is_marked
    cv.save()
    return Response({
        'message': 'CV marked successfully',
        'status': status.HTTP_200_OK
    }, status=status.HTTP_200_OK)

# view_cv
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def view_cv(request, pk):
    """Xem CV"""
    cv = get_object_or_404(Cv, pk=pk)
    cv.is_viewed = True
    cv.save()
    return Response({
        'message': 'CV viewed successfully',
        'status': status.HTTP_200_OK
    }, status=status.HTTP_200_OK)
