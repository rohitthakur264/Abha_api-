# ProDoc ABDM Integration Middleware (FastAPI)

Production-ready Python FastAPI middleware integrating **ABDM (Ayushman Bharat Digital Mission)** Milestone 1 (M1 - ABHA Registration & Verification) and Milestone 2 (M2 - Care Context Linking) for **ProDoc Hospital Information System**.

---

## 🚀 Key Highlights & Architecture

1. **Live ABDM Public Certificate & RSA Encryption:**
   - Fetches official 4096-bit RSA certificate directly from ABDM (`GET /abha/api/v3/profile/public/certificate`) and gateway JWKS endpoints.
   - Encrypts Aadhaar, mobile numbers, and OTPs with standard `RSA/ECB/OAEPWithSHA-1AndMGF1Padding`.
2. **Zero-Friction Transaction Auto-Resolution:**
   - In Step 2 (`verify-otp`), clients (ProDoc / Postman) do **not** need to manually pass `transactionId`. Python automatically resolves the active transaction ID from the matching `mobile` / `patientId` from Step 1.
3. **Session Access Token Auto-Management:**
   - Automatically acquires and reuses ABDM Gateway session tokens with an expiry buffer (`GLOBAL_ACCESS_TOKEN`). No manual auth calls needed.
4. **Event-Driven Webhook Architecture (Senior Requirement 3):**
   - Push-based webhook callback handler (`/api/abdm/webhook/callback` & `/webhook/{subpath}`).
   - Direct execution of `on_message_received` with instantaneous ACK confirmation (*"I have received this message"*).
   - Background polling option available for local NAT/firewall test environments.

---

## 📋 Prerequisites & Installation

- Python 3.10 or higher
- Postman (for API testing)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Copy `.env.example` to `.env` (or update existing `.env`):
```ini
# ABDM Gateway Credentials (Sandbox)
ABDM_CLIENT_ID=your_client_id
ABDM_CLIENT_SECRET=your_client_secret
ABDM_HIP_ID=your_hip_id
ABDM_CM_ID=sbx

# Server Settings
HOST=0.0.0.0
PORT=8000
ENABLE_DEMO_ROUTES=1
ENABLE_WEBHOOK_POLLING=0
```

### 3. Run the Server
Using PowerShell / CMD:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Or run the quick-start script:
```powershell
.\run.ps1
```

- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Spec:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 API Reference: Core Workflows

### 🏥 Flow 1: ProDoc OPD - Register ABHA to Existing Patient (`frmRegisterABHAPatient`)

#### Step 1: Send Login / Verification OTP
Initiates ABHA login verification for an existing patient. Python encrypts the mobile number with the official ABDM certificate and requests OTP delivery.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/register-patient/send-otp`
- **Body:**
```json
{
  "mobile": "8779441274",
  "patientId": "946"
}
```
- **Response:**
```json
{
  "success": true,
  "transactionId": "d98522e8-5b1b-4fc8-9f34-11e25e9dd265",
  "message": "OTP sent successfully to registered mobile",
  "key_source": "ABHA_CERT_URL (https://abhasbx.abdm.gov.in/abha/api/v3/profile/public/certificate)"
}
```

#### Step 2: Verify OTP & Fetch ABHA Profile
Verifies the OTP entered by the patient. **`transactionId` is optional**; Python auto-matches it from Step 1 using `mobile` or `regNo`.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/register-patient/verify-otp`
- **Body:**
```json
{
  "mobile": "8779441274",
  "otp": "123456",
  "regNo": "946"
}
```
- **Response:**
```json
{
  "success": true,
  "message": "OTP Verified Successfully",
  "transactionId": "d98522e8-5b1b-4fc8-9f34-11e25e9dd265",
  "abhaNumber": "91-1234-5678-9012",
  "abhaAddress": "patient.name@sbx",
  "patientName": "Patient Full Name",
  "gender": "M",
  "dob": "1995-05-12",
  "status": "ACTIVE",
  "verifiedStatus": "VERIFIED",
  "accounts": [
    {
      "ABHANumber": "91-1234-5678-9012",
      "preferredAbhaAddress": "patient.name@sbx",
      "name": "Patient Full Name",
      "gender": "M",
      "dob": "1995-05-12",
      "status": "ACTIVE"
    }
  ]
}
```

#### Step 3: Link ABHA to ProDoc Patient Record
Permanently maps the verified ABHA details with the patient's registration number.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/register-patient/link`
- **Body:**
```json
{
  "regNo": "946",
  "abhaNumber": "91-1234-5678-9012",
  "abhaAddress": "patient.name@sbx"
}
```

#### Step 4: Check Patient ABHA Link Status
- **Method:** `GET`
- **URL:** `http://localhost:8000/api/abdm/register-patient/status?patientId=946`

---

### 🏥 Flow 2: Milestone 1 (M1) - ABHA Core Operations (Calls 3 to 7)

