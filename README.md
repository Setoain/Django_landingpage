# Django_landingpage

Use link: http://127.0.0.1:8000/api/waitlist/stats/ 
replacing 127.0.0.1:8000 with local url given in order to see the view with subscriber count and list.

For easier testing use command: Invoke-RestMethod -Uri http://127.0.0.1:8000/api/waitlist/join/ -Method Post -Body '{"email": "setoain@example.com"}' -ContentType "application/json"
change email and see if it updates in supabase (should be working)

Code is working only locally so next steps involves connecting this and supabase to the frontend.
