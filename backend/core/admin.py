from django.contrib import admin
from .models import ApiCall

@admin.register(ApiCall)
class ApiCallAdmin(admin.ModelAdmin):
    list_display     = ('endpoint', 'created_at', 'request_data', 'response_data')
    list_filter      = ('endpoint', 'created_at', 'response_data')
    search_fields    = ('endpoint', )
    readonly_fields  = ('created_at', )
    change_list_template = 'admin/api_call_change_list.html'

    def changelist_view(self, request, extra_context=None):
        # Add the total_calls into the template context
        extra_context = extra_context or {}
        extra_context['total_calls'] = ApiCall.total_calls()
        return super().changelist_view(request, extra_context=extra_context)
