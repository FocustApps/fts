# Reporting Service

Charts

:::mermaid
stateDiagram-v2

runner:Test Runner
storage: SQL Table
reportParser: Stored Procedure Parser

runner --> storage
storage --> reportParser

state reportParser {
    Passed
    Failed
    skipped_tests: Do not parse skipped tests or deselected tests.
}

:::

## Tables

:::mermaid
classDiagram
    class IngestTable{
        Created Date : datetime
        Report File : blob
        System Under Test : relational table
    }

    IngestTable --> SystemUnderTestTable

    class SystemUnderTestTable{
        ID: uuid
        Name: string
    }

    class TestRunTable{
        ID : uuid
        System Under Test : Related SUT table
        errors : int
        failures : int
        skipped : int
        tests : int
        time : float
        timestamp : datetime
        hostname : string 
        testcases : relational table id
    }

    IngestTable --> TestRunTable

    class TestCaseTable {
        ID: UUID
        name: string 
        time: datetime
        classname: string
        failure: blob (Optional)
    }

    TestRunTable --> TestCaseTable
:::
