#!/bin/bash
echo -n "Which Browser? chrome, firefox, or edge "
read browser

echo "Killing and removing the Selenium standalone container based on the specified browser"
docker kill selenium-standalone-$browser
docker rm selenium-standalone-$browser

echo "Pulling the Selenium standalone container based on the specified browser"
docker pull selenium/standalone-$browser:4.19

docker run -d -p 4444:4444 --name selenium-standalone-$browser selenium/standalone-$browser:4.19
echo "Selenium standalone container for $browser is running outputting logs to console:"
docker logs -f selenium-standalone-$browser
