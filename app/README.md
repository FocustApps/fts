# Fenrir API

This directory provides the web app routes for Fenrir, a system designed to integrate and manage various testing tools. It allows users to configure connection points for external tools, set up page object identifiers, and more.

For app-layer conventions and a worked example, see `app/AGENT.md`.

## Routes

### Cases

Details coming soon...

### Containers

These routes manage the test containers used to execute tests. Users can configure the connection strings for test runners through these endpoints.

### Environments

These routes handle the application URLs used during tests. Users can manage environment designations for URLs and associate users with specific environments.

### Pages

These routes manage page object identifiers for Selenium tests. Fenrir employs the page factory model, storing identifiers outside the page object class. This approach allows changes to finder strategies and locators without modifying the code.

### Work Items

These routes store identifiers for test cases that require asynchronous execution, such as emails, data processing, and other tasks.
