import { useEffect, useState } from "react";

type Provider = {
  id: number;
  provider_name: string;
  phone: string;
  email: string;
  vehicle_type: string;
  vehicle_number: string;
  passenger_capacity: number;
  base_district: string;
  service_districts: string[];
  approved: boolean;
  available: boolean;
};

function AdminProviderApproval() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  // =========================================================
  // LOAD ALL TRANSPORT PROVIDERS
  // =========================================================

  useEffect(() => {
    const loadProviders = async () => {
      try {
        setLoading(true);
        setMessage("");

        const token = sessionStorage.getItem(
          "admin_access_token"
        );

        if (!token) {
          setMessage(
            "Admin session not found. Please login again."
          );
          setLoading(false);
          return;
        }

        const response = await fetch(
          "http://127.0.0.1:8001/transport/providers",
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.status === 401) {
          sessionStorage.removeItem(
            "admin_access_token"
          );

          setMessage(
            "Admin session expired or is invalid. Please login again."
          );

          return;
        }

        if (!response.ok) {
          throw new Error(
            "Failed to load providers"
          );
        }

        const data: Provider[] =
          await response.json();

        setProviders(data);
      } catch (error) {
        console.error(
          "Load providers error:",
          error
        );

        setMessage(
          "Failed to load transport providers."
        );
      } finally {
        setLoading(false);
      }
    };

    loadProviders();
  }, []);

  // =========================================================
  // APPROVE TRANSPORT PROVIDER
  // =========================================================

  const approveProvider = async (
    providerId: number
  ) => {
    try {
      setMessage("");

      const token = sessionStorage.getItem(
        "admin_access_token"
      );

      if (!token) {
        setMessage(
          "Admin session not found. Please login again."
        );

        return;
      }

      const response = await fetch(
        `http://127.0.0.1:8001/transport/providers/${providerId}/approve`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.status === 401) {
        sessionStorage.removeItem(
          "admin_access_token"
        );

        setMessage(
          "Admin session expired or is invalid. Please login again."
        );

        return;
      }

      if (!response.ok) {
        throw new Error(
          "Failed to approve provider"
        );
      }

      setProviders((currentProviders) =>
        currentProviders.map((provider) =>
          provider.id === providerId
            ? {
                ...provider,
                approved: true,
              }
            : provider
        )
      );

      setMessage(
        "Transport provider approved successfully."
      );
    } catch (error) {
      console.error(
        "Approve provider error:",
        error
      );

      setMessage(
        "Failed to approve transport provider."
      );
    }
  };

  // =========================================================
  // SEPARATE PROVIDERS
  // =========================================================

  const pendingProviders = providers.filter(
    (provider) => !provider.approved
  );

  const approvedProviders = providers.filter(
    (provider) => provider.approved
  );

  // =========================================================
  // PROVIDER CARD
  // =========================================================

  const renderProviderCard = (
    provider: Provider
  ) => (
    <div
      className="admin-provider-item"
      key={provider.id}
    >
      <div className="provider-card-header">
        <div>
          <span className="provider-id">
            Provider #{provider.id}
          </span>

          <h3>
            {provider.provider_name}
          </h3>
        </div>

        <span
          className={
            provider.approved
              ? "status-badge approved"
              : "status-badge pending"
          }
        >
          {provider.approved
            ? "Approved"
            : "Pending"}
        </span>
      </div>

      <div className="provider-details-grid">
        <div className="provider-detail">
          <span>Vehicle Type</span>

          <strong>
            {provider.vehicle_type}
          </strong>
        </div>

        <div className="provider-detail">
          <span>Vehicle Number</span>

          <strong>
            {provider.vehicle_number}
          </strong>
        </div>

        <div className="provider-detail">
          <span>Passenger Capacity</span>

          <strong>
            {provider.passenger_capacity}
          </strong>
        </div>

        <div className="provider-detail">
          <span>Base District</span>

          <strong>
            {provider.base_district}
          </strong>
        </div>

        <div className="provider-detail">
          <span>Phone</span>

          <strong>
            {provider.phone}
          </strong>
        </div>

        <div className="provider-detail">
          <span>Email</span>

          <strong>
            {provider.email}
          </strong>
        </div>
      </div>

      <div className="provider-service-area">
        <span className="service-title">
          Service Districts
        </span>

        <div className="service-district-chips">
          {provider.service_districts.map(
            (district) => (
              <span
                className="service-chip"
                key={district}
              >
                {district}
              </span>
            )
          )}
        </div>
      </div>

      {!provider.approved && (
        <button
          type="button"
          className="approve-provider-button"
          onClick={() =>
            approveProvider(provider.id)
          }
        >
          Approve Provider
        </button>
      )}
    </div>
  );

  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="admin-provider-page">
      <div className="admin-provider-card">

        {/* Page heading */}
        <div className="admin-provider-heading">
          <div>
            <h2>
              Transport Provider Management
            </h2>

            <p>
              Review registered transport
              providers and approve them before
              they become available to customers.
            </p>
          </div>

          <span className="admin-badge">
            Admin Panel
          </span>
        </div>

        {/* Success / Error message */}
        {message && (
          <div className="admin-message">
            {message}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <p>Loading providers...</p>
        ) : providers.length === 0 ? (
          <div className="no-providers">
            <h3>No providers found</h3>

            <p>
              There are currently no registered
              transport providers.
            </p>
          </div>
        ) : (
          <>
            {/* Pending Providers */}
            <div className="provider-section">
              <div className="provider-section-header">
                <div>
                  <h3>
                    Pending Providers
                  </h3>

                  <p>
                    Providers waiting for
                    administrator approval.
                  </p>
                </div>

                <span className="provider-count pending-count">
                  {pendingProviders.length}
                </span>
              </div>

              {pendingProviders.length === 0 ? (
                <div className="no-providers">
                  <h3>
                    No Pending Providers
                  </h3>

                  <p>
                    All registered transport
                    providers are approved.
                  </p>
                </div>
              ) : (
                <div className="provider-list">
                  {pendingProviders.map(
                    (provider) =>
                      renderProviderCard(
                        provider
                      )
                  )}
                </div>
              )}
            </div>

            {/* Approved Providers */}
            <div className="provider-section approved-section">
              <div className="provider-section-header">
                <div>
                  <h3>
                    Approved Providers
                  </h3>

                  <p>
                    Transport providers approved
                    by the administrator.
                  </p>
                </div>

                <span className="provider-count approved-count">
                  {approvedProviders.length}
                </span>
              </div>

              {approvedProviders.length === 0 ? (
                <div className="no-providers">
                  <h3>
                    No Approved Providers
                  </h3>

                  <p>
                    No transport providers have
                    been approved yet.
                  </p>
                </div>
              ) : (
                <div className="provider-list">
                  {approvedProviders.map(
                    (provider) =>
                      renderProviderCard(
                        provider
                      )
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AdminProviderApproval;