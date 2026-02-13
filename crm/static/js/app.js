/**
 * Electrical Equipment Sales CRM - Frontend Application
 */

const API = "";

// === Navigation ===
document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const view = link.dataset.view;
    document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
    link.classList.add("active");
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    document.getElementById("view-" + view).classList.add("active");
    loadView(view);
  });
});

function loadView(view) {
  if (view === "dashboard") loadDashboard();
  else if (view === "contacts") loadContacts();
  else if (view === "deals") loadDeals();
  else if (view === "activities") loadActivities();
}

// === Utility ===
function money(val) {
  return "$" + Number(val || 0).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return res.json();
}

// === Dashboard ===
async function loadDashboard() {
  const data = await api("/api/dashboard");

  document.getElementById("m-total-contacts").textContent = data.total_contacts || 0;
  document.getElementById("m-revenue").textContent = money(data.total_revenue);
  document.getElementById("m-pipeline").textContent = money(data.open_pipeline_value);
  document.getElementById("m-weighted").textContent = money(data.weighted_pipeline);
  document.getElementById("m-winrate").textContent = (data.win_rate || 0) + "%";
  document.getElementById("m-pending").textContent = data.pending_activities || 0;

  // Pipeline bars
  const stages = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"];
  const pipeline = data.pipeline || {};
  const maxVal = Math.max(...stages.map((s) => (pipeline[s]?.value || 0)), 1);
  const barsEl = document.getElementById("pipeline-bars");
  barsEl.innerHTML = stages
    .map((s) => {
      const val = pipeline[s]?.value || 0;
      const count = pipeline[s]?.count || 0;
      const pct = (val / maxVal) * 100;
      const label = s.replace("_", " ");
      return `<div class="bar-row">
        <span class="label">${label}</span>
        <div class="bar"><div class="bar-fill" style="width:${pct}%">${count}</div></div>
        <span class="value">${money(val)}</span>
      </div>`;
    })
    .join("");

  // Recent activities
  const listEl = document.getElementById("recent-activities");
  listEl.innerHTML = (data.recent_activities || [])
    .map(
      (a) =>
        `<li>
          <span><span class="activity-type">${a.type}</span>${a.subject} - ${a.contact_name}</span>
          <span style="color:var(--text-muted);font-size:12px">${a.created_at?.slice(0, 10) || ""}</span>
        </li>`
    )
    .join("") || "<li>No recent activities</li>";
}

// === Contacts ===
let contactsDebounce;

document.getElementById("contact-search")?.addEventListener("input", () => {
  clearTimeout(contactsDebounce);
  contactsDebounce = setTimeout(loadContacts, 300);
});

document.getElementById("contact-status-filter")?.addEventListener("change", loadContacts);

async function loadContacts() {
  const search = document.getElementById("contact-search").value;
  const status = document.getElementById("contact-status-filter").value;
  let url = "/api/contacts?";
  if (search) url += "search=" + encodeURIComponent(search) + "&";
  if (status) url += "status=" + encodeURIComponent(status);
  const contacts = await api(url);

  document.getElementById("contacts-body").innerHTML = contacts
    .map(
      (c) =>
        `<tr>
          <td><strong>${c.first_name} ${c.last_name}</strong>${c.title ? "<br><small style='color:var(--text-muted)'>" + c.title + "</small>" : ""}</td>
          <td>${c.company || "-"}</td>
          <td>${c.email || "-"}</td>
          <td>${c.phone || "-"}</td>
          <td><span class="badge badge-${c.status}">${c.status}</span></td>
          <td>${c.tags || "-"}</td>
          <td>
            <button class="btn btn-sm btn-outline" onclick="editContact(${c.id})">Edit</button>
            <button class="btn btn-sm btn-danger" onclick="removeContact(${c.id})">Del</button>
          </td>
        </tr>`
    )
    .join("") || '<tr><td colspan="7" style="text-align:center;padding:32px">No contacts yet. Add your first contact!</td></tr>';
}

