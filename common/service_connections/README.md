# Services

This directory is where all the service connections and fenrir API should be located. As stated in the project README these are the abstract services that will connect external tools to FTS.

## Cloud Service

Cloud providers have a million different services and endpoints. The goal of this service is to implement authentication into these environments and perform ONLY the required actions. E.g. Save a file to S3 or Blob storage.

## Containers

Containers are the docker/docker-compose files+configurations that can that be deployed locally or to the cloud so you can perform UI tests.

## Database

Connection point to a database service.

## Reporting

A service that will take reports generated from pytest and send them to a storage location. Fenrir will consume the data from these reports and display it in a dashboard.

## Test Case

Test cases are a well established tool. This service connects to the tool that manages test cases. FTS consume data from the test case source.
