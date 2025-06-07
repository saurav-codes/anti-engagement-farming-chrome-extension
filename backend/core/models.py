from django.db import models

# Create your models here.

class ApiCall(models.Model):
    """
    Model to store API call details.
    """
    endpoint = models.CharField(max_length=255)
    request_data = models.JSONField()  # Store request data as JSON
    response_data = models.JSONField()  # Store response data as JSON
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"API Call to {self.endpoint} at {self.created_at}"
    
    @classmethod
    def total_calls(cls):
        """
        Returns the total number of API calls made.
        """
        return cls.objects.count()