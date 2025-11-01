import requests
import json

# Login
login_data = {
    "email": "maria@restaurantbi.com",
    "password": "123456"
}

response = requests.post("http://localhost:8000/auth/login", json=login_data)
print(f"Login status: {response.status_code}")

if response.status_code == 200:
    token = response.json()["access_token"]
    print(f"Token obtido: {token[:20]}...")
    
    # Buscar insights
    headers = {"Authorization": f"Bearer {token}"}
    params = {"start": "2025-10-26", "end": "2025-11-01"}
    
    insights_response = requests.get(
        "http://localhost:8000/analytics/insights",
        headers=headers,
        params=params
    )
    
    print(f"\nInsights status: {insights_response.status_code}")
    print(f"\nResposta completa:")
    print(json.dumps(insights_response.json(), indent=2, ensure_ascii=False))
else:
    print(f"Erro no login: {response.text}")
