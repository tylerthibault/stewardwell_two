# Database Schema Documentation Template (Lexicon)

## What This Covers
- Database schema documentation (ERD format)
- DBML for dbdiagram.io
- SQL schema with documentation
- Table/column descriptions
- Relationships and constraints
- Indexes and performance considerations

---

## Review Metrics

### Coverage
- Tables documented: X/Y (Z%)
- Relationships documented: X/Y (Z%)
- Indexes documented: X/Y (Z%)
- Constraints documented: X/Y (Z%)

### Quality
- Tables with descriptions: X/Y
- Columns with descriptions: X/Y
- Foreign keys explained: X/Y
- Enum/choice values documented: X/Y

### Completeness
- Migration history tracked: Yes/No
- Data dictionary available: Yes/No
- Relationship diagram current: Yes/No

---

## Primary Format: DBML (for dbdiagram.io)

### Why DBML?
- Visual diagram generation at dbdiagram.io
- Clean, readable syntax
- Easy to version control
- Exports to SQL, PDF, PNG
- Industry standard for schema documentation

### ⚠️ CRITICAL DBML SYNTAX RULES

**🚫 Common Mistakes to Avoid:**
1. **NO `note` in Ref definitions** - `Ref: table.col > other.col [note: 'text']` is INVALID
2. **NO standalone Notes** - All `Note:` blocks must be attached to tables/columns/enums
3. **NO duplicate relationships** - Don't define both inline `[ref: >]` AND separate `Ref:` statements
4. **NO schema prefixes in table names** - Use comments for schema documentation

**✅ Correct Patterns:**
- **Relationships:** Use inline `[ref: > table.column]` OR separate `Ref:` statements, NOT both
- **Notes:** Attach to specific elements: `Table { Note: 'text' }` or `column [note: 'text']`  
- **Architecture docs:** Use `//` comments, not standalone `Note:` blocks

### Basic DBML Structure

```dbml
// Database Schema for [Project Name]
// Created: 2025-11-13
// Last Updated: 2025-11-13
// Author: @tylerthibault

Project project_name {
  database_type: 'SQL Server'  // or PostgreSQL, MySQL, SQLite, etc.
  Note: '''
    Brief description of the database purpose.
    What system does this support?
    Multi-database architecture notes go here.
  '''
}

// ================================
// SCHEMA DOCUMENTATION COMMENTS
// ================================
// Use comments for architecture overview
// Explain multi-database design here
// Document schema separation rationale

// Tables defined below
```

---

## Table Documentation Pattern

### Simple Table Example

```dbml
Table users {
  id integer [primary key, increment, note: 'Auto-incrementing user ID']
  username varchar(50) [unique, not null, note: 'Unique username for login']
  email varchar(255) [unique, not null, note: 'User email address']
  password_hash varchar(255) [not null, note: 'Bcrypt hashed password']
  created_at timestamp [default: `now()`, note: 'Account creation timestamp']
  updated_at timestamp [default: `now()`, note: 'Last profile update']
  is_active boolean [default: true, note: 'Account active status']
  role varchar(20) [default: 'user', note: 'Role: user, admin, moderator']
  
  indexes {
    email [unique, name: 'idx_users_email']
    username [unique, name: 'idx_users_username']
    (role, is_active) [name: 'idx_users_role_active']
  }
  
  Note: 'User accounts and authentication. Core table for the application.'
}
```

### Table with Enums

```dbml
enum post_status {
  draft [note: 'Post is being written']
  published [note: 'Post is live']
  archived [note: 'Post is archived but preserved']
  deleted [note: 'Soft-deleted post']
}

Table posts {
  id integer [primary key, increment]
  user_id integer [not null, ref: > users.id, note: 'Post author']
  title varchar(255) [not null, note: 'Post title']
  slug varchar(255) [unique, not null, note: 'URL-friendly slug']
  content text [note: 'Post content in Markdown']
  status post_status [default: 'draft', note: 'Current post status']
  published_at timestamp [note: 'When post went live (null if never published)']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  
  indexes {
    user_id [name: 'idx_posts_user']
    slug [unique, name: 'idx_posts_slug']
    status [name: 'idx_posts_status']
    published_at [name: 'idx_posts_published']
    (user_id, status) [name: 'idx_posts_user_status']
  }
  
  Note: '''
    User-generated posts. Supports draft workflow.
    Posts can be published, archived, or soft-deleted.
  '''
}
```

