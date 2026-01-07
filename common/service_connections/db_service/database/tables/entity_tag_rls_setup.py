"""
Row-Level Security (RLS) setup for entity_tag table.

This script contains the SQL commands needed to enable RLS on the entity_tag table
for multi-tenant isolation. Run these commands after the table is created via Alembic migration.

IMPORTANT: RLS requires PostgreSQL 9.5+
"""

# SQL to enable RLS on entity_tag table
ENABLE_RLS_SQL = """
-- Enable Row-Level Security on entity_tag table
ALTER TABLE entity_tag ENABLE ROW LEVEL SECURITY;
"""

# SQL to create RLS policy for account isolation
CREATE_POLICY_SQL = """
-- Create RLS policy to restrict access based on account_id
-- Users can only access tags belonging to their current account context
CREATE POLICY entity_tag_account_isolation_policy ON entity_tag
    FOR ALL
    USING (account_id = current_setting('app.current_account_id', true)::uuid);
"""

# SQL to grant necessary permissions
GRANT_PERMISSIONS_SQL = """
-- Grant permissions to application role
-- Replace 'fenrir_app_user' with your application database user/role
GRANT SELECT, INSERT, UPDATE, DELETE ON entity_tag TO fenrir_app_user;
"""

# SQL to test RLS policy
TEST_POLICY_SQL = """
-- Test RLS policy by setting account context and querying
-- Replace 'test-account-uuid' with an actual account_id

-- Set account context
SET app.current_account_id = 'test-account-uuid';

-- Query should only return tags for the specified account
SELECT * FROM entity_tag;

-- Reset account context
RESET app.current_account_id;
"""

# SQL to disable RLS (for debugging/admin operations only)
DISABLE_RLS_SQL = """
-- CAUTION: Only use this for debugging or admin operations
-- Disabling RLS removes multi-tenant isolation security
ALTER TABLE entity_tag DISABLE ROW LEVEL SECURITY;
"""

# SQL to drop RLS policy
DROP_POLICY_SQL = """
-- Drop the RLS policy if you need to recreate it
DROP POLICY IF EXISTS entity_tag_account_isolation_policy ON entity_tag;
"""

# Complete setup script (run in order)
COMPLETE_SETUP = f"""
-- Complete RLS Setup for entity_tag table
-- Run these commands in order after Alembic migration creates the table

{ENABLE_RLS_SQL}

{CREATE_POLICY_SQL}

{GRANT_PERMISSIONS_SQL}

-- Verify RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'entity_tag';

-- Verify policy exists
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'entity_tag';
"""


def print_setup_instructions():
    """Print RLS setup instructions for manual execution."""
    print("=" * 80)
    print("Row-Level Security Setup for entity_tag Table")
    print("=" * 80)
    print()
    print("After running Alembic migration to create the entity_tag table,")
    print("execute the following SQL commands to enable RLS:")
    print()
    print(COMPLETE_SETUP)
    print()
    print("=" * 80)
    print("Application Code Requirements:")
    print("=" * 80)
    print()
    print("Before each request, set the account context:")
    print("  conn.execute(text('SET app.current_account_id = :account_id'),")
    print("               {'account_id': user_account_id})")
    print()
    print("After the request, reset the context:")
    print("  conn.execute(text('RESET app.current_account_id'))")
    print()
    print("Or use a context manager in your database service:")
    print()
    print("  class AccountContext:")
    print("      def __init__(self, connection, account_id):")
    print("          self.conn = connection")
    print("          self.account_id = account_id")
    print()
    print("      def __enter__(self):")
    print("          self.conn.execute(")
    print("              text('SET app.current_account_id = :account_id'),")
    print("              {'account_id': self.account_id}")
    print("          )")
    print("          return self")
    print()
    print("      def __exit__(self, *args):")
    print("          self.conn.execute(text('RESET app.current_account_id'))")
    print()
    print("Usage:")
    print("  with AccountContext(connection, user_account_id):")
    print("      tags = session.query(EntityTagTable).all()  # RLS applied")
    print()
    print("=" * 80)


if __name__ == "__main__":
    print_setup_instructions()
