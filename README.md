# Interview Backend

A FastAPI backend for an interview management platform that handles interviewer authentication, question management, and candidate interview recordings.

## Features

- Interviewer authentication
- Subscription-based access
- Interview management (questions, themes)
- Token generation for candidates
- Interview recording and transcription
- Result analysis and retrieval

## Registration and Subscription Flow

The platform follows a self-service registration flow with built-in payment processing:

1. **Initial Registration** (`POST /api/auth/registration/`)
   - Creates a pending account with a verification token
   - No payment required at this step

2. **Subscription Selection** (`POST /api/auth/registration/checkout/{plan_id}`)
   - User selects a subscription plan (basic, premium, enterprise)
   - Creates a Stripe checkout session
   - Returns a checkout URL for payment processing

3. **Payment Processing** (handled by Stripe)
   - User completes payment on the Stripe-hosted checkout page
   - Stripe redirects to success URL with session ID

4. **Account Activation** (`POST /api/auth/registration/complete`)
   - Verifies payment was successful
   - Creates active user account with subscription details
   - Removes pending account

After registration and activation, users can manage their subscriptions through:
- Customer portal access (`POST /api/payments/checkout/customer-portal`)
- Subscription reactivation (`POST /api/payments/checkout/reactivate-subscription/{plan_id}`)

## Subscription Features

The application includes a complete subscription management system:

- Integrated with Stripe for payment processing
- Multiple subscription tiers (Basic, Premium, Enterprise)
- Self-service signup flow for new companies
- Automatic subscription renewal handling
- Access control based on subscription status

## Admin Features

The application includes admin endpoints for managing interviewer accounts. These endpoints use HTTP Basic Authentication:

- **Create User**: `POST /admin/users` - Create a new interviewer account
- **List Users**: `GET /admin/users` - Get a list of all interviewer accounts
- **Delete User**: `DELETE /admin/users/{user_id}` - Delete an interviewer account

Admin credentials are configured through environment variables:
```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_admin_password
```

Default admin credentials (development only):
- Username: admin
- Password: admin

**Important**: Change these credentials in production!

## Setup

1. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Set up environment variables in `.env` file:
```
# For PostgreSQL (recommended for production)
DATABASE_URL=postgresql://user:password@localhost/interview_db
SECRET_KEY=your_secure_secret_key
OPENAI_API_KEY=your_openai_api_key

# For Stripe integration
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_BASIC_PRICE_ID=price_id_for_basic_plan
STRIPE_PREMIUM_PRICE_ID=price_id_for_premium_plan
STRIPE_ENTERPRISE_PRICE_ID=price_id_for_enterprise_plan

# Frontend URL for redirects
FRONTEND_URL=http://localhost:3000

# For development without PostgreSQL
DEV_MODE=True  # This will use SQLite if PostgreSQL connection fails
```

4. Run the application:
```
uvicorn app.main:app --reload
```

5. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Stripe Integration

To test Stripe integration locally:

1. Install the Stripe CLI: https://stripe.com/docs/stripe-cli
2. Run the webhook forwarding: `stripe listen --forward-to localhost:8000/api/payments/webhook`
3. Use the webhook signing secret provided by the CLI in your .env file

## Database Options

- **PostgreSQL** (recommended for production): Set up a PostgreSQL server and provide the connection URL
- **SQLite** (for development): Automatically used as fallback in development mode if PostgreSQL connection fails

## Deployment

This application is configured for deployment on Heroku with a PostgreSQL database.

```
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set SECRET_KEY=your_secure_secret_key
heroku config:set OPENAI_API_KEY=your_openai_api_key
heroku config:set STRIPE_API_KEY=your_stripe_api_key
heroku config:set STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
heroku config:set STRIPE_BASIC_PRICE_ID=price_id_for_basic_plan
heroku config:set STRIPE_PREMIUM_PRICE_ID=price_id_for_premium_plan
heroku config:set STRIPE_ENTERPRISE_PRICE_ID=price_id_for_enterprise_plan
heroku config:set FRONTEND_URL=https://your-frontend-app.com
heroku config:set DEV_MODE=False
git push heroku main
```