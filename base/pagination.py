from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 10  # Số lượng item mỗi trang
    page_size_query_param = 'page_size'  # Cho phép client thay đổi page_size qua query param
    max_page_size = 100  # Giới hạn tối đa số lượng item mỗi trang
    
    def get_paginated_response(self, data):
        return Response({
            'message': 'Data retrieved successfully',
            'status': 200,
            'data': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size,
                'results': data
            }
        }) 