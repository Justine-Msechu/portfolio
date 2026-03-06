# 🚀 Portfolio — Flask + Neon + Vercel

A beautiful, database-powered developer portfolio built with Python Flask, PostgreSQL (Neon), and deployed for **free** on Vercel.

---

## Stack (All Free Tier)

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| **Vercel** | Hosting + Serverless | Unlimited personal projects |
| **Neon** | PostgreSQL database | 0.5 GB storage, 1 project |
| **Flask** | Python web framework | Open source |

---

## Project Structure

```
portfolio/
├── api/
│   └── index.py        ← Flask app (Vercel entry point)
├── templates/
│   └── index.html      ← Portfolio frontend
├── vercel.json         ← Vercel deployment config
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment variable template
└── .gitignore
```

---

## 🛠️ Deployment Guide (Step by Step)

### Step 1 — Get a Free Neon Database

1. Go to **https://neon.tech** and sign up (free, no credit card)
2. Click **"New Project"** → give it a name like `portfolio`
3. Choose a region close to you (e.g., `AWS / EU West` or `AWS / US East`)
4. Click **Create Project**
5. Copy the **Connection String** — it looks like:
   ```
   postgresql://alex:password@ep-cool-darkness.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   This is your `DATABASE_URL`. **Keep it secret!**

---

### Step 2 — Push Code to GitHub

1. Create a new repo on **https://github.com** (name it `portfolio`)
2. In your terminal:
   ```bash
   cd portfolio
   git init
   git add .
   git commit -m "Initial portfolio"
   git remote add origin https://github.com/YOUR_USERNAME/portfolio.git
   git push -u origin main
   ```

---

### Step 3 — Deploy to Vercel

1. Go to **https://vercel.com** and sign up with your GitHub account (free)
2. Click **"Add New Project"**
3. Import your `portfolio` GitHub repository
4. Before deploying, add your environment variable:
   - Click **"Environment Variables"**
   - Name: `DATABASE_URL`
   - Value: *(paste your Neon connection string)*
5. Click **Deploy** 🎉

Vercel will automatically build and deploy your app. You'll get a URL like:
`https://portfolio-yourname.vercel.app`

---

### Step 4 — Test Locally (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env and add your DATABASE_URL

# Run locally
cd api
python index.py
# Visit http://localhost:5000
```

---

## ✏️ Customizing Your Portfolio

### Edit Your Profile
1. Visit your deployed site
2. Click the **⚙ Admin** button (bottom right)
3. Fill in your Name, Title, Bio, Email, GitHub, LinkedIn, Location
4. Click **Save Profile** — page will reload with your info

### Add Projects
1. Open the Admin panel
2. Fill in the **Add New Project** form
3. Add tech stack as comma-separated values: `Flutter, Flask, PostgreSQL`
4. Check **Featured** for projects to show first
5. Click **Add Project**

### Customize Design
Edit `templates/index.html` — the CSS variables at the top control the whole theme:
```css
:root {
  --gold:    #c9a84c;   /* accent color */
  --bg:      #090909;   /* background */
  --text:    #e8e2d8;   /* text color */
}
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Portfolio homepage |
| GET | `/api/health` | Health check |
| GET | `/api/projects` | List all projects (JSON) |
| POST | `/api/projects` | Create a project |
| PUT | `/api/projects/:id` | Update a project |
| DELETE | `/api/projects/:id` | Delete a project |
| GET | `/api/profile` | Get profile (JSON) |
| PUT | `/api/profile` | Update profile |

---

## 🔄 Auto-Redeployment

Every time you push to GitHub, Vercel will **automatically redeploy** your site. No manual steps needed.

---

## 📈 Future Upgrades (Still Free)

- Add **contact form** with [Resend](https://resend.com) (free email API)
- Add **blog** with markdown files
- Add **authentication** with [Clerk](https://clerk.com) (free tier)
- Add **analytics** with [Vercel Analytics](https://vercel.com/analytics) (free)
