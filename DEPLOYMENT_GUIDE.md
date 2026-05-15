# 🚀 Deployment Guide: Render + Vercel

This guide will help you deploy your Ethara Project Management app with **Backend on Render** and **Frontend on Vercel**.

## 📋 Prerequisites

- GitHub account with repository: `Shreysharma1602/Project-Manager`
- Render account (free tier available)
- Vercel account (free tier available)

---

## 🎯 Step 1: Deploy Backend on Render

### 1.1 Connect GitHub to Render
1. Go to [render.com](https://render.com)
2. Sign up/login with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository: `Shreysharma1602/Project-Manager`

### 1.2 Configure Backend Service
**Basic Settings:**
- **Name**: `ethara-backend`
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Advanced Settings:**
- **Health Check Path**: `/api/health`

### 1.3 Add PostgreSQL Database
1. In your Render dashboard, click "New" → "PostgreSQL"
2. **Name**: `ethara-db`
3. **Database Name**: `ethara`
4. **User**: `ethara_user`
5. **Plan**: Free

### 1.4 Environment Variables
Set these environment variables for your backend service:

```bash
DATABASE_URL=postgresql://username:password@host:port/database_name
SECRET_KEY=your-long-random-secret-key-here
FRONTEND_URL=https://your-frontend-domain.vercel.app
ENV=production
DEBUG=false
```

**Get Database URL:**
1. Go to your PostgreSQL service on Render
2. Click "Connect" → "External Connection"
3. Copy the connection string and use it for `DATABASE_URL`

### 1.5 Run Database Migrations
After deployment, you'll need to run migrations:
1. Go to your backend service on Render
2. Click "Shell" tab
3. Run: `alembic upgrade head`

---

## 🎯 Step 2: Deploy Frontend on Vercel

### 2.1 Connect GitHub to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Sign up/login with GitHub
3. Click "Add New" → "Project"
4. Import repository: `Shreysharma1602/Project-Manager`

### 2.2 Configure Frontend Project
**Project Settings:**
- **Name**: `ethara-frontend`
- **Root Directory**: `frontend`
- **Framework Preset**: `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

### 2.3 Environment Variables
Add this environment variable for your frontend:

```bash
VITE_API_URL=https://your-backend-domain.onrender.com/api
```

**Get Backend URL:**
1. Go to your backend service on Render
2. Copy the URL (e.g., `https://ethara-backend.onrender.com`)
3. Add `/api` at the end

### 2.4 Deploy
Click "Deploy" and wait for the build to complete.

---

## 🎯 Step 3: Update CORS Settings

### 3.1 Backend CORS Configuration
Make sure your backend allows requests from your Vercel domain:

In `backend/app/main.py` (or your CORS configuration):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://your-frontend-domain.vercel.app"  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🎯 Step 4: Test Your Deployment

### 4.1 Backend Health Check
Visit: `https://your-backend-domain.onrender.com/api/health`
Should return: `{"status": "healthy"}`

### 4.2 Frontend Access
Visit: `https://your-frontend-domain.vercel.app`
Should load the modern login page.

### 4.3 Test Authentication
1. Create a new account on the deployed frontend
2. Try logging in
3. Verify dashboard loads with project data

---

## 🔧 Troubleshooting

### Common Issues:

**1. CORS Errors**
- Ensure `FRONTEND_URL` environment variable is set correctly on Render
- Check that your Vercel domain is added to CORS origins

**2. Database Connection Issues**
- Verify `DATABASE_URL` is correctly set on Render
- Check that PostgreSQL service is running
- Run migrations if needed

**3. Build Failures**
- Check build logs on both platforms
- Ensure all dependencies are in `requirements.txt` and `package.json`

**4. 404 Errors**
- Verify API endpoints are correct
- Check that backend is running and accessible

---

## 📁 Important Files Created

- `backend/render.yaml` - Render configuration
- `frontend/vercel.json` - Vercel configuration
- `DEPLOYMENT_GUIDE.md` - This guide

---

## 🎉 Success Checklist

- [ ] Backend deployed on Render with PostgreSQL
- [ ] Frontend deployed on Vercel
- [ ] Environment variables configured
- [ ] CORS settings updated
- [ ] Database migrations run
- [ ] Authentication flow working
- [ ] Dashboard loads correctly
- [ ] Project creation and task management working

---

## 🔄 Continuous Deployment

Both platforms support automatic deployments:
- **Render**: Auto-deploys on push to main branch
- **Vercel**: Auto-deploys on push to main branch

Your app will automatically update when you push changes to GitHub!

---

## 📞 Support

If you encounter issues:
1. Check the logs on Render and Vercel dashboards
2. Verify environment variables
3. Ensure all URLs are correct
4. Test locally first, then deploy

Good luck with your deployment! 🚀
