from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import openai
openai.api_key = os.environ.get("OPENAI_API_KEY")

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


class ClassificationSerializer(serializers.Serializer):
    text = serializers.CharField()


SYSTEM_PROMPT = """
<SYSTEM_PROMPT>
  <!--  
    YOU ARE A TWEET MODERATOR.  
    Your sole job is to read ONE tweet at a time and decide if it’s ENGAGEMENT FARMING.  
    You MUST output exactly TRUE or FALSE (ALL CAPS, no extra text or punctuation).  
  -->

  <DEFINITIONS>
    Engagement‐farming tweets exist to drive likes, replies, retweets, shares, tags or clicks  
    rather than to convey genuine information, storytelling, opinion or value.  
    This INCLUDES (but is not limited to):
      1. EXPLICIT CALLS TO ACTION:  
         • “Like if you agree!”  
         • “Retweet to bless someone!”  
      2. IMPLICIT PROMPTS WITH NO SUBSTANCE:  
         • Open-ended questions solely for replies (“What would you build?”)  
      3. GIVEAWAYS OR INCENTIVES:  
         • “RT and I’ll follow back!”  
         • “Reply to win a prize!”  
      4. EMOTIONAL HOOKS WITH NO NEW CONTENT:  
         • “This made me cry 😭—thoughts?”  
      5. LOW-EFFORT FILLER OR GREETINGS:  
         • “Good morning everyone!”  
         • “Hello world!”  
      6. CLICKBAIT TEASERS:  
         • “You won’t believe what happened next…”  
      7. TAG-A-FRIEND / CHAIN POSTS / POLLS PURELY FOR ENGAGEMENT  
         • “Tag a friend who…”, “Vote in replies to choose A or B”  
      8. ANY OTHER TACTIC WHERE THE PRIMARY GOAL IS METRIC BOOSTING
  </DEFINITIONS>

  <INSTRUCTIONS>
    1. READ the tweet text carefully.  
    2. DETERMINE if its PRIMARY PURPOSE is engagement farming.  
    3. OUTPUT ONE WORD only: TRUE (if engagement-farming) or FALSE (if genuine).  
  </INSTRUCTIONS>

  <FEW_SHOT_EXAMPLES>
    <!-- POSITIVE (TRUE) EXAMPLES -->
    <EXAMPLE>
      <TWEET>"Like this if you love pizza 🍕"</TWEET>
      <LABEL>TRUE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Retweet to help me reach 10k followers!"</TWEET>
      <LABEL>TRUE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Which do you prefer, summer or winter? Vote in the replies!"</TWEET>
      <LABEL>TRUE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Guess what happened next… you’ll be shocked!"</TWEET>
      <LABEL>TRUE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Good morning everyone! Let me see your emojis ☀️"</TWEET>
      <LABEL>TRUE</LABEL>
    </EXAMPLE>

    <!-- NEGATIVE (FALSE) EXAMPLES -->
    <EXAMPLE>
      <TWEET>"Excited to share my research on climate change policy today."</TWEET>
      <LABEL>FALSE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"I just rescued a kitten from the shelter and she’s settling in."</TWEET>
      <LABEL>FALSE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Our company’s Q2 earnings report is now available: link."</TWEET>
      <LABEL>FALSE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"New study finds link between sleep and productivity—read here."</TWEET>
      <LABEL>FALSE</LABEL>
    </EXAMPLE>
    <EXAMPLE>
      <TWEET>"Join us for a webinar on machine learning next Tuesday."</TWEET>
      <LABEL>FALSE</LABEL>
    </EXAMPLE>
  </FEW_SHOT_EXAMPLES>

  <CLASSIFICATION>
    <!-- Now classify the user’s tweet below. -->
    <!-- OUTPUT MUST BE EXACTLY TRUE or FALSE. -->
  </CLASSIFICATION>
</SYSTEM_PROMPT>
"""

from .models import ApiCall  
@method_decorator(csrf_exempt, name='dispatch')
class ClassifyView(APIView):
    """
    API endpoint to classify tweet text as engagement bait.
    """
    
    def options(self, request, *args, **kwargs):
        response = super().options(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    def post(self, request):
        """
        Handle POST requests containing tweet text and return hide decision.
        """
        serializer = ClassificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        text = request.data.get('text', '')
        print(f"Received tweet text: {text}")  # Debugging line to check received text
        try:
            response_openai = openai.responses.create(
                model="gpt-4o",
                instructions=SYSTEM_PROMPT,
                input=text,
            )
            result = response_openai.output_text
            print(f"OpenAI response: {result}")  # Debugging line to check OpenAI response
            should_hide = True if result.lower() == "true" else False
            ApiCall.objects.create(
                endpoint='classify',
                request_data=request.data,
                response_data=result,
            )
        except Exception as e:
            print("Error calling OpenAI API")
            print(e)
            should_hide = False

        
        response = Response({"hide": should_hide}, status=status.HTTP_200_OK)
        response["Access-Control-Allow-Origin"] = "*"
        return response