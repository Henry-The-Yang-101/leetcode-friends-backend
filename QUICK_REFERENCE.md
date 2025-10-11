# Quick Reference - Your Gunicorn Setup

## Your Current Commands

### Start Gunicorn (Manual)
```bash
cd ~/leetcode-friends-backend
source venv/bin/activate
nohup gunicorn -w 4 -b 127.0.0.1:5000 leetcode_friends_backend:app &
```

### Check Running Processes
```bash
ps aux | grep gunicorn
```

### Stop Gunicorn (Manual)
```bash
pkill -TERM -f "gunicorn.*leetcode_friends_backend:app"
# Or force kill:
pkill -9 -f "gunicorn.*leetcode_friends_backend:app"
```

---

## New Helper Scripts (Same Commands, Easier!)

### Start
```bash
./backend/start_gunicorn.sh
```
This runs: `nohup gunicorn -w 4 -b 127.0.0.1:5000 leetcode_friends_backend:app &`

### Stop
```bash
./backend/stop_gunicorn.sh
```
Gracefully stops Gunicorn (waits 30s, then force kills)

### Auto-Deploy
```bash
./backend/auto_deploy.sh
```
Checks git, pulls updates, restarts if needed

---

## Setup Auto-Deployment Cron Job

### 1. SSH into EC2
```bash
ssh -i /path/to/your-key.pem ec2-user@3.149.1.223
```

### 2. Edit crontab
```bash
crontab -e
```

### 3. Add this line (runs every hour)
```bash
0 * * * * /home/ec2-user/leetcodefriends/backend/auto_deploy.sh >> /tmp/auto_deploy.log 2>&1
```

### 4. Verify it's saved
```bash
crontab -l
```

---

### Check if Gunicorn is running
```bash
ps aux | grep gunicorn
```

---

## What the Auto-Deploy Does

**Every hour**, the cron job:
1. ✅ Fetches latest changes from git
2. ✅ If updates exist:
   - Pulls the changes
   - Updates dependencies
   - Gracefully stops Gunicorn (finishes current requests)
   - Restarts with: `nohup gunicorn -w 4 -b 127.0.0.1:5000 leetcode_friends_backend:app &`
3. ✅ If no updates: Does nothing

---

## Important Notes

- **Port**: 127.0.0.1:5000 (localhost only)
- **Workers**: 4
- **Logs**: /tmp/gunicorn.log
- **Graceful shutdown**: 30 second timeout before force kill

