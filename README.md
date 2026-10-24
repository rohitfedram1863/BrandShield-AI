# BrandShield AI — Round 2 MVP (Cognify)

## Run on Windows
1. Extract this ZIP.
2. Open Command Prompt in the extracted folder.
3. Run `py -m pip install -r requirements.txt`
4. Run `py app.py`
5. Open `http://127.0.0.1:5000`

The application includes a brand-rule/fact setup, text review, explainable findings, suggested rewrites, revision preservation, human review decisions, SQLite history, and JSON export. The rules-based core works without an API key.

## Optional Gemini tone review
If you have a valid API key, set it in the server environment (never in source code):
`set GEMINI_API_KEY=YOUR_KEY_HERE`
Then restart the app. The optional integration has not been verified with a live key in this package. Without a key, the app uses deterministic checks.

## Important limitations
- This is an MVP, not legal or compliance certification.
- Default brand rules/facts are fictional demo data.
- No production authentication, CSRF protection, or multi-tenant access controls yet. Do not use confidential data or expose publicly with real customer data until these are added.
- Missing evidence does not prove a claim false.
- Test results, public deployment, and GitHub URL must be verified and entered by the participant; none are invented here.

## Suggested demo
1. Click “Load sample content” and run review.
2. Show findings for “No. 1”, “guaranteed results”, “free for everyone”.
3. Explain missing evidence vs proof of falsity.
4. Edit suggested rewrite and submit as new revision.
5. Save a human decision, return to dashboard, show history, and export JSON.

## Round 3 improvements
1. Evidence-linked versioned knowledge base and freshness indicators.
2. Authentication/roles, revision comparison, and audit trail.
3. Governance analytics for recurring violations and unclear rules.
