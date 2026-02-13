# Best Prompts for Building & Extending This CRM

Use these prompts with AI assistants (Claude, ChatGPT, etc.) to get the most out of your electrical equipment sales CRM.

---

## The Master CRM Prompt

Copy and paste this as your starting prompt when working with any AI assistant:

```
You are an expert CRM developer and electrical equipment sales consultant.
I have a Python/Flask CRM for selling electrical equipment (transformers,
switchgear, generators, panels, motors, VFDs, UPS systems, cable, lighting).

The CRM has:
- Contacts (leads, prospects, customers) with tags, notes, company, status
- Deals with pipeline stages (lead → qualified → proposal → negotiation → closed won/lost)
- Activities (calls, emails, meetings, tasks, follow-ups)
- Dashboard with revenue, pipeline value, win rate metrics
- REST API with full CRUD operations
- SQLite database, Flask backend, vanilla JS frontend

Tech stack: Python 3, Flask, SQLite, HTML/CSS/JS (no frameworks)
```

---

## Prompts by Category

### 1. Adding Features

**Add email integration:**
```
Add email sending capability to my Flask CRM. When I log an "email" activity,
it should optionally send the email via SMTP. Add SMTP config to a .env file.
Keep it simple - just a send button on the activity form.
```

**Add quote/proposal generation:**
```
Add a quote generator to my CRM. Given a deal, let me add line items
(product name, SKU, quantity, unit price) and generate a PDF quote.
Use reportlab or weasyprint. Include my company name, customer info,
line items with totals, and terms. Store quotes linked to deals.
```

**Add calendar/scheduling:**
```
Add a simple calendar view to my CRM that shows activities with due dates.
Use a monthly grid layout in vanilla JS. Clicking a date should show
activities for that day. Color-code by activity type.
```

**Add inventory tracking:**
```
Add a simple inventory module to my electrical equipment CRM. I need to
track products (name, SKU, category, quantity on hand, reorder point,
unit cost, sell price). Categories: transformers, switchgear, panels,
breakers, cable, motors, drives, generators, UPS, lighting. Show low
stock alerts on the dashboard.
```

### 2. Sales & Business Intelligence

**Sales forecasting:**
```
Add a sales forecast to my CRM dashboard. Calculate:
1. Weighted pipeline (deal value × probability) - already have this
2. Monthly forecast based on expected close dates
3. Comparison vs last month/quarter
4. Revenue trend chart (use Chart.js)
Show forecast by month for the next 6 months.
```

**Win/loss analysis:**
```
Add a win/loss analysis report page. Show:
- Win rate by lead source
- Average deal size by stage
- Time to close (created_at to closed_at)
- Lost deal reasons (add a "loss_reason" field to deals)
- Top performing product categories
Display as a report with charts.
```

### 3. Improving the Frontend

**Make it mobile-responsive:**
```
Improve the mobile experience of my CRM. The sidebar should collapse to
a hamburger menu on mobile. The pipeline board should scroll horizontally.
Tables should be scrollable. Forms should stack to single column. Test
at 375px width.
```

**Add dark mode:**
```
Add a dark mode toggle to my CRM. Store the preference in localStorage.
Update the CSS variables in :root to support both themes. Add a toggle
button in the sidebar.
```

### 4. Data & Integrations

**QuickBooks integration:**
```
Add a QuickBooks Online integration to my CRM. When a deal is marked
"closed_won", create an invoice in QuickBooks with the deal value and
contact info. Use the QuickBooks Python SDK. Walk me through the OAuth
setup.
```

**Zapier webhooks:**
```
Add webhook support to my CRM. Fire webhooks on: new contact created,
deal stage changed, deal closed. POST the event data as JSON to a
configurable webhook URL. This lets me connect to Zapier, Make, or
n8n for automations.
```

**Import from spreadsheet:**
```
I have my contacts in an Excel spreadsheet with columns:
Name, Company, Email, Phone, Type (customer/lead), Notes, Equipment Interest.
Write a Python script to parse this and import into my CRM database.
Handle the name splitting (first/last) and map "Equipment Interest" to tags.
```

### 5. Deployment

**Deploy to production:**
```
Help me deploy my Flask CRM to production. I want to:
1. Use gunicorn as the WSGI server
2. Set up nginx as reverse proxy
3. Use a proper PostgreSQL database instead of SQLite
4. Add environment variables for config
5. Set up on a $5/month VPS (DigitalOcean or Linode)
Give me step-by-step commands.
```

**Dockerize it:**
```
Create a Dockerfile and docker-compose.yml for my Flask CRM.
Include the Flask app with gunicorn, and optionally PostgreSQL.
Mount the SQLite database as a volume for persistence.
Expose port 5000.
```

### 6. Security

**Add authentication:**
```
Add user authentication to my Flask CRM. Requirements:
- Login page with username/password
- Password hashing with bcrypt
- Session-based auth (Flask-Login)
- Protect all /api/ routes
- Add a "users" table with role (admin, sales_rep)
- Sales reps can only see their own contacts/deals
Keep it simple, no OAuth needed.
```

---

## Quick One-Liners

| What you want | Prompt |
|---|---|
| Add a field | "Add a 'warranty_expiry' date field to deals in my Flask/SQLite CRM" |
| Bulk update | "Write a script to mark all contacts with no activity in 90 days as 'inactive'" |
| Report | "Add a monthly revenue report endpoint that groups closed-won deals by month" |
| Notification | "Add browser notifications for activities due today using the Notification API" |
| Search | "Add full-text search across contacts, deals, and activities" |
| Backup | "Write a cron script that backs up my SQLite CRM database daily to S3" |
| Chart | "Add a Chart.js pie chart showing deals by stage on the dashboard" |

---

## Tips for Better AI Prompts

1. **Be specific about your stack** - Always mention Python/Flask/SQLite so the AI gives compatible code
2. **Reference existing code** - Say "add to my existing models.py" not "create a new database"
3. **State the constraint** - "No external frameworks for the frontend" keeps answers vanilla JS
4. **Ask for the migration** - When adding fields, ask "include the ALTER TABLE migration"
5. **One feature at a time** - Don't ask for 5 features in one prompt
6. **Include business context** - "I sell electrical equipment to contractors and utilities" gets better field names and sample data
