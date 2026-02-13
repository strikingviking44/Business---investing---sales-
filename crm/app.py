"""
Electrical Equipment Sales CRM - Main Application
Full-featured CRM for managing electrical equipment sales pipeline.
"""

import csv
import io
from flask import Flask, request, jsonify, render_template, send_file

from models import (
    init_db,
    create_contact, get_contacts, get_contact, update_contact, delete_contact,
    create_deal, get_deals, get_deal, update_deal, delete_deal,
    create_activity, get_activities, complete_activity,
    get_dashboard_metrics,
)

app = Flask(__name__)


# --- Pages ---

@app.route("/")
def index():
    return render_template("index.html")


# --- Contact API ---

@app.route("/api/contacts", methods=["GET"])
def api_list_contacts():
    search = request.args.get("search")
    status = request.args.get("status")
    tag = request.args.get("tag")
    contacts = get_contacts(search=search, status=status, tag=tag)
    return jsonify(contacts)


@app.route("/api/contacts", methods=["POST"])
def api_create_contact():
    data = request.get_json()
    if not data or not data.get("first_name") or not data.get("last_name"):
        return jsonify({"error": "first_name and last_name are required"}), 400
    contact_id = create_contact(data)
    return jsonify({"id": contact_id, "message": "Contact created"}), 201


@app.route("/api/contacts/<int:contact_id>", methods=["GET"])
def api_get_contact(contact_id):
    contact = get_contact(contact_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    deals = get_deals(contact_id=contact_id)
    activities = get_activities(contact_id=contact_id)
    return jsonify({"contact": contact, "deals": deals, "activities": activities})


@app.route("/api/contacts/<int:contact_id>", methods=["PUT"])
def api_update_contact(contact_id):
    data = request.get_json()
    if not get_contact(contact_id):
        return jsonify({"error": "Contact not found"}), 404
    update_contact(contact_id, data)
    return jsonify({"message": "Contact updated"})


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
def api_delete_contact(contact_id):
    if not get_contact(contact_id):
        return jsonify({"error": "Contact not found"}), 404
    delete_contact(contact_id)
    return jsonify({"message": "Contact deleted"})


# --- CSV Import / Export ---

@app.route("/api/contacts/export", methods=["GET"])
def api_export_contacts():
    contacts = get_contacts()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "first_name", "last_name", "email", "phone",
        "company", "title", "status", "source", "tags", "notes",
        "created_at", "updated_at"
    ])
    writer.writeheader()
    for c in contacts:
        writer.writerow(c)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="contacts_export.csv"
    )


@app.route("/api/contacts/import", methods=["POST"])
def api_import_contacts():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)
    count = 0
    for row in reader:
        if row.get("first_name") and row.get("last_name"):
            create_contact(row)
            count += 1
    return jsonify({"message": f"Imported {count} contacts"})


# --- Deal API ---

@app.route("/api/deals", methods=["GET"])
def api_list_deals():
    stage = request.args.get("stage")
    contact_id = request.args.get("contact_id", type=int)
    deals = get_deals(stage=stage, contact_id=contact_id)
    return jsonify(deals)


@app.route("/api/deals", methods=["POST"])
def api_create_deal():
    data = request.get_json()
    if not data or not data.get("contact_id") or not data.get("title"):
        return jsonify({"error": "contact_id and title are required"}), 400
    if not get_contact(data["contact_id"]):
        return jsonify({"error": "Contact not found"}), 404
    deal_id = create_deal(data)
    return jsonify({"id": deal_id, "message": "Deal created"}), 201


@app.route("/api/deals/<int:deal_id>", methods=["GET"])
def api_get_deal(deal_id):
    deal = get_deal(deal_id)
    if not deal:
        return jsonify({"error": "Deal not found"}), 404
    activities = get_activities(deal_id=deal_id)
    return jsonify({"deal": deal, "activities": activities})


@app.route("/api/deals/<int:deal_id>", methods=["PUT"])
def api_update_deal(deal_id):
    data = request.get_json()
    if not get_deal(deal_id):
        return jsonify({"error": "Deal not found"}), 404
    update_deal(deal_id, data)
    return jsonify({"message": "Deal updated"})


@app.route("/api/deals/<int:deal_id>", methods=["DELETE"])
def api_delete_deal(deal_id):
    if not get_deal(deal_id):
        return jsonify({"error": "Deal not found"}), 404
    delete_deal(deal_id)
    return jsonify({"message": "Deal deleted"})


# --- Activity API ---

@app.route("/api/activities", methods=["GET"])
def api_list_activities():
    contact_id = request.args.get("contact_id", type=int)
    deal_id = request.args.get("deal_id", type=int)
    activity_type = request.args.get("type")
    pending = request.args.get("pending", "").lower() == "true"
    activities = get_activities(
        contact_id=contact_id, deal_id=deal_id,
        activity_type=activity_type, pending_only=pending
    )
    return jsonify(activities)


@app.route("/api/activities", methods=["POST"])
def api_create_activity():
    data = request.get_json()
    if not data or not data.get("contact_id") or not data.get("type") or not data.get("subject"):
        return jsonify({"error": "contact_id, type, and subject are required"}), 400
    valid_types = ("call", "email", "meeting", "note", "task", "follow_up")
    if data["type"] not in valid_types:
        return jsonify({"error": f"type must be one of: {', '.join(valid_types)}"}), 400
    activity_id = create_activity(data)
    return jsonify({"id": activity_id, "message": "Activity logged"}), 201


@app.route("/api/activities/<int:activity_id>/complete", methods=["POST"])
def api_complete_activity(activity_id):
    complete_activity(activity_id)
    return jsonify({"message": "Activity completed"})


# --- Dashboard ---

@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    return jsonify(get_dashboard_metrics())


if __name__ == "__main__":
    init_db()
    print("Electrical Equipment Sales CRM running on http://localhost:5000")
    app.run(debug=True, port=5000)