---

## Relationship Documentation

### Relationship Symbols
- `>` : many-to-one
- `<` : one-to-many
- `-` : one-to-one

### One-to-Many Example

```dbml
Table comments {
  id integer [primary key, increment]
  post_id integer [not null, ref: > posts.id, note: 'Parent post']
  user_id integer [not null, ref: > users.id, note: 'Comment author']
  parent_comment_id integer [ref: > comments.id, note: 'Parent comment for threading']
  content text [not null, note: 'Comment content']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  is_deleted boolean [default: false, note: 'Soft delete flag']
  
  indexes {
    post_id [name: 'idx_comments_post']
    user_id [name: 'idx_comments_user']
    parent_comment_id [name: 'idx_comments_parent']
    (post_id, is_deleted) [name: 'idx_comments_post_active']
  }
  
  Note: 'Comments on posts. Supports nested threading via parent_comment_id.'
}
```

### Many-to-Many Example

```dbml
Table tags {
  id integer [primary key, increment]
  name varchar(50) [unique, not null, note: 'Tag name']
  slug varchar(50) [unique, not null, note: 'URL-friendly slug']
  description text [note: 'Optional tag description']
  created_at timestamp [default: `now()`]
  
  indexes {
    slug [unique, name: 'idx_tags_slug']
  }
  
  Note: 'Tags for categorizing posts.'
}

Table post_tags {
  post_id integer [ref: > posts.id, note: 'Post being tagged']
  tag_id integer [ref: > tags.id, note: 'Tag applied to post']
  created_at timestamp [default: `now()`, note: 'When tag was added']
  
  indexes {
    (post_id, tag_id) [pk, name: 'pk_post_tags']
    tag_id [name: 'idx_post_tags_tag']
  }
  
  Note: 'Many-to-many junction table between posts and tags.'
}
```

### One-to-One Example

```dbml
Table user_profiles {
  id integer [primary key, increment]
  user_id integer [unique, not null, ref: - users.id, note: 'Associated user']
  bio text [note: 'User biography']
  avatar_url varchar(500) [note: 'Profile picture URL']
  website varchar(255) [note: 'Personal website']
  location varchar(100) [note: 'User location']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  
  Note: 'Extended user profile information. One-to-one with users table.'
}
```

---

## 🚨 Relationship Definition Best Practices

### ✅ CORRECT: Choose One Approach

**Option A: Inline Relationships (RECOMMENDED)**
```dbml
Table orders {
  id integer [pk, increment]
  customer_id integer [not null, ref: > customers.id, note: 'Order customer']
  product_id integer [not null, ref: > products.id, note: 'Ordered product']
  created_at timestamp [default: `now()`]
}
```

**Option B: Separate Relationship Definitions**
```dbml
Table orders {
  id integer [pk, increment]  
  customer_id integer [not null, note: 'Order customer']
  product_id integer [not null, note: 'Ordered product']
  created_at timestamp [default: `now()`]
}

// Define relationships separately
Ref: orders.customer_id > customers.id
Ref: orders.product_id > products.id
```

### 🚫 WRONG: Mixed Approaches (Causes Duplicates)

```dbml
// DON'T DO THIS - causes "References with same endpoints exist" error
Table orders {
  id integer [pk, increment]
  customer_id integer [not null, ref: > customers.id, note: 'Order customer']  // Inline ref
}

Ref: orders.customer_id > customers.id  // Duplicate separate ref - ERROR!
```

