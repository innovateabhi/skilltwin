import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, Sparkles, X } from "lucide-react";

const API_URL = import.meta.env.VITE_CHATBOT_API_URL || "/chatbot";

const suggestions = [
  "What is SkillTwin?",
  "What services do you provide?",
  "How does skill-gap analysis work?",
  "What solutions do you offer institutions?"
];

export default function ChatWindow({ onClose }) {
  const [messages, setMessages] = useState([{
    id: 1,
    role: "assistant",
    content: "Hello! I’m the SkillTwin Assistant. Ask me about SkillTwin, our services, solutions, portals, assessments, learning, analytics or pricing."
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(value = input) {
    const message = value.trim();
    if (!message || loading) return;

    setInput("");
    setMessages(current => [...current, { id: Date.now(), role: "user", content: message }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || "Chat request failed.");

      setMessages(current => [...current, {
        id: Date.now() + 1,
        role: "assistant",
        content: data.reply
      }]);
    } catch {
      setMessages(current => [...current, {
        id: Date.now() + 1,
        role: "assistant",
        content: "I’m unable to connect to the SkillTwin Assistant right now. Please try again in a moment."
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="chat-window">
      <header className="chat-header">
        <div className="brand-mark"><Bot size={19} /></div>
        <div className="header-copy">
          <div className="header-title">SkillTwin Assistant</div>
          <div className="header-status"><span className="status-dot" /> Knowledge Assistant</div>
        </div>
        <button className="icon-button" onClick={onClose}><X size={18} /></button>
      </header>

      <div className="chat-body">
        <div className="welcome-label"><Sparkles size={13} /> SKILLTWIN INTELLIGENCE</div>

        {messages.map(message => (
          <div key={message.id} className={`message-row ${message.role}`}>
            {message.role === "assistant" && <div className="message-avatar"><Bot size={15} /></div>}
            <div className="message-bubble">{message.content.split("\n").map((line, i) => (
              <span key={i}>{line}{i < message.content.split("\n").length - 1 && <br />}</span>
            ))}</div>
          </div>
        ))}

        {messages.length === 1 && (
          <div className="suggestions">
            {suggestions.map(item => (
              <button key={item} onClick={() => sendMessage(item)}>{item}</button>
            ))}
          </div>
        )}

        {loading && (
          <div className="message-row assistant">
            <div className="message-avatar"><Bot size={15} /></div>
            <div className="message-bubble typing"><span /><span /><span /></div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input-area" onSubmit={e => { e.preventDefault(); sendMessage(); }}>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about SkillTwin..." maxLength={2000} />
        <button type="submit" disabled={!input.trim() || loading}><ArrowUp size={18} /></button>
      </form>
    </section>
  );
}
