# Business - Investing - Sales

This repo hosts two independent projects:

1. **CRM** (below) — a lightweight Flask CRM for contacts, deals, and activities.
2. **[Weekly Market Dashboard](market_dashboard/README.md)** — an automated,
   GitHub Actions–powered market dashboard (industrial / logistics / retail /
   macro) that publishes to GitHub Pages and emails a weekly summary every
   Monday at 7 AM Central. See [`market_dashboard/README.md`](market_dashboard/README.md)
   for the full step-by-step setup guide.

---

# Business - Investing - Sales CRM

A lightweight, full-featured CRM (Customer Relationship Management) system built for small businesses, sales teams, and solo entrepreneurs.

## Features

- **Contact Management** - Store and manage leads, prospects, and customers
- **Deal Pipeline** - Visual sales pipeline with drag-and-drop stages
- **Activity Tracking** - Log calls, emails, meetings, and follow-ups
- **Dashboard** - Real-time metrics: revenue, conversion rates, deal velocity
- **Search & Filter** - Find contacts and deals instantly
- **CSV Import/Export** - Bulk import contacts, export reports
- **Tags & Segmentation** - Organize contacts with custom tags
- **Notes & History** - Full interaction history per contact

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the CRM
python crm/app.py

# Open browser to http://localhost:5000
```

## Tech Stack

- **Backend:** Python / Flask
- **Database:** SQLite (zero config, portable)
- **Frontend:** HTML, CSS, JavaScript (no frameworks needed)
- **API:** RESTful JSON endpoints

## Project Structure

```
crm/
  app.py            # Main application & API routes
  models.py         # Database models & schema
  seed.py           # Sample data seeder
  static/
    css/style.css   # Dashboard styles
    js/app.js       # Frontend logic
  templates/
    index.html      # Main dashboard
tests/
  test_api.py       # API tests
requirements.txt    # Python dependencies
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/contacts | List all contacts |
| POST | /api/contacts | Create a contact |
| GET | /api/contacts/:id | Get contact details |
| PUT | /api/contacts/:id | Update a contact |
| DELETE | /api/contacts/:id | Delete a contact |
| GET | /api/deals | List all deals |
| POST | /api/deals | Create a deal |
| PUT | /api/deals/:id | Update a deal |
| DELETE | /api/deals/:id | Delete a deal |
| GET | /api/activities | List activities |
| POST | /api/activities | Log an activity |
| GET | /api/dashboard | Dashboard metrics |
| POST | /api/contacts/import | CSV import |
| GET | /api/contacts/export | CSV export |
