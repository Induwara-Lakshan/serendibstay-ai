import { useState } from "react";

interface ProviderLoginProps {
  onLoginSuccess?: () => void;
  onBack?: () => void;
}

function ProviderLogin({
  onLoginSuccess,
  onBack,
}: ProviderLoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8001/transport/providers/login",
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
        setMessage(data.detail || "Login failed");
        return;
      }

      sessionStorage.setItem(
        "provider_access_token",
        data.access_token
      );

      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      console.error("Provider login error:", error);
      setMessage("Unable to connect to the server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="provider-login-page">
      <div className="provider-login-card">

        <div className="provider-login-brand">
          <div className="provider-login-logo">SL</div>

          <div>
            <span className="provider-login-label">
              SERENDIBSTAY AI
            </span>

            <h2>Transport Provider Login</h2>

            <p>
              Sign in to manage your transport requests.
            </p>
          </div>
        </div>

        <form
          className="provider-login-form"
          onSubmit={handleLogin}
        >
          <div className="provider-login-field">
            <label>Email Address</label>

            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              autoComplete="email"
              required
            />
          </div>

          <div className="provider-login-field">
            <label>Password</label>

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
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
            className="provider-login-button"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Signing in..."
              : "Login to Dashboard"}
          </button>
        </form>

        {onBack && (
          <button
            className="provider-login-back"
            type="button"
            onClick={onBack}
          >
            ← Back to SerendibStay Assistant
          </button>
        )}

        <div className="provider-login-footer">
          <span className="provider-login-security">
            ●
          </span>
          Secure provider access
        </div>

      </div>
    </div>
  );
}

export default ProviderLogin;