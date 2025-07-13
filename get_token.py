import base64
import requests

client_id = '2d2c5036471446d280f2ab2c3b9a1309'
client_secret = '32223d2ed5cc41fa84d32d7fd237d6e3'

# Encode to base64
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()

# Request access token
response = requests.post(
    'https://accounts.spotify.com/api/token',
    headers={
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    data={'grant_type': 'client_credentials'}
)

data = response.json()
print("Your Access Token:\n")
print(data['access_token'])
