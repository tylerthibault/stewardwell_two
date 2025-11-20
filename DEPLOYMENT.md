# CapRover Deployment with MySQL Database

## Automatic Migration Setup

This application is configured to automatically run database migrations on deployment to CapRover.

### How It Works

1. **Docker Build**: When CapRover builds your app, it includes:
   - `migrate_db.py` - Python script to run Flask-Migrate
   - `docker-entrypoint.sh` - Bash script that runs migrations before starting the app
   - All migration files in `migrations/versions/`

2. **On Deployment**: The entrypoint script automatically:
   - Runs `python migrate_db.py` to apply pending migrations
   - Starts the Gunicorn server if migrations succeed
   - Fails the deployment if migrations fail (protecting your database)

### CapRover Environment Variables

Make sure these environment variables are set in your CapRover app:

```bash
# Database Configuration
MYSQL_HOST=srv-captain--your-mysql-service
MYSQL_PORT=3306
MYSQL_USER=stewardwell_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=stewardwell

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
DEPLOYMENT_ENV=production
```

### Migration Files

Current migrations in order:
1. `bf7f8719e106` - Initial schema with is_active
2. `c9a1b2d3e4f5` - Add description to chore
3. `5fa80f4dd703` - Add store items and purchases
4. `d7e8f9a0b1c2` - Add tags and description fields

### Manual Migration (if needed)

If you need to run migrations manually:

```bash
# SSH into your CapRover container
docker exec -it $(docker ps -qf "name=srv-captain--stewardwell") bash

# Run migrations
python migrate_db.py
```

### Troubleshooting

**Migrations fail on deployment:**
- Check CapRover logs for the specific error
- Verify database credentials in environment variables
- Ensure MySQL service is running and accessible
- Check that database user has CREATE/ALTER permissions

**Database connection errors:**
- Verify `MYSQL_HOST` points to the correct MySQL service
- Check that MySQL service is on the same CapRover network
- Test connection: `docker exec <container> python -c "from src import create_app, db; app = create_app(); app.app_context().push(); db.engine.connect()"`

**Rollback a migration:**
```bash
# Downgrade to previous version
flask db downgrade
```

### Creating New Migrations

During development (not on CapRover):

```bash
# Auto-generate migration from model changes
flask db migrate -m "Description of changes"

# Review the generated file in migrations/versions/

# Apply the migration locally to test
flask db upgrade
```

The migration will automatically apply when you push to CapRover.

## First Deployment Checklist

- [ ] MySQL service created in CapRover
- [ ] Database user created with proper permissions
- [ ] Environment variables configured in CapRover
- [ ] App pushed to CapRover
- [ ] Migrations run successfully (check logs)
- [ ] Application starts without errors
- [ ] Can access the application and login

## Files Modified for Auto-Migration

- `Dockerfile` - Updated to use entrypoint script
- `docker-entrypoint.sh` - New file that runs migrations
- `migrate_db.py` - New file that executes Flask-Migrate
- `migrations/versions/d7e8f9a0b1c2_*.py` - Latest migration for current schema
