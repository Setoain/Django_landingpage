from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.db import IntegrityError
from django.conf import settings
import requests
from .models import Email, ChatMessage
from .serializers import EmailSerializer, ChatMessageSerializer


@api_view(['POST'])
@throttle_classes([AnonRateThrottle])


def join_waitlist(request):
    serializer = EmailSerializer(data=request.data)

    if serializer.is_valid():
        try:
            email_entry = serializer.save()
            
            return Response(
                {
                    'success': True,
                    'message': 'Successfully joined the waitlist!',
                    'email': email_entry.email
                },
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            return Response(
                {
                    'success': False,
                    'error': 'This email is already on the waitlist'
                },
                status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            print(f"Error: {e}")
            return Response(
                {
                    'success': False,
                    'error': 'Something went wrong. Please try again.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response(
        {
            'success': False,
            'error': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
def waitlist_stats(request):
    total_count = Email.objects.count()
    all_emails = Email.objects.all()
    serializer = EmailSerializer(all_emails, many=True)

    return Response({
        'total_subscribers': total_count,
        'subscribers': serializer.data
    })


@api_view(['POST'])
@throttle_classes([AnonRateThrottle])
def chatbot(request):
    try:
        message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id', None)

        if not message:
            return Response(
                {
                    'success': False,
                    'error': 'Message is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call Gemini API using REST endpoint
        api_key = settings.GEMINI_API_KEY
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            "contents": [{
                "parts": [{
                    "text": message
                }]
            }]
        }

        # Make API request
        gemini_response = requests.post(url, headers=headers, json=payload, timeout=30)
        gemini_response.raise_for_status()

        # Extract AI response
        response_data = gemini_response.json()
        ai_response = response_data['candidates'][0]['content']['parts'][0]['text']

        chat_message = ChatMessage.objects.create(
            message=message,
            response=ai_response,
            session_id=session_id
        )

        serializer = ChatMessageSerializer(chat_message)

        return Response(
            {
                'success': True,
                'message': message,
                'response': ai_response,
                'timestamp': chat_message.timestamp
            },
            status=status.HTTP_200_OK
        )

    except requests.exceptions.RequestException as e:
        print(f"Chatbot API Error: {e}")
        return Response(
            {
                'success': False,
                'error': 'Failed to connect to AI service. Please try again.',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except KeyError as e:
        print(f"Chatbot Response Parse Error: {e}")
        return Response(
            {
                'success': False,
                'error': 'Unexpected response from AI service.',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return Response(
            {
                'success': False,
                'error': 'Failed to generate response. Please try again.',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )