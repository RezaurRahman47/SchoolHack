# Host School Hack for free on Render

This puts the School Hack web app (`backend-python/`) online with a public link,
for example `https://schoolhack.onrender.com`, on Render's free plan. It takes
about 10 minutes. You need a GitHub account; no credit card.

**Fastest way:** click
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/RezaurRahman47/SchoolHack/tree/safick_v1),
sign in with GitHub, paste the OpenRouter key when asked and click **Deploy**.
Render reads everything else from `render.yaml`. The steps below are the manual way.

What runs online: everything in the app (tests, subtopic quizzes, learning
profile, teacher dashboard, gap finder, German and English). The AI tutor's free
answers need an OpenRouter key (step 4). The textbook search server
(`vectorstore/`) is not deployed; no page needs it.

## 1. Create a Render account

Go to <https://render.com>, click **Get Started**, and sign in with **GitHub**.

## 2. Create the web service

1. In the dashboard click **+ New → Web Service**.
2. Choose the tab **Public Git Repository** and paste
   `https://github.com/RezaurRahman47/SchoolHack`, then **Connect**.
3. Fill in the form:

| Field | Value |
|---|---|
| Name | `schoolhack` (becomes part of the link; pick another if it is taken) |
| Branch | `safick_v1` |
| Root Directory | `backend-python` |
| Runtime / Language | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** |

## 3. Add the environment variables

Under **Environment Variables** add:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `SESSION_SECRET` | click **Generate** |
| `OPENROUTER_API_KEY` | your key from <https://openrouter.ai/keys> (step 4) |

## 4. The OpenRouter key (for the AI tutor)

Paste it only into Render, never into the code or a chat. Everyone with the link
uses your credit, so set a small monthly limit for the key on OpenRouter. Without
a key the site still works; only free AI tutor answers show "not set up".

## 5. Deploy

Click **Deploy Web Service**. The first build takes 2–4 minutes. When the log says
`Your service is live`, open the link at the top of the page and sign in with
`admin` / `admin`.

## Good to know

- **Sleeping:** on the free plan the app sleeps after 15 minutes without visits.
  The next visit wakes it up in about a minute. Open the link yourself a few
  minutes before you present.
- **Demo data resets** after every deploy or restart (the free plan has no
  permanent disk). The demo class is created again automatically.
- **Updating:** after pushing to `safick_v1`, click **Manual Deploy → Deploy latest
  commit** in Render. (A service made from a public repository URL does not
  redeploy on its own.)
- **One-click alternative:** if the repository owner connects it to Render, use
  **+ New → Blueprint**; `render.yaml` in the repository fills in everything above.
