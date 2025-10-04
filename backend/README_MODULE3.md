Module 3 - Token Management & Authentication API

Endpoints:
- POST /api/auth/login  => body {username, password}
- POST /api/auth/refresh => body {refresh_token}
- POST /api/auth/logout => header Authorization: Bearer <access_token>, optional body {refresh_token}
- GET  /api/auth/verify => header Authorization: Bearer <access_token>

Integration:
- Replace verify_user_credentials stub in auth_routes.py with real call / DB model from Module 1.
- If Module 2 holds oauth_clients in another DB or service, point OAuthClient model or call its API.

Environment variables (.env):
- SECRET_KEY
- JWT_SECRET_KEY
- DATABASE_URL
- ACCESS_EXPIRES_MIN
- REFRESH_EXPIRES_DAYS
