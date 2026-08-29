# Deployment Guide: Streamlit Community Cloud

## Overview
This dashboard is configured to deploy on Streamlit Community Cloud (free).
URL: `https://share.streamlit.io`

## Prerequisites
- GitHub account (private repo is fine)
- This repository pushed to GitHub
- Google OAuth credentials (already set up via google-workspace skill)

## Step 1: Push to GitHub (Private Repo)

```bash
cd C:\LAMARAN\Streamlit
git init
git add .
git commit -m "Initial commit: job application dashboard"
gh repo create job-dashboard --private --source=. --remote=origin --push
```

Or use the GitHub web UI to create a private repo and push manually.

## Step 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **"New app"**
4. Fill in:
   - **Repository**: your-username/job-dashboard
   - **Branch**: main
   - **Main file path**: app.py
   - **App URL**: pick a custom subdomain like `handra-jobs`
5. Click **"Deploy"**

## Step 3: Configure Secrets (Critical!)

After deployment, you MUST set secrets so the app can authenticate with Google.

1. In your Streamlit Cloud dashboard, click your app
2. Click the **⋮ menu** → **"Settings"** → **"Secrets"**
3. Paste this TOML config (replace values with your actual credentials):

```toml
# Your Google Sheets spreadsheet ID
SPREADSHEET_ID = "19xFihepbtHAWfrHfRct4mm8htBU5tuW-M6E-doXpJRs"

# Google OAuth token (copy from C:\Users\Handra\AppData\Local\hermes\google_token.json)
google_token = '''
{
  "token": "ya29.a0AfH6SMB...",
  "refresh_token": "1//0gX...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "416824275857-...",
  "client_secret": "GOCSPX-...",
  "scopes": ["https://www.googleapis.com/auth/spreadsheets.readonly"]
}
'''
```

4. Click **"Save"** — app will auto-redeploy

## Step 4: Access Your Dashboard

Your dashboard will be live at:
`https://handra-jobs.streamlit.app` (or whatever subdomain you chose)

## Updating Your App

To deploy changes:
```bash
cd C:\LAMARAN\Streamlit
# make changes
git add .
git commit -m "your message"
git push
```

Streamlit Cloud will auto-redeploy within ~1 minute.

## Security Notes

- ✅ Repository is **private** — code is not visible publicly
- ✅ Secrets are **encrypted** by Streamlit Cloud
- ⚠️ Dashboard URL is **publicly accessible** — anyone with the link can see your data
- 💡 To restrict access, share the URL only with trusted people (mentor, career coach)

## Troubleshooting

**"SPREADSHEET_ID not configured"**
- Check Streamlit Cloud secrets are set correctly
- Make sure the TOML syntax is valid

**"403 Forbidden" / "Insufficient Permission"**
- Token may have expired scopes
- Regenerate by re-running google-workspace setup, then update secrets

**App won't deploy**
- Check `requirements.txt` has all needed packages
- Check Streamlit Cloud logs (click "Manage app" → "Logs")
