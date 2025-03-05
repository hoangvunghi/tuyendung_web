from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from rest_framework import status
from .models import Interview
from .serializers import InterviewSerializer
from base.pagination import CustomPagination
from base.permissions import IsEnterpriseOwner

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interviews(request):
    """Lấy danh sách phỏng vấn"""
    if hasattr(request.user, 'enterprise'):
        # Nếu là nhà tuyển dụng
        interviews = Interview.objects.filter(enterprise=request.user.enterprise)
    else:
        # Nếu là ứng viên
        interviews = Interview.objects.filter(candidate=request.user)
    
    paginator = CustomPagination()
    paginated_interviews = paginator.paginate_queryset(interviews, request)
    serializer = InterviewSerializer(paginated_interviews, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def create_interview(request):
    """Tạo lời mời phỏng vấn"""
    serializer = InterviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(enterprise=request.user.enterprise)
        return Response({
            'message': 'Interview created successfully',
            'data': serializer.data
        }, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interviews(request):
    if hasattr(request.user, 'enterprise'):
        interviews = Interview.objects.filter(enterprise=request.user.enterprise)
    else:
        interviews = Interview.objects.filter(candidate=request.user)
    
    paginator = CustomPagination()
    paginated_interviews = paginator.paginate_queryset(interviews, request)
    serializer = InterviewSerializer(paginated_interviews, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def create_interview(request):
    serializer = InterviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(enterprise=request.user.enterprise)
        return Response({
            'message': 'Interview created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Interview creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# get_interview_detail
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interview_detail(request, pk):
    try:
        interview = Interview.objects.get(pk=pk)
        serializer = InterviewSerializer(interview)
        return Response({
            'message': 'Interview detail',
            'data': serializer.data
        }, status=200)
    except Interview.DoesNotExist:
        return Response({
            'message': 'Interview not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
# update_interview
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def update_interview(request, pk):
    try:
        interview = Interview.objects.get(pk=pk)
        serializer = InterviewSerializer(interview, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Interview updated successfully',
                'data': serializer.data
            }, status=200)
        return Response(serializer.errors, status=400)
    except Interview.DoesNotExist:
        return Response({
            'message': 'Interview not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
# delete_interview
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def delete_interview(request, pk):
    try:
        interview = Interview.objects.get(pk=pk)
        interview.delete()
        return Response({
            'message': 'Interview deleted successfully',
            'status': status.HTTP_204_NO_CONTENT
        }, status=status.HTTP_204_NO_CONTENT)
    except Interview.DoesNotExist:
        return Response({
            'message': 'Interview not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

# respond_to_interview
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_interview(request, pk):
    try:
        interview = Interview.objects.get(pk=pk)
        if hasattr(request.user, 'enterprise'):
            interview.enterprise_response = request.data.get('response')
        else:
            interview.candidate_response = request.data.get('response')
        interview.save()
        return Response({
            'message': 'Interview response updated successfully',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except Interview.DoesNotExist:
        return Response({
            'message': 'Interview not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    