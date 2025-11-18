# 🗄️ Database Performance & Architecture Review

**Reviewer:** Dylan (Backend Genius & Multi-Stack Architect)  
**Date:** 2025-11-14  
**Manager:** @tylerthibault  
**Focus:** Database Optimization, Schema Design & Performance Analysis

---

## Executive Summary
[Assessment of database architecture, query performance, and optimization opportunities]

**Database Health Score:** X/10
- **Schema Design:** X/10 (Normalization, relationships, constraints)
- **Query Performance:** X/10 (Execution times, index usage, N+1 problems)
- **Scalability:** X/10 (Connection pooling, read replicas, partitioning)
- **Security:** X/10 (Access control, data protection, audit trails)
- **Monitoring:** X/10 (Query logging, performance metrics, alerting)

**Key Findings:** X Critical | X High | X Medium | X Low

---

## Database Environment Assessment

### Database Technology Stack
**Detected Systems:**
- [ ] **PostgreSQL** (Recommended for complex queries, JSONB, full-text search)
- [ ] **MySQL/MariaDB** (High performance, replication, web applications)
- [ ] **MongoDB** (Document storage, flexible schema, rapid development)
- [ ] **SQL Server** (Enterprise features, .NET integration, BI tools)
- [ ] **SQLite** (Embedded, development, small applications)

**Connection Technologies:**
- [ ] **Python**: SQLAlchemy, Django ORM, asyncpg, psycopg2
- [ ] **Node.js**: Prisma, Sequelize, TypeORM, Knex.js
- [ ] **C#**: Entity Framework Core, Dapper, ADO.NET

---

## Dylan's Database Crime Scene Investigation

### 🔴 **Critical Database Crimes**

#### 1. **The Dreaded N+1 Query Problem**
**Crime:** Multiple queries when one would suffice
```python
# ❌ GUILTY - N+1 Query Nightmare
def get_users_with_orders():
    users = User.objects.all()  # 1 query
    for user in users:
        orders = user.orders.all()  # N queries (one per user)
        print(f"{user.name}: {len(orders)} orders")
    # Total: 1 + N queries = DISASTER
```

**Dylan's Fix:**
```python
# ✅ REDEEMED - Proper eager loading
def get_users_with_orders():
    users = User.objects.prefetch_related('orders').all()  # 2 queries total
    for user in users:
        orders = user.orders.all()  # No additional queries!
        print(f"{user.name}: {len(orders)} orders")

# Alternative with select_related for ForeignKey
users = User.objects.select_related('profile').prefetch_related('orders')

# Raw SQL for maximum control
query = """
    SELECT u.*, COUNT(o.id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id
"""
```

#### 2. **Missing or Ineffective Indexes**
**Crime:** Full table scans on large datasets
```sql
-- ❌ GUILTY - No index on frequently queried column
SELECT * FROM orders WHERE user_id = 123 AND created_at > '2025-01-01';
-- Table scan on 10M+ records = 30 second query
```

**Dylan's Fix:**
```sql
-- ✅ REDEEMED - Strategic indexing
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at);
CREATE INDEX idx_orders_status_created ON orders(status, created_at) 
    WHERE status IN ('pending', 'processing');

-- Composite index for common query patterns
CREATE INDEX idx_orders_compound ON orders(user_id, status, created_at DESC);

-- Partial index for specific conditions
CREATE INDEX idx_orders_active ON orders(created_at) 
    WHERE status NOT IN ('cancelled', 'completed');

-- Index usage verification
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM orders WHERE user_id = 123 AND created_at > '2025-01-01';
```

#### 3. **Connection Pool Exhaustion**
**Crime:** Not managing database connections properly
```python
# ❌ GUILTY - Connection chaos
def get_user_data(user_id):
    # Opening new connection each time
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    # ... query logic
    # Forgot to close connection! 💥
```

**Dylan's Fix:**
```python
# ✅ REDEEMED - Proper connection pooling

# SQLAlchemy connection pool
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Normal connections
    max_overflow=20,       # Burst connections
    pool_pre_ping=True,    # Validate connections
    pool_recycle=3600,     # Recycle after 1 hour
)

# Context manager for automatic cleanup
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()

# Usage
def get_user_data(user_id):
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT * FROM users WHERE id = %s", (user_id,)
        )
        return result.fetchone()
```

### 🟠 **High Priority Issues**

