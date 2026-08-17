from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from users.permissions import IsHRAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get(self, request):
        queryset = AuditLog.objects.select_related('user').all()

        # Optional filters
        model = request.query_params.get('model')
        action = request.query_params.get('action')
        user_id = request.query_params.get('user')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if model:
            queryset = queryset.filter(model_name__iexact=model)
        if action:
            queryset = queryset.filter(action__iexact=action)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        paginator = StandardPagination()
        paginated = paginator.paginate_queryset(queryset, request)
        serializer = AuditLogSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)