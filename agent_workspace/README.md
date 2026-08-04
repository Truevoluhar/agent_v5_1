# Spring Boot Webservice (WAR + EAR)

A minimal Maven multi-module Spring Boot webservice. The `webservice` module produces a deployable WAR, and `webservice-ear` assembles that WAR into an EAR for an application server.

## Structure

- `webservice/` - Spring Boot application, controller, service, configuration, and tests (`war` packaging).
- `webservice-ear/` - EAR assembly module containing `webservice.war` (`ear` packaging).

The example endpoint is `GET /api/v1/hello` and returns `{"message":"Hello from the webservice"}`.

## Requirements

- JDK 17+
- Maven 3.8+
- A Jakarta Servlet-compatible application server for external WAR/EAR deployment

Spring Boot 3 uses Jakarta APIs, so legacy Java EE servers requiring `javax.servlet` are not supported without changing the dependencies and target versions.

## Build

From this directory:

```shell
mvn clean verify
```

Artifacts are created at:

- `webservice/target/webservice.war`
- `webservice-ear/target/webservice.ear`

The WAR can be deployed directly to a compatible servlet container. The EAR contains the WAR with context root `/webservice`; application-server-specific descriptors or classloader settings may still be required.