#### 4. **Poor Schema Design**
**Crime:** Denormalized chaos or over-normalization
```sql
-- ❌ GUILTY - All user data in one massive table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    -- 50+ more columns...
);
```

**Dylan's Fix:**
```sql
-- ✅ REDEEMED - Proper normalization and relationships

-- Core user entity
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profile (1:1 relationship)
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    date_of_birth DATE,
    phone VARCHAR(20),
    bio TEXT,
    avatar_url VARCHAR(255)
);

-- Addresses (1:many relationship)
CREATE TABLE user_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(20) CHECK (type IN ('home', 'work', 'billing', 'shipping')),
    line1 VARCHAR(255) NOT NULL,
    line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(50) DEFAULT 'US',
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ensure one primary address per type
CREATE UNIQUE INDEX idx_user_primary_address 
ON user_addresses(user_id, type) 
WHERE is_primary = true;
```

#### 5. **Inefficient Pagination**
**Crime:** Using OFFSET for large datasets
```sql
-- ❌ GUILTY - Slow pagination for large offsets
SELECT * FROM orders 
ORDER BY created_at DESC 
LIMIT 10 OFFSET 100000;  -- Scans 100,010 rows to return 10
```

**Dylan's Fix:**
```sql
-- ✅ REDEEMED - Cursor-based pagination
SELECT * FROM orders 
WHERE created_at < '2025-01-15 10:30:00'  -- Cursor from last result
ORDER BY created_at DESC 
LIMIT 10;

-- Keyset pagination for better performance
SELECT * FROM orders 
WHERE (created_at, id) < ('2025-01-15 10:30:00', 12345)
ORDER BY created_at DESC, id DESC
LIMIT 10;
```

---

## Multi-Stack Database Optimization

### Python (SQLAlchemy + PostgreSQL)
```python
# models.py - Optimized ORM models
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)
    
    # Relationships with lazy loading control
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user", lazy='select')
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_username', 'created_at', 'username'),
    )

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, index=True)
    
    user = relationship("User", back_populates="orders")
    
    __table_args__ = (
        # Composite index for common query patterns
        Index('idx_order_user_status_created', 'user_id', 'status', 'created_at'),
        # Partial index for active orders
        Index('idx_order_active', 'created_at', postgresql_where="status IN ('pending', 'processing')"),
    )

# Optimized queries
class UserService:
    @staticmethod
    def get_users_with_recent_orders(days=30):
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return session.query(User)\
            .options(
                joinedload(User.profile),  # Eager load profile
                selectinload(User.orders.and_(Order.created_at >= cutoff_date))
            )\
            .join(Order)\
            .filter(Order.created_at >= cutoff_date)\
            .distinct()
    
    @staticmethod
    def get_user_order_summary(user_id):
        # Raw SQL for complex aggregation
        query = text("""
            SELECT 
                u.username,
                COUNT(o.id) as total_orders,
                SUM(o.total_amount) as total_spent,
                MAX(o.created_at) as last_order_date,
                AVG(o.total_amount) as avg_order_value
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE u.id = :user_id
            GROUP BY u.id, u.username
        """)
        
        return session.execute(query, {'user_id': user_id}).fetchone()
```

### Node.js (Prisma + PostgreSQL)
```typescript
// schema.prisma - Optimized schema design
model User {
  id          String   @id @default(cuid())
  email       String   @unique
  username    String   @unique
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  profile     UserProfile?
  orders      Order[]
  
  @@index([email, createdAt])
  @@index([createdAt, username])
  @@map("users")
}

model Order {
  id          Int      @id @default(autoincrement())
  userId      String
  status      OrderStatus @default(PENDING)
  totalAmount Decimal
  createdAt   DateTime @default(now())
  
  user        User     @relation(fields: [userId], references: [id])
  
  @@index([userId, status, createdAt])
  @@index([createdAt]) // For pagination
  @@map("orders")
}

// services/userService.ts - Optimized queries
export class UserService {
  async getUsersWithRecentOrders(days: number = 30) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    
    return await prisma.user.findMany({
      include: {
        profile: true,
        orders: {
          where: {
            createdAt: {
              gte: cutoffDate
            }
          },
          orderBy: {
            createdAt: 'desc'
          },
          take: 10  // Limit recent orders
        }
      },
      where: {
        orders: {
          some: {
            createdAt: {
              gte: cutoffDate
            }
          }
        }
      }
    });
  }
  
  async getUserOrderSummary(userId: string) {
    // Raw SQL for complex aggregation
    const result = await prisma.$queryRaw`
      SELECT 
        u.username,
        COUNT(o.id)::int as "totalOrders",
        COALESCE(SUM(o.total_amount), 0) as "totalSpent",
        MAX(o.created_at) as "lastOrderDate",
        COALESCE(AVG(o.total_amount), 0) as "avgOrderValue"
      FROM users u
      LEFT JOIN orders o ON u.id = o.user_id
      WHERE u.id = ${userId}
      GROUP BY u.id, u.username
    `;
    
    return result[0];
  }
  
  // Cursor-based pagination
  async getOrdersPaginated(cursor?: string, limit: number = 10) {
    return await prisma.order.findMany({
      take: limit + 1,  // Take one extra to check if there's more
      cursor: cursor ? { id: parseInt(cursor) } : undefined,
      skip: cursor ? 1 : 0,  // Skip the cursor
      orderBy: {
        createdAt: 'desc'
      },
      include: {
        user: {
          select: {
            username: true,
            email: true
          }
        }
      }
    });
  }
}
```

