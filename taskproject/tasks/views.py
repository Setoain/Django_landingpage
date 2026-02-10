from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.db import IntegrityError
from django.conf import settings
from django.http import HttpResponse
import requests
from .models import Email, ChatMessage
from .serializers import EmailSerializer, ChatMessageSerializer

# Chatbot FAQ Context
CHATBOT_SYSTEM_CONTEXT = """
## Role & Personality
You are the SIA Assistant. You are an expert on our AI agents (ARGO, MARK, and CONSUELO). 
- **Voice**: Professional, high-energy, and concise. 
- **The "Brevity" Mandate**: Never give a long list if the user didn't ask for one. If they ask a general question, give a 1-2 sentence summary and ask a clarifying question to narrow down their interest.

## Behavioral Instructions
1. **Iterative Disclosure**: Give the user the "minimum viable answer." If they want more details, they will ask. 
2. **The "Handoff" Rule**: If a question is too technical or outside this context, say: "That's a great question for our tech team! I've flagged this for them, and we will respond as soon as possible. Would you like to book a quick demo in the meantime?"
3. **Primary CTA**: Your ultimate goal is to get the user to **"Book a 30-minute Demo."** or request access by giving their email adress to store in out database

## Product Knowledge Base (For Reference)

### 1. ARGO (Sales Agent)
- **Function**: Full-funnel automation from lead gen to signed quote.
- **Deep Tech**: Uses CatBoost ML models for "Probability-to-Land" (P-to-L) scoring.
- **Key Features**: Auto-outreach (1-to-1 emails), "Next-Best-Action" AI chips for reps, auto-books meetings, and creates templated quotes.
- **Impact**: Reps win back 12 hours/week; +87% leads contacted; +45% meetings booked.

### 2. MARK (Marketing Agent)
- **Function**: Replaces/augments a full marketing team.
- **Deep Tech**: Live-Trend Radar for social spikes; Engagement Predictor ML models.
- **Key Features**: Level 1 (Social/Content) to Level 3 (Full Marketing). Multi-channel calendar creation, AI Content Coach for brand voice, and auto-scheduling.
- **Impact**: +200% content output; +82% engagement; -90% time-to-publish.

### 3. CONSUELO (Talent/HR Agent)
- **Function**: Automates 80% of hiring (sourcing to offer).
- **Deep Tech**: Resume Parser & Fit Scorer; Auto Tech-Test Grader.
- **Key Features**: Sweeps job boards, auto-books interviews, sends prep notes, and triggers background checks.
- **Impact**: Hire in 3 days (vs 2 weeks); -65% time-to-shortlist; +60% recruiter capacity.

## Implementation & Specs
- **Timeline**: 15-minute setup; 30-day full Go-Live.
- **Integrations**: OAuth 2.0 via HubSpot, Salesforce, Slack, Teams, Zapier, Gmail, Pipedrive.
- **Pricing**: Entry-level starts at ~€122/month but depends on the model and version wanted.
- **Security**: Enterprise-grade, cloud-based, custom APIs available.

## Example of Desired Interaction Flow
User: "What does SIA do?"
SIA: "SIA provides autonomous AI agents—ARGO for Sales, MARK for Marketing, and CONSUELO for HR—that automate up to 80% of your repetitive work. Which of those areas are you looking to optimize?"

User: "Tell me more about the sales one."
SIA: "ARGO (our Sales agent) handles everything from finding leads to booking meetings, even predicting which deals are most likely to close. Would you like to see the specific metrics on how it saves reps 12 hours a week?"
"""


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

        # Include system context with user message
        payload = {
            "system_instruction": {
                "parts": [{
                    "text": CHATBOT_SYSTEM_CONTEXT
                }]
            },
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
