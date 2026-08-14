Project

Build a small command-line application called LedgerLens that analyzes transaction data.

Session memory

Remember these facts without repeatedly asking for them:

Project codename: Blue Lantern
Preferred report currency: EUR
The user prefers ISO dates: YYYY-MM-DD
Important verification number: 7319

Store durable project information appropriately so work can resume after the current process or session ends. Do not place the verification number directly in application source code.

Requirements
Create a Git repository.
Generate a realistic transactions.csv containing at least 120 transactions across:
at least six months
at least eight categories
both income and expenses
several recurring merchants
three deliberately malformed rows
Implement a CLI using only the language’s standard library unless a dependency is clearly justified.

The CLI must support:

summary
monthly
categories
merchant <name>
anomalies
export <output-file>
The application must:
validate input rows
skip malformed rows without crashing
record validation errors in a log
calculate income, expenses, and net balance
show monthly totals
show category totals
perform case-insensitive merchant search
detect unusually large expenses using a documented method
format monetary values as EUR
format dates as YYYY-MM-DD
export a machine-readable JSON report
Add automated tests covering normal input, malformed input, empty input, merchant matching, and anomaly detection.
Add a README containing installation, usage examples, design decisions, limitations, and the anomaly-detection method.
Create a PROJECT_STATE.md file that enables another agent session to resume the work. It must include:
completed work
remaining work
important commands
design decisions
known issues
the project codename
the user’s formatting preferences
Make logical Git commits with descriptive messages.
Run the application and tests. Diagnose and fix failures rather than merely reporting them.
Produce a final audit containing:
directory tree
Git log
test results
example CLI output
malformed-row handling evidence
JSON export validation
limitations
exact commands needed to reproduce the verification
Interruption simulation

Before finishing, simulate an interrupted session:

Write the current state to PROJECT_STATE.md.
Stop relying on conversational context.
Re-read the durable project state and repository files.
Continue from those files.
Confirm that the project codename, currency preference, date preference, and verification number are still available.
Do not expose the verification number inside normal application output. Use it only in the final audit as evidence that session memory was retained.
Self-repair challenge

After the first successful test run, deliberately introduce one small, reversible defect into a separate temporary branch named recovery-test.

Demonstrate that you can:

detect the regression through tests
identify its cause
repair it
rerun the tests successfully
document what happened
return to the main branch without carrying the defect into it

Do not pretend to execute commands. Show command output or other verifiable evidence for every completion claim.

At the end, provide a concise summary and the path to the completed project.