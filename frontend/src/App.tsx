import { useState } from "react";
import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";
import hotelBackground from "./assets/hotel-assistant-bg.png";

type Message = {
  role: "user" | "assistant";
  text: string;
};

function App() {
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hello! I'm your Sri Lanka Hotel Assistant. Ask me about hotels, cities, districts, or bookings.",
    },
  ]);

  const [loading, setLoading] = useState(false);

  const clearChat = () => {
    setMessages([
      {
        role: "assistant",
        text: "Hello! I'm your Sri Lanka Hotel Assistant. Ask me about hotels, cities, districts, or bookings.",
      },
    ]);
  };

  const handleQuickAction = (text: string) => {
    setMessage(text);
  };

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
      const response = await fetch("http://127.0.0.1:8001/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error("Chat request failed");
      }

      const data: { reply: string } = await response.json();

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
            <div className="logo">SL</div>

            <div>
              <h1>Sri Lanka Hotel Assistant</h1>
              <p>AI powered hotel search & booking assistant</p>
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
              <div className={`message ${item.role}`}>
                {item.role === "assistant" ? (
                  <ReactMarkdown>
                    {item.text}
                  </ReactMarkdown>
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
            placeholder="Ask about hotels in Sri Lanka..."
            disabled={loading}
          />

          <button
            type="submit"
            disabled={loading || !message.trim()}
          >
            Send
          </button>
        </form>

      </div>
    </div>
  );
}

export default App;