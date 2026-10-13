# Feature Specification: Move Storage to Aurora Postgres Serverless v2

**Feature Branch**: `007-aurora-postgres-migration`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Lets change from a sqlite db to a amazon aurora postgres serverless v2 db. My infra repo is at ~/code/basso-infra"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deployed app keeps working on the managed database (Priority: P1)

The operator moves the public deployment off the single-file local database and onto a managed, serverless cloud database provisioned from the existing infrastructure repository. The new database starts empty (no existing data is carried over); accounts are registered afresh. Every shipped feature behaves exactly as before.

**Why this priority**: This is the whole point of the feature; without it nothing else matters. It also removes the dependence on a single attached disk for durable data.

**Independent Test**: Deploy against the managed database, register an account, enter a pay schedule and expenses, and confirm the home page leftover and category breakdown match the worked example in the feature 001 quickstart.

**Acceptance Scenarios**:

1. **Given** the app is deployed against the managed database, **When** a user registers, signs in, and loads any page, **Then** the page renders correctly with that account's data only.
2. **Given** a user creates, edits, or deletes records, **When** they reload the page or sign in from another device, **Then** the changes persist.
3. **Given** two accounts exist, **When** one is signed in, **Then** it cannot read or change the other's data (existing isolation guarantees hold unchanged).

---

### User Story 2 - Developing and testing locally still works (Priority: P2)

A developer can run the app and the full automated test suite on their machine without access to the cloud database, and the tests continue to prove cycle math, isolation, and authentication behave correctly.

**Why this priority**: The project's constitution requires automated tests for financial math and data isolation; those must keep running and passing after the switch.

**Independent Test**: On a fresh checkout, follow the documented setup, run the check script, and see all tests and type checks pass.

**Acceptance Scenarios**:

1. **Given** a fresh checkout, **When** the developer follows the documented local setup, **Then** the dev server starts and works against a local database.
2. **Given** the local setup, **When** the check script runs, **Then** all tests and type checks pass.

---

### User Story 3 - Database infrastructure is managed as code, privately (Priority: P2)

The database cluster, its networking, credentials, and access rules are defined in the operator's infrastructure repository, reachable only from the app's own environment, and its credentials are not stored in the application repository.

**Why this priority**: Matches the project's data-privacy rules (no third-party exposure) and the operator's existing practice of defining infrastructure as code.

**Independent Test**: Review the infrastructure definitions and confirm the database has no public endpoint, only the app's environment can connect, and the app receives its credentials at runtime.

**Acceptance Scenarios**:

1. **Given** the infrastructure is applied, **When** connecting to the database from outside the app's private network, **Then** the connection is refused.
2. **Given** the app starts, **When** database credentials are missing or wrong, **Then** it refuses to start with a clear error rather than falling back to a local file.

---

### Edge Cases

- The managed database is scaled down or idle and takes a moment to resume: the first request must succeed (possibly slower) or show a friendly error, never corrupt data.
- Old local database files left on a developer machine are ignored by the app.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deployed app MUST store and read all accounts and budget data from an Amazon Aurora PostgreSQL Serverless v2 database.
- **FR-002**: The app MUST NOT fall back to a local database file in deployment; missing or invalid database configuration MUST stop startup with a clear error.
- **FR-003**: All existing user-visible behavior (sign-in, registration, pay schedule, expenses, cycle leftover, category breakdown, other shipped features) MUST be unchanged.
- **FR-004**: Money MUST remain exact integer cents end to end, with no rounding changes introduced by the move.
- **FR-005**: Every query MUST remain scoped to the signed-in account, and the automated cross-account isolation tests MUST pass against the new database.
- **FR-008**: The database schema MUST be defined in a file tracked in the repository and applied automatically at startup.
- **FR-009**: Because the new database starts empty, the pre-login "unowned data" concept and its `claim-legacy` command are retired; every record MUST belong to an account.
- **FR-010**: Database credentials and connection details MUST be supplied to the app via runtime configuration or a secrets store, never committed to the repository.
- **FR-011**: The database MUST be provisioned from the infrastructure repository, with no public access, reachable only from the app's environment, with encryption at rest and in transit and backups enabled.
- **FR-012**: Developers MUST be able to run the app and the full test suite locally without access to the cloud database.
- **FR-013**: Project documentation and the constitution's storage principles MUST be amended to reflect the new storage baseline before planning begins.
- **FR-016**: The database MUST scale down to zero capacity when idle; the first request after an idle period MAY be slow but MUST succeed.

### Key Entities

- **Existing records (unchanged meaning)**: Accounts, pay schedules, recurring expenses, savings accounts, and credit cards. Only where they are stored changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A newly registered account can enter a pay schedule and expenses and see leftover and breakdown values that match the feature 001 worked example to the cent.
- **SC-002**: No user-visible change in features; every page loads in under 2 seconds under normal use; the first request after a long idle period may take up to 30 seconds while the database resumes.
- **SC-003**: The full automated test suite and type checks pass, including the cross-account isolation tests on every route touching budget data.
- **SC-004**: The database cannot be reached from the public internet, confirmed by a failed connection attempt from outside the app's environment.
- **SC-005**: Data survives an app restart or redeploy with no loss, and the operator can restore from an automated backup.

## Assumptions

- This is a hobby app with a small number of accounts and a small data volume; a brief planned maintenance window for cutover is acceptable.
- The operator's infrastructure repository (`~/code/basso-infra`) is the home for all new cloud resources, following its existing layout and conventions, and already contains the app's deployment, networking, and certificate setup.
- No existing data is carried over: the deployment starts fresh and the previous local database file is simply left alone.
- For local development and tests, a local PostgreSQL-compatible database is acceptable, so the same database engine behavior is exercised in tests.
- KISS: plain SQL, no ORM, no migration framework, no rollback tooling; if the cutover goes wrong, redeploy the previous commit.
- Cost matters more than idle latency: the database pauses to zero capacity when idle.
- Moving storage off the current baseline requires amending the constitution (Principles I and IV) first, as it already notes; that amendment is part of this feature's first step.
