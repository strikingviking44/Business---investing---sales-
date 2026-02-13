"""
Seed the CRM database with sample electrical equipment sales data.
Run: python crm/seed.py
"""

from models import init_db, create_contact, create_deal, create_activity

def seed():
    init_db()

    # --- Contacts: Electrical Equipment Buyers & Prospects ---
    contacts = [
        {
            "first_name": "Michael", "last_name": "Torres",
            "email": "mtorres@greenfieldconstruction.com", "phone": "(512) 555-0142",
            "company": "Greenfield Construction", "title": "Electrical Project Manager",
            "status": "customer", "source": "Trade Show",
            "tags": "transformers, switchgear, commercial",
            "notes": "Major commercial builder in TX. Repeat buyer. Prefers Eaton and Siemens."
        },
        {
            "first_name": "Sarah", "last_name": "Chen",
            "email": "schen@voltaenergy.com", "phone": "(408) 555-0198",
            "company": "Volta Energy Solutions", "title": "Procurement Director",
            "status": "customer", "source": "Referral",
            "tags": "solar, inverters, panels, renewable",
            "notes": "Solar installation company. Buys inverters, panels, and distribution boards in bulk."
        },
        {
            "first_name": "James", "last_name": "Patterson",
            "email": "jpatterson@midwestelectric.com", "phone": "(614) 555-0267",
            "company": "Midwest Electric Co-op", "title": "Supply Chain Manager",
            "status": "prospect", "source": "Cold Call",
            "tags": "utility, transformers, high-voltage, poles",
            "notes": "Rural utility. Looking to upgrade aging transformer fleet. Budget cycle Q2."
        },
        {
            "first_name": "Linda", "last_name": "Okafor",
            "email": "lokafor@apexdatacenters.com", "phone": "(703) 555-0331",
            "company": "Apex Data Centers", "title": "VP of Infrastructure",
            "status": "prospect", "source": "Website",
            "tags": "UPS, PDU, generators, data-center",
            "notes": "Expanding data center campus. Needs redundant power distribution. High-value opportunity."
        },
        {
            "first_name": "Robert", "last_name": "Kim",
            "email": "rkim@precisionmfg.com", "phone": "(313) 555-0415",
            "company": "Precision Manufacturing", "title": "Maintenance Director",
            "status": "customer", "source": "Trade Show",
            "tags": "motors, drives, VFD, industrial",
            "notes": "Auto parts manufacturer. Regular orders for motors and variable frequency drives."
        },
        {
            "first_name": "Angela", "last_name": "Brooks",
            "email": "abrooks@summitdevelopment.com", "phone": "(305) 555-0489",
            "company": "Summit Development Group", "title": "Project Coordinator",
            "status": "lead", "source": "LinkedIn",
            "tags": "residential, panels, breakers, wiring",
            "notes": "Residential developer in FL. Building 200-unit condo project. Needs full electrical package."
        },
        {
            "first_name": "David", "last_name": "Martinez",
            "email": "dmartinez@powerlineinc.com", "phone": "(713) 555-0523",
            "company": "PowerLine Inc.", "title": "Operations Manager",
            "status": "lead", "source": "Referral",
            "tags": "cable, conduit, connectors, wholesale",
            "notes": "Electrical contractor. Looking for reliable wholesale supplier for cable and conduit."
        },
        {
            "first_name": "Karen", "last_name": "Nguyen",
            "email": "knguyen@tristatehospitals.org", "phone": "(215) 555-0687",
            "company": "Tri-State Hospital Network", "title": "Facilities Manager",
            "status": "prospect", "source": "Cold Call",
            "tags": "generators, transfer-switch, emergency, medical",
            "notes": "Hospital network upgrading emergency power systems. NFPA 110 compliance required."
        },
        {
            "first_name": "William", "last_name": "Foster",
            "email": "wfoster@suncoastschools.edu", "phone": "(941) 555-0751",
            "company": "Suncoast School District", "title": "Director of Facilities",
            "status": "lead", "source": "Website",
            "tags": "lighting, LED, retrofit, education",
            "notes": "LED lighting retrofit project across 45 schools. Government procurement process."
        },
        {
            "first_name": "Patricia", "last_name": "Walsh",
            "email": "pwalsh@atlanticshipyard.com", "phone": "(757) 555-0834",
            "company": "Atlantic Shipyard", "title": "Chief Electrician",
            "status": "inactive", "source": "Trade Show",
            "tags": "marine, cable, waterproof, industrial",
            "notes": "Marine electrical specialist. Previous customer, went quiet 6 months ago."
        },
    ]

    contact_ids = []
    for c in contacts:
        cid = create_contact(c)
        contact_ids.append(cid)
        print(f"  Contact: {c['first_name']} {c['last_name']} ({c['company']})")

    # --- Deals: Electrical Equipment Sales Pipeline ---
    deals = [
        {"contact_id": contact_ids[0], "title": "500kVA Pad-Mount Transformer Order",
         "value": 87500, "stage": "closed_won", "probability": 100,
         "notes": "Delivered and installed. Invoice paid NET30."},
        {"contact_id": contact_ids[0], "title": "Main Switchgear - Phase 2 Expansion",
         "value": 145000, "stage": "proposal", "probability": 60,
         "expected_close": "2026-04-15",
         "notes": "Waiting on architect final specs. Eaton VCP-W breakers quoted."},
        {"contact_id": contact_ids[1], "title": "200x SolarEdge Inverters Bulk Order",
         "value": 320000, "stage": "negotiation", "probability": 75,
         "expected_close": "2026-03-20",
         "notes": "Price negotiation in progress. Competing with another distributor."},
        {"contact_id": contact_ids[2], "title": "Transformer Fleet Upgrade (50 units)",
         "value": 625000, "stage": "qualified", "probability": 30,
         "expected_close": "2026-06-30",
         "notes": "Budget approval pending board meeting in March. 25kVA-167kVA range."},
        {"contact_id": contact_ids[3], "title": "UPS Systems - New Data Hall",
         "value": 480000, "stage": "proposal", "probability": 50,
         "expected_close": "2026-05-01",
         "notes": "Quoted Vertiv Liebert EXL S1 800kVA. Redundant N+1 config."},
        {"contact_id": contact_ids[3], "title": "PDU Rollout - 200 Racks",
         "value": 156000, "stage": "qualified", "probability": 40,
         "expected_close": "2026-05-15",
         "notes": "ServerTech PRO2 units. Dependent on data hall deal closing."},
        {"contact_id": contact_ids[4], "title": "Motor Replacement Program Q1",
         "value": 45000, "stage": "closed_won", "probability": 100,
         "notes": "12x 50HP WEG motors delivered. Regular quarterly order."},
        {"contact_id": contact_ids[4], "title": "VFD Upgrade - Assembly Line 3",
         "value": 68000, "stage": "negotiation", "probability": 80,
         "expected_close": "2026-03-10",
         "notes": "ABB ACS580 drives. Customer wants extended warranty included."},
        {"contact_id": contact_ids[5], "title": "Full Electrical Package - Bayshore Condos",
         "value": 890000, "stage": "lead", "probability": 15,
         "expected_close": "2026-08-01",
         "notes": "200-unit condo. Panels, breakers, wiring, meters. Very early stage."},
        {"contact_id": contact_ids[6], "title": "Cable & Conduit Supply Agreement",
         "value": 210000, "stage": "lead", "probability": 20,
         "expected_close": "2026-07-01",
         "notes": "Annual supply contract. Need to beat current supplier pricing by 8%."},
        {"contact_id": contact_ids[7], "title": "Emergency Generator Upgrade - 3 Hospitals",
         "value": 375000, "stage": "qualified", "probability": 45,
         "expected_close": "2026-06-15",
         "notes": "Cat C15 generators. Transfer switches included. NFPA 110 compliant."},
        {"contact_id": contact_ids[8], "title": "LED Retrofit - 45 Schools",
         "value": 520000, "stage": "lead", "probability": 10,
         "expected_close": "2026-09-01",
         "notes": "Government RFP expected Q2. Need to pre-qualify as vendor."},
        {"contact_id": contact_ids[9], "title": "Marine Cable Restock",
         "value": 35000, "stage": "closed_lost", "probability": 0,
         "notes": "Lost to competitor. Lower pricing on marine-rated cable."},
    ]

    for d in deals:
        create_deal(d)
        print(f"  Deal: {d['title']} ({d['stage']}) - ${d['value']:,.0f}")

    # --- Activities ---
    activities = [
        {"contact_id": contact_ids[0], "type": "meeting", "subject": "Site visit - Phase 2 electrical room",
         "description": "Reviewed electrical room layout for switchgear installation."},
        {"contact_id": contact_ids[0], "type": "email", "subject": "Sent updated switchgear quote",
         "description": "Updated pricing per revised specs. Valid 30 days."},
        {"contact_id": contact_ids[1], "type": "call", "subject": "Pricing negotiation - inverter order",
         "description": "They want 8% discount on 200-unit order. Checking with supplier."},
        {"contact_id": contact_ids[1], "type": "follow_up", "subject": "Send revised pricing by Friday",
         "description": "Need supplier approval for volume discount.", "completed": 0},
        {"contact_id": contact_ids[2], "type": "call", "subject": "Intro call - transformer fleet needs",
         "description": "50 unit replacement over 2 years. Mix of 25kVA to 167kVA."},
        {"contact_id": contact_ids[2], "type": "task", "subject": "Prepare transformer fleet proposal",
         "description": "Include phased delivery schedule and financing options.", "completed": 0},
        {"contact_id": contact_ids[3], "type": "meeting", "subject": "Data center tour and power assessment",
         "description": "Toured new data hall. 2MW total capacity needed."},
        {"contact_id": contact_ids[3], "type": "email", "subject": "UPS technical specifications sent",
         "description": "Vertiv Liebert EXL S1 cut sheets and config options."},
        {"contact_id": contact_ids[4], "type": "note", "subject": "Quarterly motor order confirmed",
         "description": "Standard Q1 reorder. Same specs as last quarter."},
        {"contact_id": contact_ids[4], "type": "follow_up", "subject": "Follow up on VFD warranty terms",
         "description": "Customer wants 3-year warranty. Standard is 2. Escalate to ABB rep.", "completed": 0},
        {"contact_id": contact_ids[5], "type": "email", "subject": "Intro email - Bayshore Condos project",
         "description": "Sent capabilities overview and reference projects."},
        {"contact_id": contact_ids[6], "type": "call", "subject": "Discovery call - supply needs",
         "description": "Currently buying from Graybar. Want better pricing and delivery."},
        {"contact_id": contact_ids[7], "type": "meeting", "subject": "Hospital site assessments",
         "description": "Visited 2 of 3 hospitals. Existing generators are 15+ years old."},
        {"contact_id": contact_ids[7], "type": "task", "subject": "Get Cat C15 pricing from Caterpillar dealer",
         "description": "Need dealer pricing for 3x 500kW units with ATS.", "completed": 0},
        {"contact_id": contact_ids[8], "type": "email", "subject": "Vendor pre-qualification form submitted",
         "description": "Submitted district vendor registration. Awaiting approval."},
    ]

    for a in activities:
        create_activity(a)
        print(f"  Activity: [{a['type']}] {a['subject']}")

    print(f"\nSeeded: {len(contacts)} contacts, {len(deals)} deals, {len(activities)} activities")


if __name__ == "__main__":
    print("Seeding Electrical Equipment Sales CRM...\n")
    seed()
    print("\nDone! Run 'python crm/app.py' to start the CRM.")
