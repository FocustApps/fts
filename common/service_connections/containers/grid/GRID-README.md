# Local Docker Container

Useful things for running Selenium Hub Containers locally:

The ```grid-helpers.sh``` file can be executed to get the latest docker-compose-v3 file
from the selenium github repo. This file will have a node for Firefox, Chrome, and Edge.
If you want to only run a specific browser you can delete the "service:" section for the
browsers you don't want to use.

If you want have multiple nodes to run concurrent tests then you can scale up a node using the
following command:

```docker-compose scale chrome=3``