#### Call 3: Search Existing ABHA
Searches for an existing ABHA record by mobile number or search criteria.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/abha/search`
- **Body:**
```json
{
  "patientId": "P10025",
  "searchType": "MOBILE",
  "searchValue": "9999999999"
}
```
- **Success Response:**
```json
{
  "success": true,
  "patientId": "P10025",
  "matches": [
    {
      "abhaNumber": "12345678901234",
      "abhaAddress": "rahul.sharma@abdm",
      "verificationRequired": true
    }
  ],
  "message": "ABHA search completed"
}
```
- **Failure Response:**
```json
{
  "success": false,
  "errorCode": "ABHA_NOT_FOUND",
  "message": "No matching ABHA record found"
}
```

#### Call 4: Link Existing ABHA to ProDoc Patient
Links an existing verified ABHA identity to the ProDoc patient record.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/abha/link-existing`
- **Body:**
```json
{
  "patientId": "P10025",
  "abhaNumber": "12345678901234",
  "abhaAddress": "rahul.sharma@abdm"
}
```
- **Success Response:**
```json
{
  "success": true,
  "status": "LINKED",
  "patientId": "P10025",
  "abhaNumber": "12345678901234",
  "abhaAddress": "rahul.sharma@abdm",
  "message": "Existing ABHA linked successfully"
}
```
- **Failure Response:**
```json
{
  "success": false,
  "errorCode": "ABHA_LINK_FAILED",
  "message": "Unable to link ABHA to the ProDoc patient"
}
```

#### Call 5: Get Patient ABHA Profile
Retrieves the complete ABHA profile for a registered patient.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/patients/abha-profile`
- **Body:**
```json
{
  "patientId": "P10025"
}
```
- **Success Response:**
```json
{
  "success": true,
  "patientId": "P10025",
  "abhaProfile": {
    "abhaNumber": "12345678901234",
    "abhaAddress": "rahul.sharma@abdm",
    "name": "Rahul Sharma",
    "gender": "M",
    "dob": "1998-05-15"
  },
  "message": "ABHA profile retrieved successfully"
}
```
- **Failure Response:**
```json
{
  "success": false,
  "errorCode": "ABHA_PROFILE_NOT_FOUND",
  "message": "ABHA profile not found for this patient"
}
```

#### Call 6: Get ABHA Card
Fetches the patient's ABHA Card in Base64 format.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/patients/abha-card`
- **Body:**
```json
{
  "patientId": "P10025",
  "format": "PDF"
}
```
- **Success Response:**
```json
{
  "success": true,
  "patientId": "P10025",
  "fileName": "ABHA_P10025.pdf",
  "contentType": "application/pdf",
  "fileBase64": "BASE64_ENCODED_FILE",
  "message": "ABHA card retrieved successfully"
}
```
- **Failure Response:**
```json
{
  "success": false,
  "errorCode": "ABHA_CARD_NOT_FOUND",
  "message": "ABHA card not found for this patient"
}
```

#### Call 7: Get ABHA QR Code
Retrieves the Base64 QR code image associated with the patient's ABHA identity.
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/patients/abha-qr`
- **Body:**
```json
{
  "patientId": "P10025"
}
```
- **Success Response:**
```json
{
  "success": true,
  "patientId": "P10025",
  "abhaAddress": "rahul.sharma@abdm",
  "qrCodeBase64": "BASE64_ENCODED_QR",
  "message": "ABHA QR code generated successfully"
}
```
- **Failure Response:**
```json
{
  "success": false,
  "errorCode": "ABHA_QR_NOT_FOUND",
  "message": "ABHA QR code not found for this patient"
}
```

---

### 🔗 Flow 2: Webhook Channel & Event-Driven Callbacks (Senior Requirement 3)

ABDM uses asynchronous event-driven callbacks for Care Context linking, token responses, and transaction notifications.

#### 1. Open Webhook Channel
Registers the callback URL with ABDM Gateway and attaches the live listener:
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/abdm/webhook/open`
- **Response:**
```json
{
  "status": "OPEN",
  "mode": "EVENT_DRIVEN_PUSH_CALLBACK",
  "callback_attached": "on_message_received"
}
```

#### 2. Push Callback Receiver
Listens for incoming ABDM responses (`/api/abdm/webhook/callback`, `/api/v3/hip/token/on-generate-token`, `/webhook/*`):
- Whenever ABDM pushes an async callback, `on_message_received()` executes immediately:
  - Parses the JSON payload.
  - Matches the echoed `requestId` with original sent requests.
  - Extracts `linkToken` and persists it securely.
  - Returns instant confirmation: `"I have received this message"`.

---

## 🧪 Postman Collection Setup

1. Open Postman.
2. Click **Import** and select `ProDoc_ABDM_APIs_Postman_Collection.json`.
3. Set Collection Variable `baseUrl` to `http://localhost:8000`.
4. Run requests in sequence under **Flow 4: ProDoc OPD - Register ABHA to Existing Patient**:
   - `1. Hit 1 - Send OTP (ProDoc)`
   - `2. Hit 2 - Verify OTP (ProDoc)` (No transaction ID needed)
   - `3. Hit 3 - Register ABHA Link (ProDoc)`
   - `4. Check Patient ABHA Status`

---

## 📁 File Structure

```
├── main.py                               # FastAPI application entrypoint & lifespan
├── routes_abdm.py                        # Core ABDM M1 & M2 endpoints & Pydantic models
├── routes_demo.py                        # Optional demo/inspection routes
├── abha_service.py                       # M1 ABHA business logic (OTP, Verification, Linking)
├── crypto_abdm.py                        # RSA OAEP encryption & live ABDM cert parser
├── abdm_client.py                        # Session token management & ABDM gateway HTTP client
├── store.py                              # In-memory stores, persistent caches & token helpers
├── webhook_reader.py                     # Push callback parser & on_message_received handler
├── ProDoc_ABDM_APIs_Postman_Collection.json # Postman collection for all flows
├── requirements.txt                      # Project Python dependencies
├── run.ps1                               # Quick-start script
└── README.md                             # Project documentation
```