### 🚫 WRONG: Notes in Ref Statements

```dbml
// DON'T DO THIS - "Unknown ref setting 'note'" error  
Ref: orders.customer_id > customers.id [note: 'Order belongs to customer']  // INVALID!
```

### ✅ CORRECT: Relationship Documentation

Put relationship context in column notes, not Ref statements:
```dbml
Table orders {
  customer_id integer [not null, ref: > customers.id, note: 'Foreign key - order belongs to customer']
}
```

---

## Advanced Patterns

### Soft Deletes

```dbml
Table articles {
  id integer [primary key, increment]
  title varchar(255) [not null]
  content text
  deleted_at timestamp [note: 'Soft delete timestamp (null = not deleted)']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  
  indexes {
    deleted_at [name: 'idx_articles_deleted']
  }
  
  Note: 'Uses soft deletes. Filter WHERE deleted_at IS NULL for active records.'
}
```

### Polymorphic Relationships

```dbml
Table attachments {
  id integer [primary key, increment]
  attachable_type varchar(50) [not null, note: 'Type: Post, Comment, Message']
  attachable_id integer [not null, note: 'ID of the parent record']
  file_name varchar(255) [not null]
  file_url varchar(500) [not null]
  file_size integer [note: 'Size in bytes']
  mime_type varchar(100) [note: 'File MIME type']
  created_at timestamp [default: `now()`]
  
  indexes {
    (attachable_type, attachable_id) [name: 'idx_attachments_polymorphic']
  }
  
  Note: '''
    Polymorphic attachment system. Can attach to Posts, Comments, Messages, etc.
    Query by attachable_type and attachable_id together.
  '''
}
```

### Audit/History Table

```dbml
Table audit_log {
  id integer [primary key, increment]
  table_name varchar(50) [not null, note: 'Which table was modified']
  record_id integer [not null, note: 'ID of modified record']
  action varchar(20) [not null, note: 'Action: INSERT, UPDATE, DELETE']
  old_values jsonb [note: 'Previous values (for UPDATE/DELETE)']
  new_values jsonb [note: 'New values (for INSERT/UPDATE)']
  user_id integer [ref: > users.id, note: 'Who made the change']
  ip_address varchar(45) [note: 'IP address of change']
  created_at timestamp [default: `now()`]
  
  indexes {
    (table_name, record_id) [name: 'idx_audit_table_record']
    user_id [name: 'idx_audit_user']
    created_at [name: 'idx_audit_created']
  }
  
  Note: 'Audit trail for all data changes. Tracks who changed what and when.'
}
```

---

## 📝 Architecture Documentation Patterns

### ✅ CORRECT: Use Comments for Schema Summary

```dbml
// ================================
// DATABASE ARCHITECTURE OVERVIEW
// ================================
//
// MULTI-DATABASE DESIGN:
//   - primary: Core application data (users, posts, etc.)
//   - analytics: Read-only analytics and reporting data  
//   - logs: Application logs and audit trails
//
// SOFT DELETE STRATEGY:
//   - All user-generated content uses deleted_at timestamp
//   - NULL = active record, timestamp = soft deleted
//   - Enables complete audit trail and data recovery
//
// DEPARTMENT ISOLATION:
//   - Content scoped by department field
//   - Enables role-based access and specialized workflows
//
// PERFORMANCE CONSIDERATIONS:
//   - Comprehensive indexing on common query patterns
//   - Separate read replicas for analytics queries
//   - Partitioning on large tables by date ranges

TableGroup core_tables {
  users
  posts
  comments
  Note: 'Core application functionality'
}
```

### 🚫 WRONG: Standalone Note Blocks

```dbml
// DON'T DO THIS - "Sticky note must have a name" error
Note: '''
  This standalone note will cause an error because
  it's not attached to a specific table, column, or element.
'''

Table users {
  // table definition
}
```

### ✅ CORRECT: Table-Attached Architecture Notes

