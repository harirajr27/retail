import hmac
import hashlib
import time
from fastapi import FastAPI, Depends, HTTPException, Header, Request, status, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

API_KEY_ENV = "super_secret_master_token"
WEBHOOK_SECRET = "webhook_secret_phrase"

MOCK_CUSTOMERS = {
    1: {"id": 1, "name": "Arun", "city": "Chennai"},
    2: {"id": 2, "name": "Priya", "city": "Mumbai"}
}

class CustomerModel(BaseModel):
    name: str
    city: str

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key header missing")
    if x_api_key != API_KEY_ENV:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

@app.post("/customers", status_code=201, dependencies=[Depends(verify_api_key)])
def create_customer(customer: CustomerModel):
    if any(c["name"] == customer.name for c in MOCK_CUSTOMERS.values()):
        raise HTTPException(status_code=409, detail="Conflict")
    new_id = max(MOCK_CUSTOMERS.keys(), default=0) + 1
    MOCK_CUSTOMERS[new_id] = {"id": new_id, "name": customer.name, "city": customer.city}
    return MOCK_CUSTOMERS[new_id]

@app.get("/customers", dependencies=[Depends(verify_api_key)])
def get_all_customers(page: int = Query(1, ge=1), per_page: int = Query(5, ge=1)):
    items = list(MOCK_CUSTOMERS.values())
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]

@app.get("/customers/{id}", dependencies=[Depends(verify_api_key)])
def get_customer_by_id(id: int):
    if id not in MOCK_CUSTOMERS:
        raise HTTPException(status_code=404, detail="Not Found")
    return MOCK_CUSTOMERS[id]

@app.put("/customers/{id}", dependencies=[Depends(verify_api_key)])
def update_customer(id: int, customer: CustomerModel):
    if id not in MOCK_CUSTOMERS:
        raise HTTPException(status_code=404, detail="Not Found")
    MOCK_CUSTOMERS[id].update(customer.dict())
    return MOCK_CUSTOMERS[id]

@app.delete("/customers/{id}", status_code=204, dependencies=[Depends(verify_api_key)])
def delete_customer(id: int):
    if id not in MOCK_CUSTOMERS:
        raise HTTPException(status_code=404, detail="Not Found")
    MOCK_CUSTOMERS.pop(id)
    return

@app.post("/webhooks/order-events")
async def receive_webhook_event(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Signature")
    computed = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, signature):
        raise HTTPException(status_code=401, detail="Tampered Signature")
    return {"status": "success"}

@app.post("/token")
def mock_token_refresh():
    return {"access_token": "mocked_bearer_jwt_token", "expires_in": 3600}

client = TestClient(app)

def fetch_all(base_url=""):
    current_page = 1
    per_page = 5
    all_records = []
    has_refreshed = False
    
    while True:
        headers = {"X-API-Key": VALID_KEY, "Authorization": "Bearer expired_token"}
        if has_refreshed:
            headers["Authorization"] = "Bearer refreshed_token"
            
        response = client.get(f"/customers?page={current_page}&per_page={per_page}", headers=headers)
        
        if response.status_code == 401 and not has_refreshed:
            token_res = client.post("/token")
            has_refreshed = True
            continue
            
        if response.status_code != 200:
            break
            
        data = response.json()
        if not data:
            break
            
        all_records.extend(data)
        
        if response.headers.get("X-RateLimit-Remaining") == "0":
            time.sleep(0.1)
            
        current_page += 1
    return response.status_code

VALID_KEY = "super_secret_master_token"

def test_suite():
    passed_count = 0
    
    res = client.get("/customers?page=1&per_page=5", headers={"X-API-Key": VALID_KEY})
    if res.status_code == 200: passed_count += 1
        
    res = client.get("/customers", headers={})
    if res.status_code == 401: passed_count += 1
        
    res = client.get("/customers", headers={"X-API-Key": "wrong"})
    if res.status_code == 403: passed_count += 1
        
    res = client.get("/customers/999", headers={"X-API-Key": VALID_KEY})
    if res.status_code == 404: passed_count += 1
        
    res = client.post("/customers", json={"name": "Arun", "city": "Chennai"}, headers={"X-API-Key": VALID_KEY})
    if res.status_code == 409: passed_count += 1
        
    res = client.post("/customers", json={"city": "MissingNameField"}, headers={"X-API-Key": VALID_KEY})
    if res.status_code == 422: passed_count += 1
        
    body = b'{"id": 105}'
    sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    res = client.post("/webhooks/order-events", content=body, headers={"X-Signature": sig})
    if res.status_code == 200: passed_count += 1
        
    res = client.post("/webhooks/order-events", content=body, headers={"X-Signature": "tampered"})
    if res.status_code == 401: passed_count += 1
        
    print(f"{passed_count} passed | GET /customers?page=1&per_page=5 -> {client.get('/customers?page=1&per_page=5', headers={'X-API-Key': VALID_KEY}).status_code}")
    print(f"Webhook tampered -> {res.status_code}")

if __name__ == "__main__":
    test_suite()
