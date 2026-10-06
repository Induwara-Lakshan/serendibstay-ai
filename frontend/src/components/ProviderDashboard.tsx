import { useEffect, useState } from "react";

type Provider = {
  id: number;
  provider_name: string;
  email: string;
  vehicle_type: string;
  vehicle_number: string;
  passenger_capacity: number;
  base_district: string;
  approved: boolean;
  available: boolean;
};

type TransportRequest = {
  id: number;
  provider_id: number;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  pickup_location: string;
  destination: string;
  pickup_date: string;
  pickup_time: string;
  passengers: number;
  status: string;
};

interface ProviderDashboardProps {
  onLogout?: () => void;
}

function ProviderDashboard({
  onLogout,
}: ProviderDashboardProps) {
  const [provider, setProvider] =
    useState<Provider | null>(null);

  const [requests, setRequests] =
    useState<TransportRequest[]>([]);

  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const loadDashboard = async () => {
      const token = sessionStorage.getItem(
        "provider_access_token"
      );

      if (!token) {
        setMessage("Please login again.");
        setLoading(false);
        return;
      }

      try {
        const [providerResponse, requestsResponse] =
          await Promise.all([
            fetch(
              "http://127.0.0.1:8001/transport/providers/me",
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            ),

            fetch(
              "http://127.0.0.1:8001/transport/providers/me/requests",
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            ),
          ]);

        if (
          !providerResponse.ok ||
          !requestsResponse.ok
        ) {
          if (
            providerResponse.status === 401 ||
            requestsResponse.status === 401
          ) {
            sessionStorage.removeItem(
              "provider_access_token"
            );

            setMessage(
              "Your login session has expired. Please login again."
            );

            return;
          }

          throw new Error(
            "Failed to load provider dashboard"
          );
        }

        const providerData: Provider =
          await providerResponse.json();

        const requestsData: TransportRequest[] =
          await requestsResponse.json();

        setProvider(providerData);
        setRequests(requestsData);
      } catch (error) {
        console.error(
          "Provider dashboard error:",
          error
        );

        setMessage(
          "Unable to load provider dashboard."
        );
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  // =========================================================
  // ACCEPT / REJECT TRANSPORT REQUEST
  // =========================================================

  const handleRequestAction = async (
    requestId: number,
    action: "accept" | "reject"
  ) => {
    const token = sessionStorage.getItem(
      "provider_access_token"
    );

    if (!token) {
      setMessage("Please login again.");
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8001/transport/providers/me/requests/${requestId}/${action}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          sessionStorage.removeItem(
            "provider_access_token"
          );

          setMessage(
            "Your login session has expired. Please login again."
          );

          return;
        }

        setMessage(
          data.detail ||
            "Unable to update transport request."
        );

        return;
      }

      setRequests((previousRequests) =>
        previousRequests.map((request) =>
          request.id === requestId
            ? {
                ...request,
                status: data.status,
              }
            : request
        )
      );

      setMessage(
        `Request #${requestId} ${data.status} successfully.`
      );
    } catch (error) {
      console.error(
        "Request action error:",
        error
      );

      setMessage(
        "Unable to update transport request."
      );
    }
  };

  // =========================================================
  // PROVIDER AVAILABILITY TOGGLE
  // =========================================================

  const handleAvailabilityToggle = async () => {
    if (!provider) {
      return;
    }

    const token = sessionStorage.getItem(
      "provider_access_token"
    );

    if (!token) {
      setMessage("Please login again.");
      return;
    }

    const newAvailability = !provider.available;

    try {
      const response = await fetch(
        `http://127.0.0.1:8001/transport/providers/me/availability?available=${newAvailability}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          sessionStorage.removeItem(
            "provider_access_token"
          );

          setMessage(
            "Your login session has expired. Please login again."
          );

          return;
        }

        setMessage(
          data.detail ||
            "Unable to update availability."
        );

        return;
      }

      setProvider((previousProvider) =>
        previousProvider
          ? {
              ...previousProvider,
              available: data.available,
            }
          : previousProvider
      );

      setMessage(
        data.available
          ? "You are now available for transport requests."
          : "You are now unavailable for transport requests."
      );
    } catch (error) {
      console.error(
        "Availability update error:",
        error
      );

      setMessage(
        "Unable to update availability."
      );
    }
  };

  // =========================================================
  // LOGOUT
  // =========================================================

  const handleLogout = () => {
    sessionStorage.removeItem(
      "provider_access_token"
    );

    if (onLogout) {
      onLogout();
    }
  };

  if (loading) {
    return (
      <div className="provider-dashboard-loading">
        <div className="provider-loading-logo">
          SL
        </div>

        <h3>Loading Provider Dashboard</h3>
        <p>Please wait...</p>
      </div>
    );
  }

  const pendingCount = requests.filter(
    (request) => request.status === "pending"
  ).length;

  const acceptedCount = requests.filter(
    (request) => request.status === "accepted"
  ).length;

  return (
    <div className="provider-dashboard">

      {/* Header */}
      <div className="provider-dashboard-header">
        <div className="provider-dashboard-title">
          <div className="provider-dashboard-logo">
            SL
          </div>

          <div>
            <span className="provider-dashboard-label">
              SERENDIBSTAY AI
            </span>

            <h2>Transport Provider Dashboard</h2>

            {provider && (
              <p>
                Welcome back,{" "}
                <strong>
                  {provider.provider_name}
                </strong>
              </p>
            )}
          </div>
        </div>

        <button
          className="provider-logout-button"
          type="button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>

      <div className="provider-dashboard-content">

        {message && (
          <div className="provider-dashboard-message">
            {message}
          </div>
        )}

        {/* Provider Summary */}
        {provider && (
          <>
            <div className="provider-summary-header">
              <div>
                <span className="provider-small-label">
                  PROVIDER PROFILE
                </span>

                <h3>{provider.provider_name}</h3>

                <p>
                  Manage your vehicle information
                  and customer transport requests.
                </p>
              </div>

              <div className="provider-status-group">

                {/* Approval Status */}
                <span
                  className={`dashboard-status-badge ${
                    provider.approved
                      ? "approved"
                      : "pending"
                  }`}
                >
                  {provider.approved
                    ? "Approved"
                    : "Pending"}
                </span>

                {/* Availability Status */}
                <span
                  className={`dashboard-status-badge ${
                    provider.available
                      ? "available"
                      : "unavailable"
                  }`}
                >
                  {provider.available
                    ? "Available"
                    : "Unavailable"}
                </span>

                {/* Availability Toggle */}
                <button
                  type="button"
                  className={`provider-availability-toggle ${
                    provider.available
                      ? "online"
                      : "offline"
                  }`}
                  onClick={handleAvailabilityToggle}
                >
                  {provider.available
                    ? "Set Unavailable"
                    : "Set Available"}
                </button>

              </div>
            </div>

            <div className="provider-info-grid">

              <div className="provider-info-card">
                <span>Vehicle Type</span>
                <strong>
                  {provider.vehicle_type}
                </strong>
              </div>

              <div className="provider-info-card">
                <span>Vehicle Number</span>
                <strong>
                  {provider.vehicle_number}
                </strong>
              </div>

              <div className="provider-info-card">
                <span>Passenger Capacity</span>
                <strong>
                  {provider.passenger_capacity}
                </strong>
              </div>

              <div className="provider-info-card">
                <span>Base District</span>
                <strong>
                  {provider.base_district}
                </strong>
              </div>

            </div>
          </>
        )}

        {/* Request Statistics */}
        <div className="provider-request-summary">

          <div className="request-summary-card">
            <span>Total Requests</span>
            <strong>{requests.length}</strong>
          </div>

          <div className="request-summary-card pending">
            <span>Pending</span>
            <strong>{pendingCount}</strong>
          </div>

          <div className="request-summary-card accepted">
            <span>Accepted</span>
            <strong>{acceptedCount}</strong>
          </div>

        </div>

        {/* Requests */}
        <div className="provider-requests">

          <div className="provider-requests-heading">
            <div>
              <span className="provider-small-label">
                CUSTOMER REQUESTS
              </span>

              <h3>Transport Requests</h3>

              <p>
                Review and manage transport
                requests assigned to you.
              </p>
            </div>

            <span className="provider-request-count">
              {requests.length}
            </span>
          </div>

          {requests.length === 0 ? (
            <div className="provider-empty-requests">
              <div className="empty-request-icon">
                SL
              </div>

              <h4>No transport requests yet</h4>

              <p>
                New customer requests will
                appear here.
              </p>
            </div>
          ) : (
            <div className="provider-request-list">

              {requests.map((request) => (
                <div
                  className="provider-request-card"
                  key={request.id}
                >
                  <div className="request-card-header">

                    <div>
                      <span className="request-number">
                        REQUEST #{request.id}
                      </span>

                      <h4>
                        {request.pickup_location}
                        <span className="route-arrow">
                          →
                        </span>
                        {request.destination}
                      </h4>
                    </div>

                    <span
                      className={`request-status-badge ${request.status.toLowerCase()}`}
                    >
                      {request.status}
                    </span>

                  </div>

                  <div className="request-detail-grid">

                    <div className="request-detail">
                      <span>Customer</span>
                      <strong>
                        {request.customer_name}
                      </strong>
                    </div>

                    <div className="request-detail">
                      <span>Date</span>
                      <strong>
                        {request.pickup_date}
                      </strong>
                    </div>

                    <div className="request-detail">
                      <span>Pickup Time</span>
                      <strong>
                        {request.pickup_time}
                      </strong>
                    </div>

                    <div className="request-detail">
                      <span>Passengers</span>
                      <strong>
                        {request.passengers}
                      </strong>
                    </div>

                  </div>

                  {request.status === "pending" && (
                    <div className="request-actions">

                      <button
                        className="request-accept-button"
                        type="button"
                        onClick={() =>
                          handleRequestAction(
                            request.id,
                            "accept"
                          )
                        }
                      >
                        Accept Request
                      </button>

                      <button
                        className="request-reject-button"
                        type="button"
                        onClick={() =>
                          handleRequestAction(
                            request.id,
                            "reject"
                          )
                        }
                      >
                        Reject
                      </button>

                    </div>
                  )}

                </div>
              ))}

            </div>
          )}

        </div>
      </div>
    </div>
  );
}

export default ProviderDashboard;