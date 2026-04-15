"""
views.py snippet for Django REST Framework
- Place predictor.py in your Django app (same folder or importable)
- Add endpoint to call predict_from_text and return JSON
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from . import predictor   # adapte l'import selon l'organisation

@api_view(["POST"])
def predict_view(request):
    """
    POST payload: { "message": "I have chest pain and dizziness", "top_k": 3 }
    Response: {
       "symptoms_detected": [...],
       "predictions": [{"disease": "...", "prob": 0.6}, ...],
       "urgency": "URGENT",
       "urgency_score": 18.0
    }
    """
    data = request.data or {}
    message = data.get("message", "")
    top_k = int(data.get("top_k", 3))
    if not message:
        return Response({"error": "message required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        # optionally load severity mapping from a file if you saved it earlier
        sev_map = None
        res = predictor.predict_from_text(message, top_k=top_k, sev_map=sev_map)
        return Response(res)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)