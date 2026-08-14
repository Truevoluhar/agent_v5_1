# Executor Skills

## Run Tests

Get test files from queue with tool `get_tasks`. Skip tests that are unsafe or destructive without permission.
You have the ability to meaningfully provide test execution, that means obtaining valid authentication request parameters, such as usernames, passwords, tokens, etc.
You have the ability to replace placeholder values in test cases with real values, obtained from previous endpoint tests or other sources.
Here is your workflow:
1. Use tool `get_tasks` to get tasks from queue.
2. Pick one test from `get_tasks` result and use tool `load_test` to get information about specific test you want to execute.
3. For every test case use tool `test_endpoint`. Replace request parameter placeholders if necessary. Use `search_for_params` to get parameters for a webservice you are currently testing.Capture response status code, headers, body, elapsed time, and any errors
4. After each executed test case use `save_test_result` tool and provide meaningful task results. Include parameters you used to call a tool in task results.

You must repeat these steps until `get_tasks` doesnt return any items.