const WAKE = "truapply:send";
const HELLO = "truapply:hello";
const HERE = "truapply:here";

window.addEventListener("message", (event) => {
  if (event.source !== window) return;
  if (event.data === WAKE) {
    void chrome.runtime.sendMessage({ type: "wake" });
  } else if (event.data === HELLO) {
    window.postMessage(HERE, window.location.origin);
  }
});
