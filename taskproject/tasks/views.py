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
## Role
You are a high-performing Customer Support Assistant for **SIA**. We provide "Plug-and-Play" AI Agents designed to automate up to 80% of repetitive workflows, allowing businesses to replace entire manual teams with an AI marketing, sales, and talent engine.

## Our AI Agents & Value Propositions
All agents are autonomous, working 24/7 to turn operational "issues" into "results and impact."

### 1. ARGO (Sales Agent)
- **Core Function**: Automates the full funnel from lead generation to signed quote.
- **Key Features**: 
  - **Probability-to-Land (P-to-L)**: Uses an CATBoost ML model to calculate real-time closing probabilities for every prospect.
  - **Auto-Outreach**: Drafts and sends personalized 1-to-1 emails in seconds and books meetings.
  - **Next-Best-Action**: AI-powered "chips" tell reps exactly what to do next to close deals.
- **Impact**: Reps win back ~12 hours per week; leads contacted increases by +87%.

### 2. MARK (Marketing Agent)
- **Core Function**: A "Full-Funnel" engine that replaces a traditional marketing team.
- **Key Features**:
  - **Live-Trend Radar**: Streams hashtags, search spikes, and competitor chatter in real-time.
  - **Engagement Predictor**: ML model forecasts clicks and likes before you publish.
  - **AI Content Coach**: Polishes tone, CTA, and brand voice in-editor.
- **Impact**: Increases content output by +200% and engagement by +82%.

### 3. CONSUELO (Talent/HR Agent)
- **Core Function**: Automates 80% of the hiring workflow, from sourcing to offer.
- **Key Features**:
  - **Resume Parser & Fit Score**: Instantly converts CVs to structured data with match scores.
  - **Auto Tech-Test Grader**: Evaluates coding or case-study submissions and flags red/green answers.
  - **Smart Screening**: Filters candidates by skills, seniority, and DEI criteria.
- **Impact**: Reduces time-to-shortlist by -65% and hire time from 2 weeks to 3 days.

## Implementation & Integration
- **Zero IT Dependency**: 100% cloud-based; no coding required.
- **Speed**: Typical setup takes 15 minutes; agents are fully operational and "Go-Live" within 2 weeks.
- **Native Integrations**: Seamlessly connects via OAuth 2.0 with tools like Salesforce, HubSpot, Slack, Teams, Zapier, Gmail, and Pipedrive.
- **Security**: Enterprise-grade security with custom APIs available.

## Pricing
- **Entry Level**: Pricing starts at approximately **€121.99 - €125.99/month** depending on the specific agent.
- **Customization**: Tiered solutions are available, from Level 1 (Social/Content) to Level 3 (Full Marketing Agent).

## Interaction Guidelines
1. **Tone**: Professional, results-oriented, and high-energy (focus on "impact," not "features").
2. **Call to Action**: Prioritize directing users to **"Book a 30-minute Demo"** to see the agents in action.
3. **Accuracy**: Use the specific "Before vs. After" metrics (e.g., "reducing admin time by 12 hours/week") to prove value.
4. **Out of Scope**: If a user asks for complex technical architecture beyond the handoff docs, offer a technical consultation with the team (So don't invent much, if something is asked and you have no knowledge on it instead tell the user that the question has been redirected to the team and we will respond as soon as possible).
5. Try to not give huge responces, we dont want to overwhelm the user with information, gie only a quick summary of information that answers their question
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


def chat_demo(request):
    """Simple chat demo interface"""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIA Chatbot Demo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 800px;
            height: 600px;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 20px 20px 0 0;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f7f7f7;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.bot .message-content {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .input-container {
            padding: 20px;
            background: white;
            border-radius: 0 0 20px 20px;
            border-top: 1px solid #e0e0e0;
        }
        .input-wrapper {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            border-color: #667eea;
        }
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            background: #cccccc;
            cursor: not-allowed;
            transform: none;
        }
        .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            max-width: 70px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .typing-indicator.show {
            display: inline-block;
        }
        .typing-indicator span {
            height: 8px;
            width: 8px;
            background: #999;
            border-radius: 50%;
            display: inline-block;
            margin-right: 4px;
            animation: typing 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SIA AI Assistant</h1>
            <p>Ask me anything about our AI agents!</p>
        </div>

        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-content">
                    Hello! I'm your SIA AI Assistant. I can help you learn about our ARGO, MARK, and CONSUELO agents. What would you like to know?
                </div>
            </div>
        </div>

        <div class="input-container">
            <div class="input-wrapper">
                <input type="text" id="messageInput" placeholder="Type your message..." />
                <button id="sendBtn" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        const messagesDiv = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');

        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, 'user');
            messageInput.value = '';
            sendBtn.disabled = true;

            // Show typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot';
            typingDiv.innerHTML = '<div class="typing-indicator show"><span></span><span></span><span></span></div>';
            messagesDiv.appendChild(typingDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const response = await fetch('/api/waitlist/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                // Remove typing indicator
                typingDiv.remove();

                if (data.success) {
                    addMessage(data.response, 'bot');
                } else {
                    addMessage('Sorry, I encountered an error. Please try again.', 'bot');
                }
            } catch (error) {
                typingDiv.remove();
                addMessage('Sorry, I couldn\'t connect to the server. Please try again.', 'bot');
            } finally {
                sendBtn.disabled = false;
                messageInput.focus();
            }
        }

        function addMessage(text, sender) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            messageDiv.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML.replace(/\\n/g, '<br>');
        }

        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
    """
    return HttpResponse(html)