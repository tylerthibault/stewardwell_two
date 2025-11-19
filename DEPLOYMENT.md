# CapRover Deployment Setup Guide

## Step 1: Set Environment Variables in CapRover

Go to your app in CapRover → App Configs → Environment Variables

Add these variables:

```
DEPLOYMENT_ENV=production
SECRET_KEY=your-production-secret-key-generate-a-strong-random-string
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password-from-caprover-db-setup
MYSQL_HOST=srv-captain--stewardwell-db
MYSQL_PORT=3306
MYSQL_DATABASE=stewardwell
```

**Important:** Replace `your-mysql-password-from-caprover-db-setup` with the actual MySQL root password from your CapRover MySQL database.

## Step 2: Create Database (if not exists)

**The database will be created automatically by the setup script in Step 4.**

If you need to manually verify or create it:

Option A - Using MySQL Client (if you have SSH access):
```bash
mysql -h srv-captain--stewardwell-db -u root -p
# Enter your MySQL password when prompted
```
Then in MySQL:
```sql
CREATE DATABASE IF NOT EXISTS stewardwell CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EXIT;
```

Option B - Using phpMyAdmin (if installed):
1. Access phpMyAdmin
2. Create new database named `stewardwell`
3. Set charset to `utf8mb4` and collation to `utf8mb4_unicode_ci`

Option C - Let the setup script handle it (Recommended):
Skip this step and go directly to Step 3. The `setup_db.py` script will create the database if it doesn't exist.

## Step 3: Deploy Application

```bash
git add .
git commit -m "feat: add database setup and logging"
git push
```

Wait for deployment to complete in CapRover.

## Step 4: Initialize Database Tables

**Option A - Automatic Setup (Recommended):**

The database and tables will be created automatically on first app startup. Just visit your deployed site and the setup will happen automatically.

**Option B - Manual Setup using CapRover CLI:**

If you have CapRover CLI installed:
```bash
caprover run --appName your-app-name --command "python setup_db.py"
```

**Option C - SSH Access:**

If you have SSH access to your CapRover server:
```bash
# SSH into your server
ssh root@your-server

# Find your container
docker ps | grep stewardwell

# Execute command in container
docker exec -it <container-id> python setup_db.py
```

Expected output:
```
Testing database connection...
✓ Database connection successful!

Creating database tables...
✓ All tables created successfully!

✓ Created X tables:
  - family
  - parent
  - kid
  - chore
  - chore_assignment
  - store_item
  - purchase

✓ Database setup complete!
```

## Step 5: Verify

1. Check your app logs in CapRover for:
   ```
   [DATABASE] Using MySQL: root@srv-captain--stewardwell-db:3306/stewardwell
   ```

2. Try creating a user on your deployed site

## Troubleshooting

### "Can't connect to MySQL server"
- Verify MySQL database app is running in CapRover
- Check `MYSQL_HOST` matches your database service name
- Verify MySQL password is correct

### "Access denied for user 'root'"
- Double-check `MYSQL_PASSWORD` environment variable
- Verify MySQL root password in database settings

### "Unknown database 'stewardwell'"
- Run Step 2 to create the database
- Check database name in `MYSQL_DATABASE` env var

### Tables don't exist
- Run `python setup_db.py` in CapRover web terminal

### Still getting 500 errors
- Check app logs in CapRover for detailed error messages
- Verify all environment variables are set correctly
- Ensure `pymysql` is in requirements.txt (already added)