```dbml
Table system_config {
  id integer [pk, increment]
  config_key varchar(100) [unique, not null]
  config_value text [not null]
  
  Note: '''
    SYSTEM ARCHITECTURE NOTES:
    
    This table serves as the central configuration store.
    Multi-database design uses separate bindings:
    - __bind_key__ = "primary" for main app data
    - __bind_key__ = "analytics" for reporting data
    - __bind_key__ = "logs" for audit trails
    
    Soft delete pattern used throughout:
    - deleted_at IS NULL = active records
    - deleted_at timestamp = soft deleted
    
    Department isolation implemented via department column
    in user-generated content tables.
  '''
}
```

---

## Alternative Format: Documented SQL

### When to Use SQL Format
- Project already has migration files
- Need to show exact DDL syntax
- Database-specific features (PostgreSQL arrays, MySQL JSON, etc.)
- Teaching/documentation purposes

### SQL Schema Example

```sql
-- ============================================
-- Users Table
-- ============================================
-- Purpose: Core user accounts and authentication
-- Owner: @tylerthibault
-- Created: 2025-01-13
-- Last Modified: 2025-01-13

CREATE TABLE users (
    id SERIAL PRIMARY KEY,  -- Auto-incrementing user ID
    username VARCHAR(50) UNIQUE NOT NULL,  -- Unique username for login
    email VARCHAR(255) UNIQUE NOT NULL,  -- User email address
    password_hash VARCHAR(255) NOT NULL,  -- Bcrypt hashed password
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Account creation
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Last update
    is_active BOOLEAN DEFAULT TRUE,  -- Account active status
    role VARCHAR(20) DEFAULT 'user'  -- Role: user, admin, moderator
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role_active ON users(role, is_active);

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts and authentication';
COMMENT ON COLUMN users.id IS 'Auto-incrementing user ID';
COMMENT ON COLUMN users.role IS 'User role: user, admin, or moderator';


-- ============================================
-- Posts Table
-- ============================================
-- Purpose: User-generated posts with draft workflow
-- Relationships: users (author)

CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived', 'deleted');

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT,
    status post_status DEFAULT 'draft',
    published_at TIMESTAMP,  -- Null if never published
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_user ON posts(user_id);
CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_published ON posts(published_at);

COMMENT ON TABLE posts IS 'User-generated posts with publishing workflow';
COMMENT ON COLUMN posts.status IS 'Current status: draft, published, archived, or deleted';
COMMENT ON COLUMN posts.published_at IS 'Timestamp when post went live (null if never published)';
```

---

## Data Dictionary Format

### When to Include a Data Dictionary
- Complex domain with many business terms
- Non-technical stakeholders need reference
- Onboarding documentation
- Compliance/audit requirements

### Data Dictionary Example

```markdown
# Data Dictionary

## Users Table

| Column | Type | Constraints | Description | Business Rules |
|--------|------|-------------|-------------|----------------|
| id | integer | PK, auto-increment | Unique user identifier | System-generated |
| username | varchar(50) | UNIQUE, NOT NULL | Login username | 3-50 chars, alphanumeric + underscore |
| email | varchar(255) | UNIQUE, NOT NULL | User email | Must be valid email format |
| password_hash | varchar(255) | NOT NULL | Bcrypt password hash | Never store plain text passwords |
| created_at | timestamp | DEFAULT now() | Account creation time | System-generated, immutable |
| updated_at | timestamp | DEFAULT now() | Last profile update | Auto-updated on changes |
| is_active | boolean | DEFAULT true | Account status | Inactive = soft delete |
| role | varchar(20) | DEFAULT 'user' | User role | Values: user, admin, moderator |

## Posts Table

| Column | Type | Constraints | Description | Business Rules |
|--------|------|-------------|-------------|----------------|
| id | integer | PK, auto-increment | Unique post identifier | System-generated |
| user_id | integer | FK → users.id, NOT NULL | Post author | Must exist in users table |
| title | varchar(255) | NOT NULL | Post title | Max 255 characters |
| slug | varchar(255) | UNIQUE, NOT NULL | URL-friendly identifier | Auto-generated from title |
| content | text | | Post content | Markdown format |
| status | enum | DEFAULT 'draft' | Publication status | draft, published, archived, deleted |
| published_at | timestamp | | When post went live | Null until first publish |
| created_at | timestamp | DEFAULT now() | Post creation time | System-generated |
| updated_at | timestamp | DEFAULT now() | Last edit time | Auto-updated |
```

