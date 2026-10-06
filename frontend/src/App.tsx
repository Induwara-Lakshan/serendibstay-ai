import { useState } from "react";
import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import "./App.css";

import hotelBackground from "./assets/hotel-assistant-bg.png";

import ProviderRegistration from "./components/ProviderRegistration";
import AdminProviderApproval from "./components/AdminProviderApproval";
import ProviderLogin from "./components/ProviderLogin";
import ProviderDashboard from "./components/ProviderDashboard";
import AdminLogin from "./components/AdminLogin";

type Message = {
  role: "user" | "assistant";
  text: string;
};

function App() {
  const [currentView, setCurrentView] = useState<
    | "chat"
    | "provider"
    | "providerLogin"
    | "providerDashboard"
    | "adminLogin"
    | "admin"
  >("chat");

  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hello! I'm your SerendibStay AI Assistant. I can help you search hotels, make bookings, find transport, and request transport services.",
    },
  ]);

  const [loading, setLoading] = useState(false);

  // =========================================================
  // CLEAR CHAT
  // =========================================================

  const clearChat = () => {
    setMessages([
      {
        role: "assistant",
        text: "Hello! I'm your SerendibStay AI Assistant. I can help you search hotels, make bookings, find transport, and request transport services.",
      },
    ]);
  };

  // =========================================================
  // QUICK ACTION
  // =========================================================

  const handleQuickAction = (text: string) => {
    setMessage(text);
  };

  // =========================================================
  // SEND CHAT MESSAGE
  // =========================================================

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();

    const userMessage = message.trim();

    if (!userMessage || loading) {
      return;
    }

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        text: userMessage,
      },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8001/chat/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userMessage,
            history: messages.map((msg) => ({
              role: msg.role,
              content: msg.text,
            })),
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Chat request failed");
      }

      const data: { reply: string } =
        await response.json();

      console.log("CHAT RESPONSE:", data);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: data.reply,
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: "Sorry, I could not connect to the hotel assistant.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // PROVIDER LOGIN VIEW
  // =========================================================

  if (currentView === "providerLogin") {
    return (
      <div
        className="app"
        style={{
          backgroundImage: `linear-gradient(
            rgba(4, 47, 46, 0.25),
            rgba(4, 47, 46, 0.25)
          ), url(${hotelBackground})`,
        }}
      >
        <div className="chat-container">
          <ProviderLogin
            onBack={() => setCurrentView("chat")}
            onLoginSuccess={() => {
              setCurrentView("providerDashboard");
            }}
          />
        </div>
      </div>
    );
  }

  // =========================================================
  // PROVIDER DASHBOARD VIEW
  // =========================================================

  if (currentView === "providerDashboard") {
    return (
      <div
        className="app"
        style={{
          backgroundImage: `linear-gradient(
            rgba(4, 47, 46, 0.25),
            rgba(4, 47, 46, 0.25)
          ), url(${hotelBackground})`,
        }}
      >
        <div className="chat-container">
          <ProviderDashboard
            onLogout={() => {
              setCurrentView("providerLogin");
            }}
          />
        </div>
      </div>
    );
  }

  // =========================================================
  // PROVIDER REGISTRATION VIEW
  // =========================================================

  if (currentView === "provider") {
    return (
      <div
        className="app"
        style={{
          backgroundImage: `linear-gradient(
            rgba(4, 47, 46, 0.25),
            rgba(4, 47, 46, 0.25)
          ), url(${hotelBackground})`,
        }}
      >
        <div className="chat-container">
          <button
            type="button"
            className="clear-button"
            onClick={() => setCurrentView("chat")}
          >
            ← Back to Assistant
          </button>

          <ProviderRegistration />
        </div>
      </div>
    );
  }

  // =========================================================
  // ADMIN LOGIN VIEW
  // =========================================================

  if (currentView === "adminLogin") {
    return (
      <div
        className="app"
        style={{
          backgroundImage: `linear-gradient(
            rgba(4, 47, 46, 0.25),
            rgba(4, 47, 46, 0.25)
          ), url(${hotelBackground})`,
        }}
      >
        <div className="chat-container">
          <AdminLogin
            onBack={() => setCurrentView("chat")}
            onLoginSuccess={() => {
              setCurrentView("admin");
            }}
          />
        </div>
      </div>
    );
  }

  // =========================================================
  // ADMIN PROVIDER MANAGEMENT VIEW
  // =========================================================

  if (currentView === "admin") {
    return (
      <div
        className="app"
        style={{
          backgroundImage: `linear-gradient(
            rgba(4, 47, 46, 0.25),
            rgba(4, 47, 46, 0.25)
          ), url(${hotelBackground})`,
        }}
      >
        <div className="chat-container">
          <button
            type="button"
            className="clear-button"
            onClick={() => {
              sessionStorage.removeItem(
                "admin_access_token"
              );

              setCurrentView("adminLogin");
            }}
          >
            Logout Admin
          </button>

          <AdminProviderApproval />
        </div>
      </div>
    );
  }

  // =========================================================
  // MAIN CHAT VIEW
  // =========================================================

  return (
    <div
      className="app"
      style={{
        backgroundImage: `linear-gradient(
          rgba(4, 47, 46, 0.25),
          rgba(4, 47, 46, 0.25)
        ), url(${hotelBackground})`,
      }}
    >
      <div className="chat-container">

        {/* Header */}
        <header className="chat-header">
          <div className="brand">
            <div className="logo">
              SL
            </div>

            <div>
              <h1>SerendibStay AI</h1>

              <p>
                AI powered hotel & transport assistant
                for Sri Lanka
              </p>
            </div>
          </div>

          <button
            className="clear-button"
            type="button"
            onClick={clearChat}
          >
            Clear Chat
          </button>
        </header>

        {/* Quick Actions */}
        <div className="quick-actions">

          <button
            type="button"
            onClick={() =>
              handleQuickAction(
                "Help me search for hotels in Sri Lanka."
              )
            }
          >
            Search Hotels
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickAction(
                "I want to make a hotel booking. What information do you need?"
              )
            }
          >
            Make a Booking
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickAction(
                "Help me find a transport provider in Sri Lanka."
              )
            }
          >
            Find Transport
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickAction(
                "I want to request transport. What information do you need?"
              )
            }
          >
            Request Transport
          </button>

          <button
            type="button"
            onClick={() =>
              setCurrentView("provider")
            }
          >
            Register as Transport Provider
          </button>

          <button
            type="button"
            onClick={() =>
              setCurrentView("providerLogin")
            }
          >
            Transport Provider Login
          </button>

          <button
            type="button"
            onClick={() =>
              setCurrentView("adminLogin")
            }
          >
            Admin Login
          </button>

        </div>

        {/* Messages */}
        <main className="messages">
          {messages.map((item, index) => (
            <div
              key={index}
              className={`message-row ${
                item.role === "user"
                  ? "user-row"
                  : "assistant-row"
              }`}
            >
              <div
                className={`message ${item.role}`}
              >
                {item.role === "assistant" ? (
  <div className="ai-response-content">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {item.text}
    </ReactMarkdown>
  </div>
) : (
  item.text
)}
              </div>
            </div>
          ))}

          {/* Typing animation */}
          {loading && (
            <div className="message-row assistant-row">
              <div className="message assistant typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </main>

        {/* Input */}
        <form
          className="chat-form"
          onSubmit={sendMessage}
        >
          <input
            type="text"
            value={message}
            onChange={(event) =>
              setMessage(event.target.value)
            }
            placeholder="Ask about hotels or transport in Sri Lanka..."
            disabled={loading}
          />

          <button
            type="submit"
            disabled={
              loading || !message.trim()
            }
          >
            Send
          </button>
        </form>

      </div>
    </div>
  );
}

export default App;