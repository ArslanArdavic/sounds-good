# 🚀 Sounds Good - Quick Start Deployment Checklist

**Deploy in 2-3 hours using your GitHub Student Pack for FREE!**

---

## ⏱️ Phase 1: Setup (30 minutes)

### 1. Activate GitHub Student Pack Benefits
- [ ] Go to [education.github.com/pack](https://education.github.com/pack)
- [ ] Activate **DigitalOcean** ($200 credit)
- [ ] Activate **Namecheap** (free .me domain)
- [ ] Save credentials for both

### 2. Get API Keys
- [ ] **Spotify:** Create app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
  - Copy Client ID and Client Secret
  - Add temporary redirect: `http://localhost:8000/api/auth/callback`
- [ ] **Groq:** Sign up at [console.groq.com](https://console.groq.com)
  - Create API key
  - Copy key (starts with `gsk_`)

### 3. Generate Security Keys
```bash
# Run these commands and save the output:

# ENCRYPTION_KEY
python3 << 'EOF'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF

# JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## ⏱️ Phase 2: Backend Deployment (45 minutes)

### 4. Deploy to DigitalOcean
- [ ] Sign in to [cloud.digitalocean.com](https://cloud.digitalocean.com)
- [ ] Create → Apps → From GitHub
- [ ] Select `ArslanArdavic/sounds-good`
- [ ] Configure:
  - Source Directory: `/backend`
  - Run Command: `poetry run uvicorn src.main:app --host 0.0.0.0 --port 8080`

### 5. Add Databases
- [ ] Add PostgreSQL (Dev - $15/month)
- [ ] Add Redis (Dev - $15/month)

### 6. Add Environment Variables
```
DATABASE_URL=(auto-injected)
REDIS_URL=(auto-injected)
SPOTIFY_CLIENT_ID=<from Spotify>
SPOTIFY_CLIENT_SECRET=<from Spotify>
SPOTIFY_REDIRECT_URI=https://your-app.ondigitalocean.app/api/auth/callback
GROQ_API_KEY=<from Groq>
ENCRYPTION_KEY=<generated above>
JWT_SECRET=<generated above>
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000
```

### 7. Deploy & Get URL
- [ ] Click "Create Resources"
- [ ] Wait 5-10 minutes
- [ ] Copy your backend URL: `https://sounds-good-xxxxx.ondigitalocean.app`

---

## ⏱️ Phase 3: Frontend Deployment (30 minutes)

### 8. Deploy to Vercel
- [ ] Sign up at [vercel.com](https://vercel.com) with GitHub
- [ ] Import `ArslanArdavic/sounds-good`
- [ ] Configure:
  - Root Directory: `frontend`
  - Framework: Vite

### 9. Add Environment Variables
```
VITE_API_URL=https://sounds-good-xxxxx.ondigitalocean.app
VITE_SPOTIFY_CLIENT_ID=<from Spotify>
```

### 10. Deploy & Get URL
- [ ] Click "Deploy"
- [ ] Wait 2-3 minutes
- [ ] Copy your frontend URL: `https://sounds-good-xxxxx.vercel.app`

---

## ⏱️ Phase 4: Connect Everything (15 minutes)

### 11. Update Backend for Frontend
In DigitalOcean, update environment variable:
```
ALLOWED_ORIGINS=https://sounds-good-xxxxx.vercel.app
```

### 12. Update Spotify Redirect URIs
In [Spotify Dashboard](https://developer.spotify.com/dashboard):
- [ ] Add: `https://sounds-good-xxxxx.ondigitalocean.app/api/auth/callback`
- [ ] Add: `https://sounds-good-xxxxx.vercel.app/auth/callback`

---

## ⏱️ Phase 5: Test Everything (15 minutes)

### 13. Test Backend
```bash
curl https://sounds-good-xxxxx.ondigitalocean.app/health
```
Should return: `{"status":"healthy"}`

### 14. Test Full Flow
- [ ] Visit your Vercel URL
- [ ] Click "Connect with Spotify"
- [ ] Authorize app
- [ ] Test sync library
- [ ] Test generate playlist
- [ ] Test save to Spotify

---

## 🎉 Optional: Custom Domain (30 minutes)

### 15. Get Free Domain
- [ ] Go to [namecheap.com](https://namecheap.com)
- [ ] Search for `soundsgood.me`
- [ ] Apply GitHub Student Pack coupon
- [ ] Complete checkout ($0.00!)

### 16. Configure DNS
**Frontend (Vercel):**
- [ ] Vercel → Settings → Domains → Add `soundsgood.me`
- [ ] Add DNS records shown by Vercel to Namecheap

**Backend (DigitalOcean):**
- [ ] Add domain `api.soundsgood.me` in DigitalOcean
- [ ] Configure DNS in Namecheap

### 17. Update URLs Everywhere
- [ ] DigitalOcean: `ALLOWED_ORIGINS=https://soundsgood.me`
- [ ] Vercel: `VITE_API_URL=https://api.soundsgood.me`
- [ ] Spotify: Add `https://soundsgood.me/auth/callback`

---

## 📊 Monitoring Setup (15 minutes)

### 18. Set Up Uptime Monitoring
- [ ] Sign up at [uptimerobot.com](https://uptimerobot.com)
- [ ] Add monitor for `https://api.soundsgood.me/health`
- [ ] Add email alert

### 19. Enable DigitalOcean Alerts
- [ ] App → Settings → Alerts
- [ ] Enable high error rate alert
- [ ] Enable high CPU alert

---

## ✅ Final Checklist

- [ ] Backend deployed and healthy
- [ ] Frontend deployed and accessible
- [ ] Spotify OAuth working
- [ ] Can sync Spotify library
- [ ] Can generate playlists
- [ ] Can save to Spotify
- [ ] Monitoring enabled
- [ ] Custom domain configured (optional)

---

## 💰 Cost Tracking

**Current Status:**
- DigitalOcean Credit: $200
- Monthly Burn Rate: ~$35
- **Months of Free Hosting:** ~6 months

**Monitor credit:**
- [ ] DigitalOcean → Billing → Check remaining credit weekly

---

## 🆘 If Something Goes Wrong

### Backend won't deploy?
1. Check DigitalOcean Runtime Logs
2. Verify all environment variables are set
3. Check `pyproject.toml` has all dependencies

### Frontend can't connect?
1. Check browser console for CORS errors
2. Verify `VITE_API_URL` matches backend URL
3. Verify `ALLOWED_ORIGINS` includes frontend URL

### Spotify OAuth fails?
1. Check redirect URIs match exactly (no trailing slash!)
2. Verify Client ID and Secret are correct
3. Check DigitalOcean logs for OAuth errors

### Need help?
- Read: `GITHUB_STUDENT_DEPLOYMENT.md` (detailed guide)
- Check: DigitalOcean Community Forums
- Ask: In FastAPI Discord or Vercel Discussions

---

## 📱 Share Your App!

Once everything works:
- [ ] Share on Twitter/X
- [ ] Show to friends
- [ ] Add to your portfolio
- [ ] Update GitHub README with live URL

**Your app URL:** `https://soundsgood.me` (or Vercel URL)

---

## 🎓 Next Steps After Launch

**Week 1:**
- Monitor logs daily
- Fix any bugs
- Collect user feedback

**Month 1:**
- Add analytics (Vercel Analytics free tier)
- Monitor costs
- Optimize performance

**Before Credits Expire (~6 months):**
- Plan cost optimization
- Consider alternative hosting
- Apply for more student credits if available

---

**Congratulations! You're ready to deploy Sounds Good! 🚀**

**Estimated Total Time:** 2-3 hours
**Estimated Total Cost:** $0 for first 6 months!