### C# (Entity Framework Core + SQL Server)
```csharp
// Models/User.cs - Optimized entity configuration
public class User
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Email { get; set; }
    public string Username { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    
    // Navigation properties
    public UserProfile Profile { get; set; }
    public ICollection<Order> Orders { get; set; }
}

// Data/ApplicationDbContext.cs
public class ApplicationDbContext : DbContext
{
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // User configuration
        modelBuilder.Entity<User>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Email).IsRequired().HasMaxLength(100);
            entity.Property(e => e.Username).IsRequired().HasMaxLength(50);
            
            // Indexes
            entity.HasIndex(e => e.Email).IsUnique();
            entity.HasIndex(e => new { e.Email, e.CreatedAt });
            entity.HasIndex(e => new { e.CreatedAt, e.Username });
            
            // Relationships
            entity.HasOne(e => e.Profile)
                  .WithOne(p => p.User)
                  .HasForeignKey<UserProfile>(p => p.UserId)
                  .OnDelete(DeleteBehavior.Cascade);
        });
        
        // Order configuration
        modelBuilder.Entity<Order>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.TotalAmount).HasColumnType("decimal(18,2)");
            
            // Composite index for common queries
            entity.HasIndex(e => new { e.UserId, e.Status, e.CreatedAt });
            
            // Filtered index for active orders
            entity.HasIndex(e => e.CreatedAt)
                  .HasFilter("[Status] IN ('Pending', 'Processing')");
        });
    }
    
    // Query optimization
    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        optionsBuilder
            .EnableSensitiveDataLogging(false)
            .EnableServiceProviderCaching()
            .EnableDetailedErrors()
            .UseSqlServer(connectionString, options =>
            {
                options.CommandTimeout(30);
                options.EnableRetryOnFailure(3);
            });
    }
}

// Services/UserService.cs - Optimized data access
public class UserService
{
    private readonly ApplicationDbContext _context;
    
    public UserService(ApplicationDbContext context)
    {
        _context = context;
    }
    
    public async Task<List<UserOrderSummaryDto>> GetUsersWithRecentOrdersAsync(int days = 30)
    {
        var cutoffDate = DateTime.UtcNow.AddDays(-days);
        
        // Optimized query with projection
        return await _context.Users
            .Where(u => u.Orders.Any(o => o.CreatedAt >= cutoffDate))
            .Select(u => new UserOrderSummaryDto
            {
                Username = u.Username,
                Email = u.Email,
                TotalOrders = u.Orders.Count(),
                TotalSpent = u.Orders.Sum(o => o.TotalAmount),
                LastOrderDate = u.Orders.Max(o => o.CreatedAt),
                RecentOrdersCount = u.Orders.Count(o => o.CreatedAt >= cutoffDate)
            })
            .AsNoTracking()  // Read-only query optimization
            .ToListAsync();
    }
    
    public async Task<UserDetailDto> GetUserWithOrdersAsync(Guid userId)
    {
        return await _context.Users
            .Include(u => u.Profile)
            .Include(u => u.Orders.OrderByDescending(o => o.CreatedAt).Take(10))
            .Where(u => u.Id == userId)
            .Select(u => new UserDetailDto
            {
                Id = u.Id,
                Username = u.Username,
                Profile = u.Profile,
                RecentOrders = u.Orders.Select(o => new OrderSummaryDto
                {
                    Id = o.Id,
                    TotalAmount = o.TotalAmount,
                    Status = o.Status,
                    CreatedAt = o.CreatedAt
                }).ToList()
            })
            .AsNoTracking()
            .FirstOrDefaultAsync();
    }
    
    // Raw SQL for complex queries
    public async Task<List<OrderAnalyticsDto>> GetOrderAnalyticsAsync()
    {
        return await _context.Database
            .SqlQueryRaw<OrderAnalyticsDto>(@"
                SELECT 
                    DATEPART(year, created_at) as Year,
                    DATEPART(month, created_at) as Month,
                    COUNT(*) as OrderCount,
                    SUM(total_amount) as Revenue,
                    AVG(total_amount) as AverageOrderValue
                FROM orders 
                WHERE created_at >= DATEADD(year, -1, GETUTCDATE())
                GROUP BY DATEPART(year, created_at), DATEPART(month, created_at)
                ORDER BY Year, Month
            ")
            .ToListAsync();
    }
}
```

