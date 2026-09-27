import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";

const isEmbedded =
  new URLSearchParams(window.location.search).get("embed") === "1";

export default function App() {
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    if (isEmbedded) {
      document.documentElement.classList.add("embed-mode");
    }

    return () => {
      document.documentElement.classList.remove("embed-mode");
    };
  }, []);

  const handleClose = () => {
    if (isEmbedded && window.parent !== window) {
      window.parent.postMessage(
        {
          type: "skilltwin-chatbot-close",
        },
        "*"
      );

      return;
    }

    setIsOpen(false);
  };

  const handleOpen = () => {
    setIsOpen(true);
  };

  return (
    <>
      {isOpen ? (
        <div className="shell">
          <ChatWindow onClose={handleClose} />
        </div>
      ) : (
        <button
          type="button"
          className="launcher"
          onClick={handleOpen}
          aria-label="Open SkillTwin Assistant"
        >
          🤖
        </button>
      )}
    </>
  );
}