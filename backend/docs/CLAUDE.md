orris
# 📄 PRD – Authentication & User Management Backend (EVIDEV LLP)

## use mvc architecture

## 🔧 Tech Stack
- **Backend**: Python, FastAPI, Pydantic
- **Database**: PostgreSQL (RDBMS)
- **Password Hashing**: bcrypt
- **Token Auth**: JWT (access + refresh)
- **Session Tracking**: Per device/session
- **Cookie Auth**: HTTP-only, Secure
- **OAuth**: Google OAuth2

---

## 🧩 MODULES TO BE DEVELOPED

### 1. 🧑‍💼 User Management

#### 👤 User Table
- id
- name
- email
- password (hashed using bcrypt)
- role (signed_up, non_pi_access, pi_access)
- status
- email_verified
- created_at

#### 🔐 Signup (Manual)
- Validations:
  - Email format
  - Password strength
  - Confirm password match
- Hash password using bcrypt
- Check if user exists by email → return 409 Conflict
- On success:
  - Return access & refresh token in secure cookies

#### 🔐 Login (Manual)
- Validate email & password
- On success:
  - Generate JWT access & refresh tokens
  - Save refresh token with device info
  - Create user log
  - Set tokens in secure cookies

---

### 2. 🔑 Google OAuth2 Login/Signup

- Verify Google ID token using Google's certs
- If email exists → proceed to login
- If not → create new user with:
  - role = signed_up
  - email_verified = true
- Block signup if user with email already exists
- Return tokens in cookies

---

### 3. 🪙 Token Management

#### 🔐 Access Token
- Claims: sub, email, role, iat, exp
- Expiry: 15 minutes

#### 🔁 Refresh Token
- Generated during login/signup
- Stored in DB (hashed) with:
  - user_id
  - device_id
  - ip_address
  - user_agent
  - created_at
  - expires_at
  - is_valid
- Expiry: 7 days
- Sent as HttpOnly, Secure, SameSite=None cookie

#### 🔄 Refresh Endpoint
- Accepts refresh token from cookie
- Validates token (exists, not expired, is_valid)
- Issues new access & refresh tokens (rotation)
- Invalidates old refresh token

---

### 4. 📜 User Logs

#### 📘 Logs Table
- id
- user_id
- action (signup, login, logout)
- ip_address
- user_agent
- created_at

- Logs created during the request

---

### 5. 🚫 Logout

- Invalidate refresh token (is_valid = false)
- Clear cookies on frontend
- Log the logout event

---

### 6. 🔐 Middleware / Security

- Decode access token from cookie
- Inject user data into request context
- Reject expired tokens
- Use FastAPI dependencies for protected routes

---

### 7. 🛡️ Security Best Practices

- Sensitive routes protected by JWT
- Passwords hashed via bcrypt
- Cookies:
  - HttpOnly
  - Secure
  - SameSite=None
- Rate-limit login/signup
- Role changes trigger forced logout
- Tokens signed with strong secret keys
- Refresh tokens stored as hashes

---

## 🧪 Testing (via Swagger)
- `/signup`
- `/login`
- `/auth/google`
- `/refresh`
- `/logout`
- `/me` (get profile info)
- Logs auto-generated for login/logout/signup

---

## 📦 Deliverables

- FastAPI app with working endpoints
- Pydantic request/response models
- JWT & token utilities
- Refresh token & session DB handling
- Cookie handling logic
- Google OAuth2 integration
- Swagger UI for all endpoints
