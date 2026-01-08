# Fenrir Domain Model & Entity Relationships

## Core Entity Hierarchy

```
auth_users (Root Entity - No dependencies)
    │
    ├──> account (Owner: auth_user)
    │       │
    │       ├──> system_under_test (SUT)
    │       │       │
    │       │       ├──> suite
    │       │       │     ├──> test_case
    │       │       │     └──> plan (M:M association)
    │       │       │
    │       │       ├──> test_case
    │       │       └──> action_chain
    │       │
    │       ├──> entity_tag (Polymorphic - can tag any entity)
    │       └──> audit_log (Polymorphic - tracks any entity)
    │
    └──> plan (Owner: auth_user, NO account FK!)

page (Independent - UI locator patterns)
    └──> identifier
```

## Key Insights

### 1. **Multi-Tenancy via Account**

- Most entities belong to an `account` for isolation
- **Exception**: `plan` table has NO `account_id` FK (design flaw or intentional?)

### 2. **Ownership Pattern**

Every entity has:

- `owner_user_id` → auth_users (creator)
- `deactivated_by_user_id` → auth_users (soft delete actor)

### 3. **System Under Test (SUT) as Context**

- SUTs belong to accounts
- Suites, test_cases, and action_chains all reference `sut_id`
- SUT provides the "application context" for test artifacts

### 4. **Test Hierarchy**

```
plan (Test Plan - collection of suites)
  ↓ (M:M via plan_suite association)
suite (Test Suite - collection of test cases)
  ↓ (M:M via suite_test_case association)
test_case (Individual Test)
  ↓ (1:M - one test can have multiple action chains)
action_chain (Selenium steps as JSONB)
```

### 5. **Polymorphic Cross-Cutting Entities**

- **entity_tag**: Can tag ANY entity (suite, test_case, plan, etc.)
  - Uses `entity_type` (string) + `entity_id` (string)
- **audit_log**: Tracks changes to ANY entity
  - Uses `entity_type` + `entity_id` for polymorphic reference

### 6. **Page Objects (Separate Hierarchy)**

- `page` → `identifier` (UI element locators)
- No FK to account or SUT (reusable across projects)

## Fixture Strategy

### Dependency Order for Fixtures

```python
1. auth_user_factory()          # Root - no dependencies
2. account_factory(owner_user_id)  # Needs user
3. system_under_test_factory(account_id, owner_user_id)  # Needs account & user
4. suite_factory(sut_id, account_id, owner_user_id)
5. test_case_factory(sut_id, account_id, owner_user_id)
6. plan_factory(owner_user_id)  # NO account_id!
7. action_chain_factory(sut_id, account_id, owner_user_id)
8. entity_tag_factory(account_id, created_by_user_id, entity_type, entity_id)
9. audit_log_factory(account_id, performed_by_user_id, entity_type, entity_id)
```

### Fixture Patterns

**Option A: Full Auto-Creation (Current)**

```python
def test_something():
    # Auto-creates: user → account → SUT → suite
    suite_id = suite_factory()
```

**Option B: Explicit Context (Better for domain tests)**

```python
def test_multi_tenant_isolation():
    # Setup Account 1
    user1 = auth_user_factory()
    account1 = account_factory(owner_user_id=user1)
    sut1 = system_under_test_factory(account_id=account1)
    
    # Setup Account 2
    user2 = auth_user_factory()
    account2 = account_factory(owner_user_id=user2)
    sut2 = system_under_test_factory(account_id=account2)
    
    # Test: User1's suite should NOT see User2's test cases
    suite1 = suite_factory(account_id=account1, sut_id=sut1)
    test_case2 = test_case_factory(account_id=account2, sut_id=sut2)
    
    # Assert isolation...
```

## Issues to Address

### 1. **Plan Table Missing account_id**

```python
# Current: plan has no account FK
plan = PlanTable(owner_user_id="user-1")  # Multi-tenant leak?

# Expected: should have account for isolation
plan = PlanTable(account_id="acct-1", owner_user_id="user-1")
```

### 2. **Association Tables Not in Analysis**

Missing from fixtures:

- `plan_suite` (M:M between plans and suites)
- `suite_test_case` (M:M between suites and test cases)

### 3. **Polymorphic References Need Validation**

```python
# entity_tag and audit_log use string references
# Need to validate entity_type values against actual table names
VALID_ENTITY_TYPES = [
    "suite", "test_case", "plan", "action_chain",
    "system_under_test", "account", "page", "identifier"
]
```

## Recommended Test Organization

### By Domain Context (Not Alphabetical)

```
tests/
├── test_auth/              # User authentication
│   ├── test_auth_users.py
│   └── test_auth_tokens.py
│
├── test_multi_tenancy/     # Account isolation
│   ├── test_account_isolation.py
│   └── test_cross_tenant_security.py
│
├── test_test_management/   # Core test hierarchy
│   ├── test_plan_suite_relationships.py
│   ├── test_suite_test_case_relationships.py
│   └── test_action_chains.py
│
├── test_metadata/          # Cross-cutting concerns
│   ├── test_entity_tags.py
│   └── test_audit_log.py
│
└── test_page_objects/      # UI automation
    ├── test_pages.py
    └── test_identifiers.py
```

## Next Steps

1. **Create composite fixtures** that setup realistic scenarios:

   ```python
   @pytest.fixture
   def complete_test_hierarchy():
       """Full hierarchy: account → SUT → plan → suite → test_case."""
       user = auth_user_factory()
       account = account_factory(owner_user_id=user)
       sut = system_under_test_factory(account_id=account)
       plan = plan_factory(owner_user_id=user)
       suite = suite_factory(account_id=account, sut_id=sut)
       test_case = test_case_factory(account_id=account, sut_id=sut)
       
       # Link them via association tables
       link_plan_to_suite(plan, suite)
       link_suite_to_test_case(suite, test_case)
       
       return {
           "user": user, "account": account, "sut": sut,
           "plan": plan, "suite": suite, "test_case": test_case
       }
   ```

2. **Add association helper fixtures** for M:M relationships

3. **Group tests by business domain** instead of model files

4. **Add schema validation tests** for polymorphic references
