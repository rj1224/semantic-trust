# Ownership Validation Rules — `[O]` CI Gate

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Verifies that every data asset has a real, accountable owner. Blocks spurious or blank values. Binary pass/fail — blocks PR merge on failure.

## What it checks

- All ownership fields are non-blank: `business_owner`, `technical_owner`, `business_domain`, `refresh_cadence`, `tags`, `approved_by`
- Email format is valid (`name@domain.tld`)
- Domain is on the approved list (configured in `.semantic-trust.json` → `approved_email_domains`)
- Email does NOT match placeholder patterns (see below)
- `technical_owner` is a non-empty list (not `[]`)
- `tags` is a non-empty list (not `[]`)

## When it fails

- Blank values → ownership not yet assigned. Author must fill before merge.
- Spurious email (e.g., `employee-1@your-company.example.com`) → placeholder that was never replaced. Author must provide real contact.
- Invalid domain → typo or external email. Must use a domain in the project's `approved_email_domains` list.

## Check Counts by Document Type

### dbt docs — 2 `[O]` checks
1. Owner email value is valid non-placeholder email
2. Tags value is non-empty list

### Semantic Model — 5 `[O]` checks
1. `business_owner` value is valid non-placeholder email
2. `technical_owner` value is valid non-placeholder email list
3. `business_domain` value non-empty
4. `refresh_cadence` value valid
5. `tags` value non-empty

### Metrics — 4 `[O]` checks
1. `business_owner` value valid non-placeholder
2. `technical_owner` value valid non-placeholder
3. `business_domain` value non-empty
4. `approved_by` value valid non-placeholder

### Few-Shot — 0 `[O]` checks
No ownership fields in few-shot examples.

---

## Email Validation Rules (CI Reference)

### Validation steps (in order)

1. **Not blank** — value is not `""`, `null`, or missing
2. **Valid email format** — matches `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
3. **Approved domain** — domain portion is in the project's `approved_email_domains` list
   (configured in `.semantic-trust.json`; empty list means no domain check is applied)
4. **Not a placeholder** — local part does NOT match any of these patterns:
   - `employee-\d+` (e.g., `employee-1`, `employee-42`)
   - `test-\d+` or `test\d+`
   - `user-\d+` or `user\d+`
   - `example`
   - `placeholder`
   - `todo`
   - Any local part that is purely numeric (e.g., `12345@your-company.example.com`)
   - Any local part matching `[a-z]+-\d+` (generic pattern: word-number)
5. **List fields are non-empty** — `technical_owner: []` and `tags: []` fail the gate

### Placeholder penalty

`<TODO>` values in ownership fields cap the trust score at 65 regardless of content quality. This is a soft penalty — the CI gate blocks merge, but even if the gate were somehow bypassed, the trust score reflects the missing ownership.

### Future enhancement: Directory validation

For maximum confidence, validate emails against the company directory:
- Google Workspace Admin API: `GET /admin/directory/v1/users/{email}` → 200 = active, 404 = invalid
- Fallback: maintain a `valid_owners.txt` allowlist in the dbt repo, updated quarterly
- This catches: typos, former employees, emails that pass format checks but don't exist
