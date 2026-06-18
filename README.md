# 🌿 Bloom — Data-Driven Inventory Optimisation
**Crawford University Final Year CS Project · 2026**

Bloom is a web application that gives campus micro-vendors personalised,
data-backed inventory recommendations powered by real student demand data.

---

## 📁 Project Structure

```
bloom/
├── bloom-frontend/      React + TypeScript + Tailwind (Vite)
└── bloom-backend/       Python Flask REST API
```

---

## 🚀 Quick Start

### Backend (Flask API)

```bash
cd bloom-backend

# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your MongoDB URI (or leave as-is for demo mode)

# 4. Run
python app.py
# → API running at http://localhost:5000
# → Demo login (no MongoDB needed): demo@bloom.ng / demo123
```

### Frontend (React App)

```bash
cd bloom-frontend

# 1. Install dependencies
npm install

# 2. Run dev server
npm run dev
# → App running at http://localhost:5173

# 3. Build for production
npm run build
```

---

## 🗄️ MongoDB Setup (Optional)

The app runs in **demo mode** without MongoDB.
For full persistence, use MongoDB Atlas (free tier):

1. Create account at https://www.mongodb.com/atlas
2. Create a free M0 cluster
3. Get your connection string
4. Paste into `bloom-backend/.env` as `MONGO_URI`

---

## 🔌 API Endpoints

| Method | Endpoint                        | Auth | Description               |
|--------|---------------------------------|------|---------------------------|
| POST   | /api/auth/register              | ✗    | Create vendor account     |
| POST   | /api/auth/login                 | ✗    | Login, get JWT token      |
| GET    | /api/auth/me                    | ✓    | Get current vendor        |
| GET    | /api/dashboard                  | ✓    | Full dashboard report     |
| GET    | /api/dashboard/products         | ✓    | Product analysis          |
| GET    | /api/dashboard/alerts           | ✓    | Restock alerts            |
| GET    | /api/dashboard/recommendations  | ✓    | Product recommendations   |
| GET    | /api/dashboard/gap-analysis     | ✓    | Demand vs supply gaps     |
| PUT    | /api/dashboard/products         | ✓    | Update vendor products    |
| GET    | /api/health                     | ✗    | Health check              |

---

## 🧠 How the Recommendation Engine Works

1. Vendor registers with store type and products
2. Engine matches products to Crawford campus demand database
3. Calculates demand scores, weekly units, restock points
4. Identifies gaps between student demand and vendor supply
5. Returns personalised report with:
   - Products to add (undersupplied on campus)
   - Products to reduce (slow movers)
   - Restock alerts (threshold-based)
   - Weekly quantity recommendations

### Restock Point Formula
```
Restock Point = (Weekly Units ÷ 6) × Lead Time Days × 1.5
```

### Demand Score Formula
```
Demand Score = (Purchase Rate × 0.6) + (Complaint Rate × 0.4) × 10
```

---

## 🎓 Academic Context

- **Student survey:** 465 respondents, Crawford University
- **Vendor survey:** 7 vendors, Firebase-collected
- **Analysis engine:** Python (pandas, scipy, numpy)
- **Statistical tests:** Chi-square (×3), Spearman correlation

---

## 📦 Tech Stack

| Layer     | Technology                    |
|-----------|-------------------------------|
| Frontend  | React + TypeScript (Vite)     |
| Styling   | Tailwind CSS                  |
| Charts    | Recharts                      |
| Routing   | React Router v6               |
| Backend   | Python Flask                  |
| Auth      | JWT (flask-jwt-extended)      |
| Database  | MongoDB (pymongo)             |
| Passwords | bcrypt                        |
| CORS      | flask-cors                    |
