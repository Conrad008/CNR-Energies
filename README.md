# CNR Energies | Petrol Station Management System

A full-stack, enterprise-grade station management portal built for **CNR Energies**. The system digitizes daily petrol station operations—including shift reconciliation, underground tank inventory management, pump meter tracking, commercial credit customer ledgers, and real-time sales analytics.

---

##  Tech Stack & Architecture

* **Backend Framework:** Django 5.x & Django REST Framework (DRF)
* **Authentication:** SimpleJWT (JSON Web Tokens) with RBAC (Role-Based Access Control)
* **Database:** PostgreSQL (Production) / SQLite (Development)
* **Frontend Framework:** React 18+ (bootstrapped with Vite)
* **Styling & UI:** Tailwind CSS, Lucide React Icons
* **Data Visualization:** Recharts / Chart.js

---

## System Features

### 1. Shift Management & Cash Reconciliation
* **Shift Lifecycle:** Open shift with initial register float and close shift with recorded cash/POS receipts.
* **Meter Discrepancy Engine:** Calculates expected cash revenue automatically based on meter delta (`Closing Meter - Opening Meter * Price per Liter`) and compares it against actual cash/card submitted.
* **Variance Alerting:** Flags overages or shortfalls per attendant shift.

### 2. Underground Tank & Inventory Control
* **Dip Tank Readings:** Daily physical dipstick depth recording vs. calculated volume.
* **Tanker Deliveries:** Track incoming fuel batches (Liters received, supplier invoices) with automatic stock level adjustments.
* **Visual Fuel Gauge:** Real-time percentage capacity tracking for Super Petrol, Diesel, and Kerosene.

### 3. Commercial Credit Accounts (B2B Debtors)
* **Credit Ledger:** Track fleets and business accounts dispensing fuel on credit.
* **Credit Limit Safeguards:** Validates account balances before authorizing credit fuel transactions.
* **Payment Processing:** Logs partial and full account clearing settlements.

### 4. Admin Analytics & Reporting
* **Daily Sales Summary:** Aggregated daily volume (Liters) and gross revenue ($/KSh).
* **Attendant Performance:** Audit trail and variance logs per staff member.

---

## API Architecture Blueprint (20 Endpoints)

| Module | Method | Endpoint | Description | Access |
|---|---|---|---|---|
| **Auth** | `POST` | `/api/auth/login/` | Obtain JWT access & refresh tokens | Public |
| | `POST` | `/api/auth/refresh/` | Refresh expired access token | Public |
| | `GET` | `/api/users/me/` | Fetch current user profile & role | Authenticated |
| | `GET` | `/api/users/` | List all station staff members | Admin |
| **Products** | `GET` | `/api/products/` | List fuel types & active prices | Authenticated |
| | `PATCH` | `/api/products/{id}/price/` | Update price per liter | Admin |
| **Tanks** | `GET` | `/api/tanks/` | Get current volume across all tanks | Authenticated |
| | `POST` | `/api/dip-logs/` | Record manual dip stick reading | Manager/Admin |
| | `POST` | `/api/deliveries/` | Log fuel tanker delivery | Manager/Admin |
| | `GET` | `/api/deliveries/` | List delivery audit history | Manager/Admin |
| **Shifts** | `POST` | `/api/shifts/start/` | Open new attendant shift | Manager/Attendant |
| | `POST` | `/api/shifts/{id}/close/` | Close shift & submit collections | Manager/Attendant |
| | `GET` | `/api/shifts/` | View shift logs and status | Authenticated |
| **Pumps** | `POST` | `/api/pump-readings/` | Submit opening/closing pump meters | Manager/Attendant |
| | `GET` | `/api/pump-readings/` | List meter readings by shift | Authenticated |
| **Credit** | `GET` | `/api/credit-customers/` | List B2B accounts & balances | Authenticated |
| | `POST` | `/api/credit-transactions/` | Log credit fuel dispense | Manager/Admin |
| | `POST` | `/api/credit-customers/{id}/payment/` | Record customer debt payment | Admin |
| **Analytics**| `GET` | `/api/analytics/daily-summary/` | Daily volume & revenue metrics | Admin |
| | `GET` | `/api/analytics/reconciliation/` | Shift variance & cash audit summary | Admin |

---

## Quickstart & Development Setup

### 1. Backend Setup (Django & DRF)

```bash
# Clone repository
git clone https://github.com/Conrad008/CNR-Energies.git
cd cnr-energies/backend

python3 -m venv my_env
source my_env/scripts/activate  

# Install dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env

# Run database migrations
python manage.py migrate

python manage.py seed_station_data

# Create superuser
python manage.py createsuperuser

python manage.py runserver
```

### 2. Frontend Setup (React & Vite)

```bash
cd ../frontend

npm install

npm run dev
```

---

##  License
This project is licensed under the MIT license

## Author
Conrad Kipngeno