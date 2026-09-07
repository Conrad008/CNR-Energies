# CNR Energies — Enterprise Station Operations Platform

A full-stack, enterprise-grade station management and operations platform custom-built for **CNR Energies**. The system digitizes daily petrol station operations—featuring explicit shift lifecycle management, double-entry financial reconciliation, underground tank inventory auditing, automated B2B credit controls, and real-time management analytics.

---

## Tech Stack & Architecture

* **Backend Framework:** Django 5.x & Django REST Framework (DRF)
* **Authentication & RBAC:** SimpleJWT (JSON Web Tokens) with granular Role-Based Access Control
* **Database:** PostgreSQL (Production) / SQLite (Development)
* **Frontend Framework:** React 18+ (bootstrapped with Vite)
* **Styling & UI:** Tailwind CSS, Lucide React Icons
* **Data Visualization:** Recharts / Chart.js
* **API Documentation:** OpenAPI 3.0 / Swagger (drf-spectacular)

---

## System Users & Role-Based Access Control (RBAC)

To reflect real-world station operations, the system explicitly separates physical **Users** from database **Roles (RBAC Access Levels)**:

### 1. System Users (Who uses the platform)
* **Station Owners (Parents):** Executive management viewing high-level sales totals, financial summaries, and overall profit analytics.
* **Station Manager:** Day-to-day operations lead overseeing shifts, approving meter shortages/variances, updating fuel prices, and managing credit clients.
* **Pump Attendants:** Ground staff opening/closing active shifts, entering pump meter readings, recording sales, and submitting collections.
* **Station Accountant / Cashier:** Financial officer managing B2B credit accounts, verifying bank deposits against shift collections, and settling debt.
* **Inventory / Tanker Officer:** Stock auditor entering physical tank dip readings and logging incoming tanker deliveries.

### 2. RBAC Permissions Hierarchy

| Role (`role` field) | Primary Access & Key Permissions |
|---|---|
| `SUPER_ADMIN` | Full read/write system access, user management, audit logs, and operational overrides. |
| `MANAGER` | Price adjustments, shift variance approvals, B2B credit account registration, and delivery logging. |
| `ATTENDANT` | Assigned shift operations, opening/closing pump meters, logging sales, and submitting collections. |
| `ACCOUNTANT` | B2B credit ledger access, customer payment settlements, and cash/bank reconciliation reports. |
| `INVENTORY_OFFICER` | Dipstick tank readings, tanker delivery entry, and stock variance audit views. |

---

## System Features & Operational Pillars

```text
Fuel Delivery → Tanks Holding → Pump Dispensing → Attendant Shifts → Payments → Shift Reconciliation → Audit & Inventory Update
```

### 1. Advanced Shift Lifecycle & Dual Reconciliation
* **Explicit Shift Lifecycle:** Tracks shifts through operational states (`SCHEDULED` → `OPEN` → `ACTIVE` → `PENDING_RECONCILIATION` → `RECONCILED` → `CLOSED`).
* **Cash Reconciliation Engine:** Automatically calculates expected revenue based on pump meter deltas:
  $$	ext{Expected Sales} = (	ext{Closing Meter} - 	ext{Opening Meter}) 	imes 	ext{Price Per Liter}$$
* **Variance Alerting:** Compares expected revenue against submitted payment methods (Cash, M-Pesa, Card, Credit) and flags shortages/overages for manager review.

### 2. Tank Inventory & Audit Engine
* **Tank Stock Reconciliation:** Compares physical dipstick measurements against calculated expected inventory:
  $$	ext{Expected Stock} = 	ext{Opening Stock} + 	ext{Deliveries} - 	ext{Dispensed Fuel}$$
* **Delivery Logging:** Logs incoming fuel tanker batches with supplier invoice details, automatically updating tank levels.
* **Variance Detection:** Automatically detects fuel leakage, temperature evaporation, or measurement inaccuracies.

### 3. Price History Ledger
* **Historical Pricing:** Preserves time-stamped price records (`effective_from` / `effective_to`) to ensure historical shift reconciliations remain accurate when fuel prices fluctuate.

### 4. B2B Commercial Credit Management
* **Accounts Receivable Ledger:** Tracks fleet and commercial accounts dispensing fuel on credit.
* **Automated Credit Blocking:** Enforces real-time credit limit checks at the backend level. Rejects fuel dispenses if `Current Balance + Purchase Amount > Credit Limit`.
* **Payment Settlements:** Processes partial and full customer debt clearance payments.

