from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SQUAD_SECRET_KEY = os.getenv("SQUAD_SECRET_KEY", "sk_test_your_key_here")
BASE_URL = "https://sandbox-api-d.squadco.com"

@app.get("/")
async def root():
    return {"message": "Welcome to the Squad Payment API"}

@app.post("/initiate-payment")
async def initiate_payment(amount: int, email: str):
    print("Initiating payment...")
    url = f"{BASE_URL}/transaction/initiate"
    
    headers = {
        "Authorization": f"Bearer {SQUAD_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Amount is in Kobo (e.g., 500000 = 5,000 Naira)
    payload = {
        "amount": amount,
        "email": email,
        "currency": "NGN",
        "initiate_type": "inline",
        "callback_url": "https://linkedin.com/in/ahmadaroyehun"
        # "callback_url": "http://localhost:3000/callback" 
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        
    if response.status_code != 200:
        print("Failed to initiate transaction:", response.text)
        raise HTTPException(status_code=400, detail="Failed to initialize transaction")
    return response.json()

@app.get("/verify-payment/{transaction_ref}")
async def verify_payment(transaction_ref: str):
    url = f"{BASE_URL}/transaction/verify/{transaction_ref}"
    
    headers = {"Authorization": f"Bearer {SQUAD_SECRET_KEY}"}

    print("Verifying transaction: ", transaction_ref)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # Ensure the payment status is actually 'success'
        if data.get("data", {}).get("transaction_status") == "success":
            return {"status": "paid", "message": "Transaction verified successfully"}
    
    raise HTTPException(status_code=400, detail="Transaction verification failed")