import { useCallback, useEffect, useState } from "react";
import type { CSSProperties, FormEvent } from "react";

const API_URL = "http://127.0.0.1:8011";

type VerificationStatus = "pending" | "verified" | "rejected" | "legacy";
type Hotel = {
  id: number;
  name: string;
  district: string;
  address: string | null;
  registration_no: string | null;
  accommodation_type: string | null;
  price_per_night: number | null;
  available: boolean;
  is_active: boolean;
  verification_status: VerificationStatus;
};
type HotelForm = {
  name: string;
  address: string;
  district: string;
  registration_no: string;
  accommodation_type: string;
  price_per_night: string;
};
type Filter = "all" | "pending" | "verified" | "legacy" | "rejected";

const emptyForm: HotelForm = {
  name: "", address: "", district: "", registration_no: "",
  accommodation_type: "", price_per_night: "",
};

const inputStyle: CSSProperties = {
  width: "100%", padding: "11px 12px", border: "1px solid #d5dce5",
  borderRadius: 8, boxSizing: "border-box", background: "#fff", color: "#152238",
};
const buttonStyle: CSSProperties = {
  padding: "9px 13px", border: 0, borderRadius: 8,
  background: "#147d64", color: "white", cursor: "pointer", fontWeight: 600,
};
const secondaryButton: CSSProperties = {
  ...buttonStyle, background: "#e9eef3", color: "#26384b",
};

function getToken(): string {
  return sessionStorage.getItem("admin_access_token") || "";
}

async function adminRequest(path: string, options: RequestInit = {}) {
  const token = getToken();
  if (!token) throw new Error("Admin login required. Please log in again.");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  const result: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result && typeof result === "object" && "detail" in result
      ? (result as { detail: unknown }).detail : null;
    const detailText = typeof detail === "string" ? detail :
      Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg || "Invalid field").join("; ") :
      `Request failed (${response.status})`;
    throw new Error(detailText);
  }
  return result;
}

function toForm(hotel: Hotel): HotelForm {
  return {
    name: hotel.name,
    address: hotel.address || "",
    district: hotel.district || "",
    registration_no: hotel.registration_no || "",
    accommodation_type: hotel.accommodation_type || "",
    price_per_night: hotel.price_per_night == null ? "" : String(hotel.price_per_night),
  };
}

function formPayload(form: HotelForm) {
  return {
    name: form.name.trim(),
    address: form.address.trim() || null,
    district: form.district.trim(),
    registration_no: form.registration_no.trim(),
    accommodation_type: form.accommodation_type.trim() || null,
    price_per_night: form.price_per_night.trim() === "" ? null : Number(form.price_per_night),
  };
}