function showContactForm(data = null) {
  const isEdit = !!data;
  document.getElementById("modal-title").textContent = isEdit ? "Edit Contact" : "New Contact";
  document.getElementById("modal-body").innerHTML = `
    <form id="contact-form" onsubmit="saveContact(event, ${data?.id || "null"})">
      <div class="form-row">
        <div class="form-group">
          <label>First Name *</label>
          <input name="first_name" required value="${data?.first_name || ""}">
        </div>
        <div class="form-group">
          <label>Last Name *</label>
          <input name="last_name" required value="${data?.last_name || ""}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Email</label>
          <input name="email" type="email" value="${data?.email || ""}">
        </div>
        <div class="form-group">
          <label>Phone</label>
          <input name="phone" value="${data?.phone || ""}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Company</label>
          <input name="company" value="${data?.company || ""}">
        </div>
        <div class="form-group">
          <label>Title</label>
          <input name="title" value="${data?.title || ""}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Status</label>
          <select name="status">
            <option value="lead" ${data?.status === "lead" ? "selected" : ""}>Lead</option>
            <option value="prospect" ${data?.status === "prospect" ? "selected" : ""}>Prospect</option>
            <option value="customer" ${data?.status === "customer" ? "selected" : ""}>Customer</option>
            <option value="churned" ${data?.status === "churned" ? "selected" : ""}>Churned</option>
            <option value="inactive" ${data?.status === "inactive" ? "selected" : ""}>Inactive</option>
          </select>
        </div>
        <div class="form-group">
          <label>Source</label>
          <input name="source" placeholder="e.g. Trade Show, Referral, Website" value="${data?.source || ""}">
        </div>
      </div>
      <div class="form-group">
        <label>Tags (comma separated)</label>
        <input name="tags" placeholder="e.g. transformers, switchgear, high-voltage" value="${data?.tags || ""}">
      </div>
      <div class="form-group">
        <label>Notes</label>
        <textarea name="notes" placeholder="Equipment interests, project details...">${data?.notes || ""}</textarea>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">${isEdit ? "Update" : "Create"} Contact</button>
      </div>
    </form>
  `;
  openModal();
}

async function saveContact(e, id) {
  e.preventDefault();
  const form = new FormData(e.target);
  const data = Object.fromEntries(form.entries());

  if (id) {
    await api("/api/contacts/" + id, { method: "PUT", body: data });
  } else {
    await api("/api/contacts", { method: "POST", body: data });
  }
  closeModal();
  loadContacts();
}

async function editContact(id) {
  const res = await api("/api/contacts/" + id);
  showContactForm(res.contact);
}

async function removeContact(id) {
  if (!confirm("Delete this contact and all associated deals/activities?")) return;
  await api("/api/contacts/" + id, { method: "DELETE" });
  loadContacts();
}

// === Deals ===
async function loadDeals() {
  const deals = await api("/api/deals");
  const stages = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"];

  stages.forEach((stage) => {
    const el = document.getElementById("deals-" + stage);
    const stageDeals = deals.filter((d) => d.stage === stage);
    el.innerHTML = stageDeals
      .map(
        (d) =>
          `<div class="deal-card" onclick="editDeal(${d.id})">
            <div class="deal-title">${d.title}</div>
            <div class="deal-company">${d.contact_name} ${d.company ? "- " + d.company : ""}</div>
            <div class="deal-meta">
              <span class="deal-value">${money(d.value)}</span>
              <span class="deal-prob">${d.probability}%</span>
            </div>
          </div>`
      )
      .join("") || '<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:13px">No deals</div>';
  });
}

async function showDealForm(data = null) {
  const isEdit = !!data;
  const contacts = await api("/api/contacts");
  const contactOptions = contacts
    .map((c) => `<option value="${c.id}" ${data?.contact_id === c.id ? "selected" : ""}>${c.first_name} ${c.last_name} - ${c.company || "N/A"}</option>`)
    .join("");

  document.getElementById("modal-title").textContent = isEdit ? "Edit Deal" : "New Deal";
  document.getElementById("modal-body").innerHTML = `
    <form id="deal-form" onsubmit="saveDeal(event, ${data?.id || "null"})">
      <div class="form-group">
        <label>Contact *</label>
        <select name="contact_id" required>${contactOptions}</select>
      </div>
      <div class="form-group">
        <label>Deal Title *</label>
        <input name="title" required placeholder="e.g. 500kVA Transformer Supply" value="${data?.title || ""}">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Value ($)</label>
          <input name="value" type="number" step="0.01" placeholder="e.g. 75000" value="${data?.value || ""}">
        </div>
        <div class="form-group">
          <label>Probability (%)</label>
          <input name="probability" type="number" min="0" max="100" value="${data?.probability || 10}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Stage</label>
          <select name="stage">
            <option value="lead" ${data?.stage === "lead" ? "selected" : ""}>Lead</option>
            <option value="qualified" ${data?.stage === "qualified" ? "selected" : ""}>Qualified</option>
            <option value="proposal" ${data?.stage === "proposal" ? "selected" : ""}>Proposal</option>
            <option value="negotiation" ${data?.stage === "negotiation" ? "selected" : ""}>Negotiation</option>
            <option value="closed_won" ${data?.stage === "closed_won" ? "selected" : ""}>Closed Won</option>
            <option value="closed_lost" ${data?.stage === "closed_lost" ? "selected" : ""}>Closed Lost</option>
          </select>
        </div>
        <div class="form-group">
          <label>Expected Close</label>
          <input name="expected_close" type="date" value="${data?.expected_close || ""}">
        </div>
      </div>
      <div class="form-group">
        <label>Notes</label>
        <textarea name="notes" placeholder="Equipment specs, delivery requirements...">${data?.notes || ""}</textarea>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
        ${isEdit ? `<button type="button" class="btn btn-danger" onclick="removeDeal(${data.id})">Delete</button>` : ""}
        <button type="submit" class="btn btn-primary">${isEdit ? "Update" : "Create"} Deal</button>
      </div>
    </form>
  `;
  openModal();
}

