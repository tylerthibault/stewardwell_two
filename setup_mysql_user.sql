-- Create a user that can connect from any host
-- Replace 'your_password_here' with your actual password

CREATE USER IF NOT EXISTS 'stewardwell'@'%' IDENTIFIED BY 'your_password_here';

-- Grant all privileges on the stewardwell database
GRANT ALL PRIVILEGES ON stewardwell.* TO 'stewardwell'@'%';

-- Apply the changes
FLUSH PRIVILEGES;

-- Show the user was created
SELECT User, Host FROM mysql.user WHERE User = 'stewardwell';