export default function AdminHotelManagement() {
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [form, setForm] = useState<HotelForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadHotels = useCallback(async () => {
    try {
      const result = await adminRequest("/hotels/admin/list");
      if (!Array.isArray(result)) throw new Error("Unexpected hotel list response");
      setHotels(result as Hotel[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load hotels");
    }
  }, []);

  useEffect(() => { void loadHotels(); }, [loadHotels]);

  function updateField(field: keyof HotelForm, value: string) {
    setForm((previous) => ({ ...previous, [field]: value }));
  }

  function startEdit(hotel: Hotel) {
    setEditingId(hotel.id);
    setForm(toForm(hotel));
    setMessage(""); setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() { setEditingId(null); setForm(emptyForm); }

  async function saveHotel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setMessage(""); setError(""); setLoading(true);
    try {
      const editing = editingId !== null;
      const result = await adminRequest(
        editing ? `/hotels/admin/${editingId}` : "/hotels/admin",
        { method: editing ? "PATCH" : "POST", body: JSON.stringify(formPayload(form)) },
      );
      if (!result) throw new Error("Empty server response");
      setMessage(editing ? "Hotel details updated successfully." :
        "Hotel saved. Manual verification is required before publication.");
      cancelEdit();
      await loadHotels();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save hotel");
    } finally { setLoading(false); }
  }

  async function changeVerification(hotel: Hotel, next: "verified" | "rejected" | "pending") {
    if (next === "verified") {
      const confirmed = window.confirm(
        `Have you independently checked official SLTDA registration evidence for "${hotel.name}"?\n\nOnly continue if evidence was actually checked. This action does not contact SLTDA.`,
      );
      if (!confirmed) return;
    } else if (!window.confirm(`Change "${hotel.name}" to ${next}?`)) return;
    setError(""); setMessage(""); setBusyId(hotel.id);
    try {
      await adminRequest(`/hotels/admin/${hotel.id}/verification`, {
        method: "PATCH",
        body: JSON.stringify({ verification_status: next, evidence_checked: next === "verified" }),
      });
      setMessage(`Hotel #${hotel.id} verification status changed to ${next}.`);
      await loadHotels();
    } catch (err) { setError(err instanceof Error ? err.message : "Verification update failed"); }
    finally { setBusyId(null); }
  }

  async function changeActivation(hotel: Hotel) {
    const next = !hotel.is_active;
    if (!window.confirm(`${next ? "Activate" : "Deactivate"} "${hotel.name}"?`)) return;
    setError(""); setMessage(""); setBusyId(hotel.id);
    try {
      await adminRequest(`/hotels/admin/${hotel.id}/activation`, {
        method: "PATCH", body: JSON.stringify({ is_active: next }),
      });
      setMessage(`Hotel #${hotel.id} ${next ? "activated" : "deactivated"}.`);
      await loadHotels();
    } catch (err) { setError(err instanceof Error ? err.message : "Activation update failed"); }
    finally { setBusyId(null); }
  }

  async function changeAvailability(hotel: Hotel) {
    const next = !hotel.available;
    if (!window.confirm(`Set "${hotel.name}" availability to ${next ? "available" : "unavailable"}?`)) return;
    setError(""); setMessage(""); setBusyId(hotel.id);
    try {
      await adminRequest(`/hotels/admin/${hotel.id}`, {
        method: "PATCH", body: JSON.stringify({ available: next }),
      });
      setMessage(`Hotel #${hotel.id} availability updated.`);
      await loadHotels();
    } catch (err) { setError(err instanceof Error ? err.message : "Availability update failed"); }
    finally { setBusyId(null); }
  }

  const shown = hotels.filter((hotel) => {
    const matchesFilter = filter === "all" || hotel.verification_status === filter;
    const q = search.trim().toLowerCase();
    return matchesFilter && (!q || [hotel.name, hotel.district, hotel.registration_no || "", String(hotel.id)]
      .some((value) => value.toLowerCase().includes(q)));
  });
  const counts = {
    all: hotels.length,
    pending: hotels.filter((h) => h.verification_status === "pending").length,
    verified: hotels.filter((h) => h.verification_status === "verified").length,
    legacy: hotels.filter((h) => h.verification_status === "legacy").length,
    rejected: hotels.filter((h) => h.verification_status === "rejected").length,
  };

  return (
    <div style={{ padding: 24, maxWidth: 1120, margin: "auto", color: "#152238" }}>
      <h2>Hotel Management</h2>
      <p>Manage registrations, verification, and hotel visibility in SerendibStay AI.</p>
      {message && <p role="status" style={{ color: "#087443" }}>{message}</p>}
      {error && <p role="alert" style={{ color: "#b42318" }}>{error}</p>}

      <section style={{ background: "#fff", padding: 24, borderRadius: 12, marginBottom: 24 }}>
        <h3>{editingId === null ? "Add New Hotel" : `Edit Hotel #${editingId}`}</h3>
        <form onSubmit={saveHotel}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
            <input style={inputStyle} placeholder="Hotel Name" aria-label="Hotel Name" value={form.name}
              onChange={(e) => updateField("name", e.target.value)} required minLength={2} />
            <input style={inputStyle} placeholder="District" aria-label="District" value={form.district}
              onChange={(e) => updateField("district", e.target.value)} required minLength={2} />
            <input style={inputStyle} placeholder="Address" aria-label="Address" value={form.address}
              onChange={(e) => updateField("address", e.target.value)} />
            <input style={inputStyle} placeholder="SLTDA Registration Number" aria-label="Registration Number"
              value={form.registration_no} onChange={(e) => updateField("registration_no", e.target.value)} required minLength={3} />
            <input style={inputStyle} placeholder="Accommodation Type" aria-label="Accommodation Type"
              value={form.accommodation_type} onChange={(e) => updateField("accommodation_type", e.target.value)} />
            <input style={inputStyle} type="number" min="0" step="0.01" placeholder="Price per Night (LKR)"
              aria-label="Price per Night" value={form.price_per_night}
              onChange={(e) => updateField("price_per_night", e.target.value)} />
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
            <button type="submit" disabled={loading} style={{ ...buttonStyle, opacity: loading ? 0.65 : 1 }}>
              {loading ? "Saving..." : editingId === null ? "Add Hotel" : "Save Changes"}
            </button>
            {editingId !== null && <button type="button" onClick={cancelEdit} style={secondaryButton}>Cancel Edit</button>}
          </div>
        </form>
        <p style={{ fontSize: 13, color: "#526174", marginTop: 12 }}>
          New hotels start as pending, inactive, and unavailable. Verification requires checking official evidence manually.
        </p>
      </section>

      <section style={{ background: "#fff", padding: 24, borderRadius: 12 }}>
        <h3>All Hotels ({hotels.length})</h3>
        <p style={{ color: "#526174" }}>
          Legacy means an existing listing, not officially verified. Public visibility requires active, available, and legacy/verified status.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {(["all", "pending", "verified", "legacy", "rejected"] as Filter[]).map((item) => (
            <button key={item} type="button" onClick={() => setFilter(item)}
              style={{ ...secondaryButton, background: filter === item ? "#147d64" : "#e9eef3",
                color: filter === item ? "white" : "#26384b" }}>
              {item.charAt(0).toUpperCase() + item.slice(1)} ({counts[item]})
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
          <input style={{ ...inputStyle, maxWidth: 360 }} placeholder="Search name, district, registration or ID"
            aria-label="Search hotels" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button type="button" style={secondaryButton} onClick={() => void loadHotels()}>Refresh</button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", minWidth: 900 }}>
            <thead><tr>
              {(["ID", "Hotel", "District", "Verification", "Active", "Available", "Actions"] as const)
                .map((heading) => <th key={heading} style={{ padding: 10, borderBottom: "1px solid #dce3eb" }}>{heading}</th>)}
            </tr></thead>
            <tbody>
              {shown.map((hotel) => (
                <tr key={hotel.id}>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>{hotel.id}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>
                    <strong>{hotel.name}</strong>
                    <div style={{ fontSize: 12, color: "#526174" }}>{hotel.registration_no || "No registration number"}</div>
                  </td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>{hotel.district || "—"}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>{hotel.verification_status}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>{hotel.is_active ? "Yes" : "No"}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>{hotel.available ? "Yes" : "No"}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #edf0f4" }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button type="button" style={secondaryButton} disabled={busyId === hotel.id} onClick={() => startEdit(hotel)}>Edit</button>
                      {hotel.verification_status !== "verified" &&
                        <button type="button" style={buttonStyle} disabled={busyId === hotel.id}
                          onClick={() => void changeVerification(hotel, "verified")}>Verify</button>}
                      {hotel.verification_status === "pending" &&
                        <button type="button" style={{ ...secondaryButton, color: "#b42318" }} disabled={busyId === hotel.id}
                          onClick={() => void changeVerification(hotel, "rejected")}>Reject</button>}
                      {hotel.verification_status === "rejected" &&
                        <button type="button" style={secondaryButton} disabled={busyId === hotel.id}
                          onClick={() => void changeVerification(hotel, "pending")}>Reopen</button>}
                      <button type="button" style={secondaryButton} disabled={busyId === hotel.id ||
                        (!hotel.is_active && !["legacy", "verified"].includes(hotel.verification_status))}
                        onClick={() => void changeActivation(hotel)}>{hotel.is_active ? "Deactivate" : "Activate"}</button>
                      <button type="button" style={secondaryButton} disabled={busyId === hotel.id}
                        onClick={() => void changeAvailability(hotel)}>
                        {hotel.available ? "Set Unavailable" : "Set Available"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {shown.length === 0 && <tr><td colSpan={7} style={{ padding: 20, textAlign: "center" }}>No hotels match this filter.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
