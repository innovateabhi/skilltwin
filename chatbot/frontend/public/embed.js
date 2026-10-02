(function () {
  const script = document.currentScript;

  const chatbotUrl =
    script?.getAttribute("data-chatbot-url") ||
    "/chatbot/";

  // Prevent duplicate chatbot instances
  if (window.__skillTwinChatbotCleanup) {
    window.__skillTwinChatbotCleanup();
  }

  // =========================================================
  // CHATBOT LAUNCHER
  // =========================================================

  const button = document.createElement("button");

  button.innerHTML = "💬";

  button.setAttribute(
    "aria-label",
    "Open SkillTwin Assistant"
  );

  Object.assign(button.style, {
    position: "fixed",
    right: "24px",
    bottom: "24px",
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    border: "1px solid rgba(124, 58, 237, 0.5)",
    background:
      "linear-gradient(135deg, #7c3aed, #4f46e5)",
    color: "#ffffff",
    fontSize: "22px",
    cursor: "pointer",
    zIndex: "999999",
    boxShadow:
      "0 10px 30px rgba(0, 0, 0, 0.30)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0",
    margin: "0",
    transition:
      "transform 0.2s ease, box-shadow 0.2s ease",
  });

  // =========================================================
  // CHATBOT IFRAME
  // =========================================================

  const iframe = document.createElement("iframe");

  iframe.src = `${chatbotUrl}?embed=1`;

  iframe.setAttribute(
    "title",
    "SkillTwin Assistant"
  );

  iframe.setAttribute(
    "allow",
    "clipboard-write"
  );

  Object.assign(iframe.style, {
    position: "fixed",
    right: "24px",
    bottom: "92px",
    width: "400px",
    height: "560px",
    maxWidth: "calc(100vw - 48px)",
    maxHeight: "calc(100vh - 116px)",
    boxSizing: "border-box",
    border: "none",
    background: "transparent",
    borderRadius: "18px",
    zIndex: "999998",
    display: "none",
    overflow: "hidden",
    boxShadow:
      "0 16px 45px rgba(0, 0, 0, 0.28)",
    margin: "0",
    padding: "0",
  });

  document.body.appendChild(iframe);
  document.body.appendChild(button);

  let open = false;

  // =========================================================
  // OPEN / CLOSE CHATBOT
  // =========================================================

  function toggleChatbot() {
    open = !open;

    iframe.style.display = open
      ? "block"
      : "none";

    button.innerHTML = open
      ? "×"
      : "💬";
  }

  button.addEventListener(
    "click",
    toggleChatbot
  );

  // =========================================================
  // CLOSE CHATBOT FROM INSIDE IFRAME
  // =========================================================

  function handleMessage(event) {
    if (
      event.data &&
      event.data.type ===
        "skilltwin-chatbot-close"
    ) {
      open = false;

      iframe.style.display = "none";

      button.innerHTML = "💬";
    }
  }

  window.addEventListener(
    "message",
    handleMessage
  );

  // =========================================================
  // RESPONSIVE SIZE
  // =========================================================

  function updateIframeSize() {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Desktop / Laptop
    if (viewportWidth > 600) {
      iframe.style.width =
        Math.min(
          400,
          viewportWidth - 48
        ) + "px";

      iframe.style.height =
        Math.min(
          560,
          viewportHeight - 116
        ) + "px";

      iframe.style.right = "24px";
      iframe.style.bottom = "92px";
      iframe.style.borderRadius = "18px";
    }

    // Mobile / Narrow screens
    else {
      iframe.style.width =
        viewportWidth - 24 + "px";

      iframe.style.height =
        viewportHeight - 94 + "px";

      iframe.style.right = "12px";
      iframe.style.bottom = "82px";
      iframe.style.borderRadius = "16px";
    }
  }

  updateIframeSize();

  window.addEventListener(
    "resize",
    updateIframeSize
  );

  // =========================================================
  // CLEANUP
  // =========================================================

  function cleanup() {
    button.removeEventListener(
      "click",
      toggleChatbot
    );

    window.removeEventListener(
      "message",
      handleMessage
    );

    window.removeEventListener(
      "resize",
      updateIframeSize
    );

    button.remove();

    iframe.remove();

    delete window.__skillTwinChatbotCleanup;
  }

  window.__skillTwinChatbotCleanup = cleanup;
})();
