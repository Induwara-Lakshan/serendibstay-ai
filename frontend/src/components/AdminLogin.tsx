import { useState } from "react";

type AdminLoginProps = {
  onLoginSuccess: () => void;
  onBack: () => void;
};

function AdminLogin({
  onLoginSuccess,
  onBack,
}: AdminLoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    try {
      setLoading(true);
      setMessage("");

      const response = await fetch(
        "http://127.0.0.1:8001/transport/admin/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(
          data.detail || "Invalid admin email or password."
        );
        return;
      }

      sessionStorage.setItem(
        "admin_access_token",
        data.access_token
      );

      onLoginSuccess();
    } catch (error) {
      console.error("Admin login error:", error);
      setMessage("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="provider-login-page">
      <div className="provider-login-card">

        <div className="provider-login-brand">
          <div className="provider-login-logo">
            SL
          </div>

          <span className="provider-login-label">
            SerendibStay AI
          </span>
        </div>

        <div>
          <h2>Admin Login</h2>

          <p>
            Sign in to manage transport provider approvals.
          </p>
        </div>

        <form
          className="provider-login-form"
          onSubmit={handleLogin}
        >
          <div className="provider-login-field">
            <label htmlFor="admin-email">
              Admin Email
            </label>

            <input
              id="admin-email"
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              placeholder="Enter admin email"
              autoComplete="username"
              required
            />
          </div>

          <div className="provider-login-field">
            <label htmlFor="admin-password">
              Password
            </label>

            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="Enter admin password"
              autoComplete="current-password"
              required
            />
          </div>

          {message && (
            <div className="provider-login-message">
              {message}
            </div>
          )}

          <button
            type="submit"
            className="provider-login-button"
            disabled={loading}
          >
            {loading
              ? "Signing in..."
              : "Login to Admin Panel"}
          </button>
        </form>

        <button
          type="button"
          className="provider-login-back"
          onClick={onBack}
        >
          Back to Chat
        </button>

        <div className="provider-login-footer">
          <span className="provider-login-security">
            Secure administrator access
          </span>
        </div>
      </div>
    </div>
  );
}

export default AdminLogin;