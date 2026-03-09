# Deployment Guide: Apache + Node.js

## Quick Start

### Option 1: Apache Reverse Proxy (Easiest)

1. **Start Node.js service:**
   ```bash
   cd hb-service
   npm install
   npm install -g pm2
   pm2 start hb-api-server.js --name hb-service
   pm2 save
   pm2 startup
   ```

2. **Configure Apache:**
   ```bash
   # Enable required modules
   sudo a2enmod proxy
   sudo a2enmod proxy_http
   sudo a2enmod rewrite
   
   # Copy config
   sudo cp apache-config.conf /etc/apache2/sites-available/hb-service.conf
   
   # Edit the file and update ServerName
   sudo nano /etc/apache2/sites-available/hb-service.conf
   
   # Enable site
   sudo a2ensite hb-service
   sudo systemctl restart apache2
   ```

3. **Access:**
   - http://your-domain.com → Apache → Node.js (port 8000)

---

### Option 2: Apache for Static + Node.js for API

1. **Copy static files to Apache directory:**
   ```bash
   sudo cp -r static/* /var/www/html/hb-service/
   ```

2. **Start Node.js for API only:**
   ```bash
   pm2 start hb-api-server.js
   ```

3. **Configure Apache:**
   ```bash
   sudo cp apache-hybrid-config.conf /etc/apache2/sites-available/hb-hybrid.conf
   sudo a2ensite hb-hybrid
   sudo systemctl restart apache2
   ```

---

### Option 3: Standalone Node.js (Development)

```bash
cd hb-service
npm install
node hb-api-server.js
```

Access at http://localhost:8000

---

## PM2 Commands

```bash
# Start
pm2 start hb-api-server.js --name hb-service

# Stop
pm2 stop hb-service

# Restart
pm2 restart hb-service

# View logs
pm2 logs hb-service

# Monitor
pm2 monit

# List processes
pm2 list

# Auto-start on boot
pm2 startup
pm2 save
```

---

## HTTPS/SSL Setup

1. **Install Certbot:**
   ```bash
   sudo apt install certbot python3-certbot-apache
   ```

2. **Get SSL certificate:**
   ```bash
   sudo certbot --apache -d your-domain.com
   ```

3. **Auto-renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```

---

## Firewall Configuration

```bash
# Allow Apache
sudo ufw allow 'Apache Full'

# Or specific ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Node.js port (only if direct access needed)
sudo ufw allow 8000/tcp
```

---

## Troubleshooting

**Apache logs:**
```bash
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log
```

**PM2 logs:**
```bash
pm2 logs hb-service --lines 100
```

**Test Node.js directly:**
```bash
curl http://localhost:8000/health
```

**Test Apache proxy:**
```bash
curl http://your-domain.com/health
```

---

## Recommended Setup for Production

✅ **Apache reverse proxy** (handles SSL, caching, security)  
✅ **PM2** (keeps Node.js running, auto-restart)  
✅ **SSL/HTTPS** (via Let's Encrypt)  
✅ **Firewall** (UFW/iptables)  

This gives you the best of both worlds: Apache's stability and Node.js's performance!
