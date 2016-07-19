django-docker-runner
====================

A test runner for Django that does not require the specified database be installed or setup before the test suite executes.

Why? Because sometimes your application really needs to use that array field that postgres offers. Or anything else that sqlite does not offer (e.g. CTEs, etc.). Or you want your tests to run on the same database that will be used in production.

Docker is a requirement.

Targets the Django and nose test runners.
