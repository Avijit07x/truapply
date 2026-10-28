const WAKE = "truapply:send";

window.addEventListener("message", (event) => {
  if (event.source === window && event.data === WAKE) {
    void chrome.runtime.sendMessage({ type: "wake" });
  }
});
