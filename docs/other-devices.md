# Use the tracker from your phone

The tracker runs on your computer and answers only there (`127.0.0.1`). It has no login, so it never listens on your Wi-Fi or the internet. To open it from your phone or another computer, use [Tailscale](https://tailscale.com): a free app that links your own devices into a private network. Only devices signed in to your Tailscale account can reach it, from any network (home Wi-Fi, mobile data, office), and nothing is opened to the internet.

It works the same on macOS, Windows and Linux, and from iPhone, Android or any other computer.

## Set it up once

1. Install Tailscale on the computer that runs TruApply and on your phone, and sign in to the same account on both.
2. On the computer, share the tracker with your devices (HTTPS on your private Tailscale address):

   | System | Command |
   |---|---|
   | macOS | `tailscale serve --bg 8765` (with the Mac app, turn on **Settings → Install CLI** first, or use `/Applications/Tailscale.app/Contents/MacOS/Tailscale serve --bg 8765`) |
   | Windows | `tailscale serve --bg 8765` in PowerShell |
   | Linux | `sudo tailscale serve --bg 8765` |

   The first time, Tailscale may ask you to turn on HTTPS for your account; follow the link it prints. Use the port the tracker runs on if it isn't 8765.
3. Start the tracker as usual. It finds your Tailscale address by itself and prints it:

   ```
   Tracker running at http://127.0.0.1:8765  (Ctrl+C to stop)
     On your other devices: https://laptop.tail1234.ts.net
   ```

4. Open that address on your phone.

To stop sharing: `tailscale serve --https=443 off`.

## What works from your phone

Everything on the tracker page: jobs, scoring, runs, settings, companies and what it learned. Two things still happen on the computer:

- **Open it filled in** opens the filled-in browser on the computer, not on your phone.
- The Chrome extension only runs in desktop Chrome.

The computer has to be on and awake.

## How it stays private

- The tracker still listens only on `127.0.0.1`. Tailscale's own app passes requests from your devices to it.
- The tracker answers only the addresses it knows: `127.0.0.1`, `localhost` and your Tailscale address. Changes (any `POST`) must come from one of those pages too, so another website can't act through your browser.
- Another address can be allowed by hand with `truapply tracker --allow-host NAME`, for example on a second Tailscale network. Only use names that point to your own devices.
- Don't put the tracker on the open internet with a public tunnel: it has no login.
