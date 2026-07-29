import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hey! 👋 Ich bin dein persönlicher Style-Assistent. Ich kenne deine Garderobe und kann dir bei Outfit-Ideen, Styling-Tipps oder Fashion-Fragen helfen. Du kannst mir auch Bilder zeigen!",
    },
  ]);
  const [input, setInput] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function handleImageSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setImage(file);
    setImagePreview(URL.createObjectURL(file));
    e.target.value = ""; // Reset input
  }

  function removeImage() {
    setImage(null);
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
      setImagePreview(null);
    }
  }

  async function sendMessage() {
    if (!input.trim() && !image) return;
    
    const userMessage = input.trim();
    const userImage = image;
    const userImagePreview = imagePreview;
    
    // Add user message to chat
    const newUserMsg = {
      role: "user",
      content: userMessage || "(Bild gesendet)",
      image: userImagePreview,
    };
    setMessages((prev) => [...prev, newUserMsg]);
    
    // Clear input
    setInput("");
    removeImage();
    setError("");
    setLoading(true);
    
    try {
      // Prepare history (without images for API)
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));
      
      const result = await api.chat(userMessage || "Was sagst du zu diesem Bild?", history, userImage);
      
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.response,
        },
      ]);
    } catch (err) {
      setError(err.message || "Nachricht konnte nicht gesendet werden.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyPress(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink-900">💬 Style-Chat</h2>
        <p className="text-sm text-ink-700/60">
          Chatte mit deinem persönlichen Style-Assistenten
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
        <AnimatePresence initial={false}>
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-clay-500 text-white"
                    : "bg-sand-100 text-ink-900"
                }`}
              >
                {msg.image && (
                  <img
                    src={msg.image}
                    alt="Hochgeladenes Bild"
                    className="w-full rounded-xl mb-2 max-h-64 object-cover"
                  />
                )}
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="bg-sand-100 text-ink-900 rounded-2xl px-4 py-3 flex items-center gap-2">
              <motion.span
                className="inline-block w-2 h-2 bg-clay-500 rounded-full"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1.5, delay: 0 }}
              />
              <motion.span
                className="inline-block w-2 h-2 bg-clay-500 rounded-full"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }}
              />
              <motion.span
                className="inline-block w-2 h-2 bg-clay-500 rounded-full"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }}
              />
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 rounded-xl bg-clay-500/10 text-clay-600 text-sm px-3 py-2"
        >
          {error}
        </motion.div>
      )}

      {/* Image Preview */}
      {imagePreview && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-3 relative inline-block"
        >
          <img
            src={imagePreview}
            alt="Vorschau"
            className="h-20 rounded-xl object-cover border-2 border-sand-200"
          />
          <button
            onClick={removeImage}
            className="absolute -top-2 -right-2 w-6 h-6 bg-clay-500 text-white rounded-full flex items-center justify-center text-sm hover:bg-clay-600 transition"
          >
            ×
          </button>
        </motion.div>
      )}

      {/* Input Area */}
      <div className="flex items-end gap-2">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex-shrink-0 w-10 h-10 rounded-xl bg-sand-100 text-ink-700 flex items-center justify-center hover:bg-sand-200 transition"
          aria-label="Bild hinzufügen"
        >
          📷
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleImageSelect}
        />
        
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Schreib eine Nachricht..."
            rows={1}
            className="w-full rounded-xl border border-sand-200 bg-white px-4 py-2.5 text-ink-900 text-sm placeholder:text-ink-700/30 focus:border-clay-500 focus:ring-2 focus:ring-clay-500/20 outline-none transition resize-none"
            style={{ minHeight: "40px", maxHeight: "120px" }}
            onInput={(e) => {
              e.target.style.height = "40px";
              e.target.style.height = e.target.scrollHeight + "px";
            }}
          />
        </div>

        <button
          onClick={sendMessage}
          disabled={loading || (!input.trim() && !image)}
          className="flex-shrink-0 w-10 h-10 rounded-xl bg-clay-500 text-white flex items-center justify-center hover:bg-clay-600 active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Senden"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