---

## Query Performance Analysis

### Query Execution Plan Analysis
```sql
-- PostgreSQL query analysis
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT u.username, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= '2025-01-01'
GROUP BY u.id, u.username
ORDER BY order_count DESC
LIMIT 10;

-- Key metrics to analyze:
-- 1. Execution Time
-- 2. Index Usage (Index Scan vs Seq Scan)
-- 3. Buffer Usage
-- 4. Sort Operations
-- 5. Join Methods (Hash Join, Nested Loop, Merge Join)
```

### Index Usage Monitoring
```sql
-- PostgreSQL index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0  -- Unused indexes
ORDER BY schemaname, tablename;

-- Table scan statistics
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    seq_tup_read / seq_scan as avg_seq_read
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC;
```

---

## Database Security Best Practices

### Access Control & Permissions
```sql
-- Create dedicated application user with minimal permissions
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_random_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE myapp TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON users, orders, user_profiles TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Read-only reporting user
CREATE ROLE reporting_user WITH LOGIN PASSWORD 'another_secure_password';
GRANT CONNECT ON DATABASE myapp TO reporting_user;
GRANT USAGE ON SCHEMA public TO reporting_user;
GRANT SELECT ON users, orders, user_profiles TO reporting_user;

-- Row Level Security (RLS)
ALTER TABLE user_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_data_policy ON user_data
FOR ALL TO app_user
USING (user_id = current_setting('app.current_user_id')::UUID);
```

### Data Protection & Auditing
```sql
-- Audit trail table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_id UUID,
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100)
);

-- Audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log(table_name, operation, user_id, old_data, changed_by)
        VALUES (TG_TABLE_NAME, 'DELETE', OLD.user_id, row_to_json(OLD), current_user);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log(table_name, operation, user_id, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'UPDATE', NEW.user_id, row_to_json(OLD), row_to_json(NEW), current_user);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(table_name, operation, user_id, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'INSERT', NEW.user_id, row_to_json(NEW), current_user);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply audit trigger
CREATE TRIGGER users_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

---

## Monitoring & Alerting

### Database Performance Monitoring
```python
# Database metrics collection
import psutil
import psycopg2
from prometheus_client import Gauge, Counter

# Metrics
db_connections_active = Gauge('db_connections_active', 'Active database connections')
db_connections_total = Gauge('db_connections_total', 'Total database connections')
db_query_duration = Gauge('db_query_duration_seconds', 'Query execution time')
db_slow_queries = Counter('db_slow_queries_total', 'Number of slow queries')