---

## Common Findings for Database Schema Docs

### Missing Documentation
- Tables without descriptions
- Columns without notes/comments
- Undocumented relationships
- Missing enum value explanations
- No index documentation
- Foreign key constraints not explained

### Incomplete Documentation
- Generic descriptions ("stores data")
- Missing business rules
- Undocumented data formats/patterns
- No migration history
- Missing performance notes
- Unclear soft delete strategy

### Accuracy Issues
- Documentation doesn't match actual schema
- Outdated table/column names
- Missing recent migrations
- Incorrect relationship cardinality
- Wrong data types documented

### Clarity Issues
- Unclear naming conventions
- Abbreviations not explained
- Complex relationships not diagrammed
- No visual ERD provided

---

## 🔧 DBML Troubleshooting Guide

### Common DBML Syntax Errors & Solutions

#### Error: "Unknown ref setting 'note'"
**Problem:** `Ref: table.col > other.col [note: 'text']`  
**Solution:** Remove notes from Ref statements - put context in column notes instead
```dbml
// ❌ WRONG
Ref: orders.customer_id > customers.id [note: 'Order belongs to customer']

// ✅ CORRECT  
Table orders {
  customer_id integer [ref: > customers.id, note: 'Foreign key - order belongs to customer']
}
```

#### Error: "References with same endpoints exist"
**Problem:** Defining relationships both inline AND separately  
**Solution:** Choose one approach - inline OR separate, not both
```dbml
// ❌ WRONG - causes duplicate error
Table orders {
  customer_id integer [ref: > customers.id]  // Inline definition
}
Ref: orders.customer_id > customers.id       // Separate definition - DUPLICATE!

// ✅ CORRECT - use inline only
Table orders {
  customer_id integer [ref: > customers.id, note: 'Order customer']
}
```

#### Error: "Sticky note must have a name"
**Problem:** Standalone `Note:` blocks at schema level  
**Solution:** Convert to comments or attach to table/enum
```dbml
// ❌ WRONG - standalone note
Note: '''
  Architecture overview here...
'''

// ✅ CORRECT - use comments
// ================================
// ARCHITECTURE OVERVIEW
// ================================
// Multi-database design explanation...
// Performance considerations...

// OR attach to table
Table system_info {
  version varchar(20)
  Note: '''
    SYSTEM ARCHITECTURE:
    Overview and design decisions...
  '''
}
```

#### Error: "Table [name] doesn't exist"
**Problem:** Typo in relationship reference or case sensitivity  
**Solution:** Ensure exact table/column name matches
```dbml
// ❌ WRONG - case mismatch
Table TestReq { id integer [pk] }
Ref: orders.part_id > testreq.id    // Should be 'TestReq'

// ✅ CORRECT - exact match
Ref: orders.part_id > TestReq.id
```

### Pre-Validation Checklist

Before pasting into dbdiagram.io:
- [ ] No `[note: '...']` in `Ref:` statements
- [ ] No duplicate relationship definitions (inline + separate)  
- [ ] No standalone `Note:` blocks - use comments or attach to elements
- [ ] All table/column names in relationships match exactly
- [ ] All enum values have proper syntax
- [ ] All `indexes {}` blocks are properly formatted

---

## Lexicon's Tone for Database Docs