### 5. Multi-Role RBAC & Audit Trail
* **Role Hierarchy:** Enforces explicit permission boundaries across `SUPER_ADMIN`, `MANAGER`, `ATTENDANT`, `ACCOUNTANT`, and `INVENTORY_OFFICER`.
* **System Audit Log:** Immutably records administrative actions, price updates, and variance approvals (`user`, `action`, `model`, `old_value`, `new_value`, `timestamp`).

---

## API Architecture Blueprint

The platform exposes structured RESTful endpoints grouped by operational modules:

| Module | Method | Endpoint | Description | Access |
|---|---|---|---|---|
| **Auth** | `POST` | `/api/auth/login/` | Obtain JWT access & refresh tokens | Public |
| | `POST` | `/api/auth/refresh/` | Refresh expired access token | Public |
| | `GET` | `/api/users/me/` | Fetch active user profile & RBAC permissions | Authenticated |
| **Users** | `GET` | `/api/users/` | List all system users & roles | Admin/Manager |
| | `POST` | `/api/users/` | Register new station staff | Admin |
| **Stations** | `GET` | `/api/stations/` | List station facilities | Authenticated |
| **Fuel & Pricing**| `GET` | `/api/fuel-products/` | List fuel types & current prices | Authenticated |
| | `POST` | `/api/fuel-prices/` | Log price update with effective timestamp | Manager/Admin |
| **Pumps & Tanks** | `GET` | `/api/pumps/` | List pumps and assigned nozzles | Authenticated |
| | `GET` | `/api/tanks/` | View tank capacities & fuel levels | Authenticated |
| | `POST` | `/api/tanks/{id}/dips/` | Record physical dipstick reading | Manager/Inventory |
| | `POST` | `/api/deliveries/` | Record incoming fuel tanker batch | Manager/Inventory |
| **Shifts** | `POST` | `/api/shifts/start/` | Open attendant shift with opening meters | Attendant/Manager |
| | `GET` | `/api/shifts/` | List shift logs & operational statuses | Authenticated |
| | `POST` | `/api/shifts/{id}/close/` | Close shift with closing meters & collections | Attendant/Manager |
| | `POST` | `/api/shifts/{id}/approve/` | Approve shift reconciliation & variance | Manager/Admin |
| **Sales** | `POST` | `/api/sales/` | Record fuel transaction | Attendant/Manager |
| | `GET` | `/api/sales/` | List transaction logs | Authenticated |
| **Payments** | `POST` | `/api/payments/` | Process cash, card, or credit settlement | Attendant/Manager |
| | `POST` | `/api/payments/mpesa/stk/` | Trigger M-Pesa STK push request | Attendant/Manager |
| **Credit Accounts**| `GET` | `/api/credit-customers/` | List B2B accounts, balances & limits | Authenticated |
| | `POST` | `/api/credit-customers/{id}/payments/` | Record credit debt settlement | Accountant/Admin |
| **Analytics** | `GET` | `/api/analytics/dashboard/` | Real-time sales, inventory & variance metrics | Manager/Admin |
| **Audit Logs** | `GET` | `/api/audit-logs/` | View system activity trail | Admin |

---

## Domain Entity Relationship (ERD Overview)

```text
[ Station ]
   ├─── 1:N ───> [ Pump ] ─── 1:N ───> [ Nozzle ]
   ├─── 1:N ───> [ Tank ] ─── 1:N ───> [ DipReading ]
   │                └─── 1:N ───> [ Delivery ]
   └─── 1:N ───> [ Shift ]
                    ├─── 1:N ───> [ PumpReading ]
                    ├─── 1:N ───> [ Sale ] ─── 1:1 ───> [ Payment ]
                    └─── 1:1 ───> [ Reconciliation ]

[ FuelProduct ] ─── 1:N ───> [ FuelPriceHistory ]
[ CreditCustomer ] ─── 1:N ───> [ CreditTransaction ]
[ User ] ─── 1:N ───> [ AuditLog ]
```

---

## Quickstart & Setup Guide

### 1. Backend Setup (Django & DRF)

```bash
# Clone repository
git clone https://github.com/Conrad008/CNR-Energies.git
cd CNR-Energies/backend

# Create and activate virtual environment
python3 -m venv my_env
source my_env/bin/activate  # On Windows: my_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env

# Run database migrations
python manage.py migrate

# Seed initial station data
python manage.py seed_station_data

# Create administrative account
python manage.py createsuperuser

# Start Django development server
python manage.py runserver
```

### 2. Frontend Setup (React & Vite)

```bash
# Navigate to frontend directory
cd ../frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

---

## License
This project is proprietary software developed for **CNR Energies**. All rights reserved.

## Author
Conrad Kipngeno