class DatabaseMonitor:
    def __init__(self, connection_string):
        self.connection_string = connection_string
    
    def collect_metrics(self):
        with psycopg2.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            
            # Connection metrics
            cursor.execute("""
                SELECT count(*) as active, 
                       (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_conn
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active, max_conn = cursor.fetchone()
            db_connections_active.set(active)
            db_connections_total.set(max_conn)
            
            # Slow query detection
            cursor.execute("""
                SELECT query, query_start, state, wait_event
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND query_start < NOW() - INTERVAL '30 seconds'
                AND query NOT LIKE '%pg_stat_activity%'
            """)
            
            for query, start, state, wait_event in cursor.fetchall():
                db_slow_queries.inc()
                logger.warning(f"Slow query detected", extra={
                    'query': query[:200],
                    'duration': (datetime.utcnow() - start).total_seconds(),
                    'state': state,
                    'wait_event': wait_event
                })
```

### Automated Query Analysis
```python
# Query performance analyzer
class QueryAnalyzer:
    def __init__(self, connection_string):
        self.connection_string = connection_string
    
    def analyze_query(self, query, params=None):
        with psycopg2.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            
            # Get execution plan
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            cursor.execute(explain_query, params)
            plan = cursor.fetchone()[0]
            
            # Extract key metrics
            execution_time = plan[0]['Execution Time']
            planning_time = plan[0]['Planning Time']
            
            # Check for performance issues
            issues = self._analyze_plan(plan[0]['Plan'])
            
            return {
                'execution_time_ms': execution_time,
                'planning_time_ms': planning_time,
                'issues': issues,
                'recommendations': self._generate_recommendations(issues)
            }
    
    def _analyze_plan(self, plan):
        issues = []
        
        # Check for sequential scans on large tables
        if plan.get('Node Type') == 'Seq Scan':
            rows = plan.get('Plan Rows', 0)
            if rows > 1000:
                issues.append({
                    'type': 'sequential_scan',
                    'severity': 'high',
                    'message': f'Sequential scan on {rows} rows',
                    'table': plan.get('Relation Name')
                })
        
        # Check for expensive sort operations
        if 'Sort' in plan.get('Node Type', ''):
            sort_method = plan.get('Sort Method', '')
            if 'external' in sort_method.lower():
                issues.append({
                    'type': 'external_sort',
                    'severity': 'high',
                    'message': 'Sort operation using disk'
                })
        
        # Recursively check child plans
        for child in plan.get('Plans', []):
            issues.extend(self._analyze_plan(child))
        
        return issues
```

---

## Dylan's Database Optimization Checklist

### Schema Design
- [ ] **Proper normalization** - 3NF for transactional data
- [ ] **Strategic denormalization** - For read-heavy reporting tables
- [ ] **Appropriate data types** - Use smallest viable types
- [ ] **Constraints defined** - NOT NULL, CHECK, UNIQUE, FK constraints
- [ ] **Indexes optimized** - Composite indexes for query patterns

### Query Performance
- [ ] **N+1 queries eliminated** - Use eager loading/joins
- [ ] **Pagination implemented** - Cursor-based for large datasets
- [ ] **Query complexity managed** - Break down complex queries
- [ ] **Prepared statements used** - Prevent SQL injection, improve performance
- [ ] **Result set limits** - Always limit unbounded queries

### Connection Management
- [ ] **Connection pooling configured** - Appropriate pool sizes
- [ ] **Connection timeouts set** - Prevent hanging connections
- [ ] **Retry logic implemented** - Handle transient failures
- [ ] **Connection validation** - Pre-ping or validation queries

### Security & Compliance
- [ ] **Least privilege access** - Role-based permissions
- [ ] **Audit trails implemented** - Track data changes
- [ ] **Sensitive data encrypted** - At rest and in transit
- [ ] **Backup strategy verified** - Regular, tested backups
- [ ] **SQL injection prevented** - Parameterized queries only

### Monitoring & Maintenance
- [ ] **Performance monitoring active** - Query metrics, connection stats
- [ ] **Slow query logging enabled** - Identify performance bottlenecks
- [ ] **Index usage monitored** - Remove unused indexes
- [ ] **Database maintenance scheduled** - VACUUM, REINDEX, ANALYZE
- [ ] **Alerting configured** - Performance degradation, errors

---

## Dylan's Database Wisdom

*"Your database is the foundation of your entire application—treat it with the respect it deserves. A well-designed schema is like a perfectly organized workshop: everything has its place, relationships are clear, and finding what you need is effortless. Remember: optimize for reads if you read more than you write, optimize for writes if it's the opposite, and always measure before you optimize."*

**The Database Golden Rules:**
1. **Measure twice, optimize once** - Profile before assuming
2. **Index strategically** - More isn't always better
3. **Normalize for integrity** - Denormalize for performance (carefully)
4. **Constrain everything** - Let the database enforce rules
5. **Plan for growth** - Today's small table is tomorrow's bottleneck
6. **Monitor religiously** - Databases don't lie about performance

---

*Remember: A slow database makes even the most brilliant application feel sluggish. Make your data layer fast, reliable, and scalable—your users will never know how hard you worked, and that's exactly the point.*