async function saveDeal(e, id) {
  e.preventDefault();
  const form = new FormData(e.target);
  const data = Object.fromEntries(form.entries());
  data.value = parseFloat(data.value) || 0;
  data.probability = parseInt(data.probability) || 10;
  data.contact_id = parseInt(data.contact_id);

  if (id) {
    await api("/api/deals/" + id, { method: "PUT", body: data });
  } else {
    await api("/api/deals", { method: "POST", body: data });
  }
  closeModal();
  loadDeals();
}

async function editDeal(id) {
  const res = await api("/api/deals/" + id);
  showDealForm(res.deal);
}

async function removeDeal(id) {
  if (!confirm("Delete this deal?")) return;
  await api("/api/deals/" + id, { method: "DELETE" });
  closeModal();
  loadDeals();
}

// === Activities ===
document.getElementById("activity-type-filter")?.addEventListener("change", loadActivities);
document.getElementById("pending-only")?.addEventListener("change", loadActivities);

async function loadActivities() {
  const type = document.getElementById("activity-type-filter").value;
  const pending = document.getElementById("pending-only").checked;
  let url = "/api/activities?";
  if (type) url += "type=" + encodeURIComponent(type) + "&";
  if (pending) url += "pending=true";
  const activities = await api(url);

  document.getElementById("activities-body").innerHTML = activities
    .map(
      (a) =>
        `<tr>
          <td><span class="activity-type">${a.type}</span></td>
          <td><strong>${a.subject}</strong>${a.description ? "<br><small>" + a.description + "</small>" : ""}</td>
          <td>${a.contact_name}</td>
          <td>${a.created_at?.slice(0, 10) || "-"}</td>
          <td>${a.completed ? '<span class="badge badge-customer">Done</span>' : '<span class="badge badge-prospect">Pending</span>'}</td>
          <td>${!a.completed ? `<button class="btn btn-sm btn-success" onclick="markDone(${a.id})">Done</button>` : ""}</td>
        </tr>`
    )
    .join("") || '<tr><td colspan="6" style="text-align:center;padding:32px">No activities. Log your first one!</td></tr>';
}

async function showActivityForm() {
  const contacts = await api("/api/contacts");
  const contactOptions = contacts
    .map((c) => `<option value="${c.id}">${c.first_name} ${c.last_name} - ${c.company || "N/A"}</option>`)
    .join("");

  document.getElementById("modal-title").textContent = "Log Activity";
  document.getElementById("modal-body").innerHTML = `
    <form id="activity-form" onsubmit="saveActivity(event)">
      <div class="form-row">
        <div class="form-group">
          <label>Contact *</label>
          <select name="contact_id" required>${contactOptions}</select>
        </div>
        <div class="form-group">
          <label>Type *</label>
          <select name="type" required>
            <option value="call">Call</option>
            <option value="email">Email</option>
            <option value="meeting">Meeting</option>
            <option value="note">Note</option>
            <option value="task">Task</option>
            <option value="follow_up">Follow-up</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Subject *</label>
        <input name="subject" required placeholder="e.g. Discussed 200A panel board specs">
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea name="description" placeholder="Details about the interaction..."></textarea>
      </div>
      <div class="form-group">
        <label>Due Date</label>
        <input name="due_date" type="date">
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Log Activity</button>
      </div>
    </form>
  `;
  openModal();
}

async function saveActivity(e) {
  e.preventDefault();
  const form = new FormData(e.target);
  const data = Object.fromEntries(form.entries());
  data.contact_id = parseInt(data.contact_id);
  await api("/api/activities", { method: "POST", body: data });
  closeModal();
  loadActivities();
}

async function markDone(id) {
  await api("/api/activities/" + id + "/complete", { method: "POST" });
  loadActivities();
}

// === Modal ===
function openModal() {
  document.getElementById("modal-overlay").classList.add("active");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("active");
}

// === Init ===
loadDashboard();
