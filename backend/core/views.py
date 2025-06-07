from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Create your views here.



class IndexView(APIView):
    """
    A simple API view that returns a welcome message.
    """
    
    def get(self, request):
        """
        Handle GET requests to return a welcome message.
        """
        return Response({"message": "Welcome to the backend API!"}, status=status.HTTP_200_OK)