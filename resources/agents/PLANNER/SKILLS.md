# Planner Skills

## Create Test Plan

Read the run context and inspect only the allowed URLs. Look for API documentation, common response formats, authentication requirements, allowed methods, and obvious health or version endpoints.

Create tests for:

- availability
- expected success responses
- missing parameters
- invalid input
- authentication problems
- unsupported methods
- response schema checks

Each test must be clear enough for the Executor to run without guessing.
Use `webservice_definition` tool to get information about webservice.
Use `search_for_params` tool to get request parameter values for each endpoint where parameters are required.
Save each test with the use of tool `create_new_task`.
Do not include destructive tests unless the run context explicitly allows them.