**When reviewing schema:**
- "This table is called 'data.' That's not a name, that's a cry for help."
- "No comments, no notes, no idea what 'flag_2' means. Future-you is going to hate past-you."
- "Relationship between users and posts is documented! This is the bare minimum but I'll take it."

**When creating schema docs:**
- Be specific: not "user data" but "user's billing address for invoices"
- Explain business rules: "soft delete: deleted_at IS NOT NULL"
- Note performance considerations: "indexed for common queries"
- Clarify unusual patterns: "polymorphic - attachable_type + attachable_id"

**When the docs are good:**
- "This DBML is *chef's kiss*. Every table documented, relationships clear, enums explained. Perfection."
- "Finally, a schema doc that actually helps me understand the domain model. Bravo."
- "This data dictionary just saved me from asking 10 questions in Slack. Thank you."

---

## Finding Template

```markdown
### Finding #X: Undocumented user_sessions table
**Severity:** 🟠 High **Effort:** Small **Risk:** Low
**Location:** database schema / user_sessions table
**Category:** Missing Documentation

#### The Issue
The `user_sessions` table exists in the database but has zero documentation. 
New developers have no idea what columns mean, how sessions expire, or how 
to query active sessions.

**Current State:**
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    token VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);
```

#### Options

**Option A: Full DBML documentation** [RECOMMENDED]
Complete documentation with relationships, indexes, and business rules.

```dbml
Table user_sessions {
  id integer [primary key, increment, note: 'Unique session ID']
  user_id integer [not null, ref: > users.id, note: 'Session owner']
  token varchar(255) [unique, not null, note: 'JWT session token']
  ip_address varchar(45) [note: 'IP address when session created']
  user_agent text [note: 'Browser user agent string']
  expires_at timestamp [not null, note: 'Session expiration (24 hours from creation)']
  created_at timestamp [default: `now()`, note: 'Session creation time']
  last_activity_at timestamp [note: 'Last API activity timestamp']
  
  indexes {
    user_id [name: 'idx_sessions_user']
    token [unique, name: 'idx_sessions_token']
    expires_at [name: 'idx_sessions_expires']
    (user_id, expires_at) [name: 'idx_sessions_user_active']
  }
  
  Note: '''
    User authentication sessions. Sessions expire after 24 hours.
    Query active sessions: WHERE expires_at > NOW()
    Cleanup job runs daily to delete expired sessions.
  '''
}
```

**Option B: SQL with inline comments**
Lighter weight but still clear.

```sql
-- User Sessions
-- Tracks active user login sessions with JWT tokens
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,  -- Unique session identifier
    user_id INTEGER NOT NULL REFERENCES users(id),  -- Session owner
    token VARCHAR(255) UNIQUE NOT NULL,  -- JWT token (unique per session)
    expires_at TIMESTAMP NOT NULL,  -- Expiration time (24 hours from creation)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When session started
    
    -- Indexes for performance
    INDEX idx_sessions_user (user_id),
    INDEX idx_sessions_expires (expires_at)
);

COMMENT ON TABLE user_sessions IS 'Active user authentication sessions';
```

#### Manager Decision
- [ ] Approve A (DBML)
- [ ] Approve B (SQL)
- [ ] Reject
- [ ] Needs Discussion

**Status:** PENDING
```

---

## Quick Reference: dbdiagram.io Tips

### Viewing Your Schema
1. Go to dbdiagram.io
2. Paste your DBML code
3. Auto-generates visual ERD
4. Export as PDF, PNG, or SQL

### Useful DBML Features
```dbml
// Project metadata
Project my_db {
  database_type: 'PostgreSQL'
  Note: 'Description here'
}

// Table groups (visual organization)
TableGroup user_management {
  users
  user_profiles
  user_sessions
}

// Inline relationships
Table posts {
  user_id integer [ref: > users.id]  // Inline ref
}

// Or separate relationship definitions
Ref: posts.user_id > users.id
```

---

**Lexicon's reminder:** "A database without documentation is just organized chaos. Let's bring order to the data."