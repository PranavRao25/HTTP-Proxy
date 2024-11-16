# HTTP-Proxy

## General Information
This is a Python Implementation of HTTP Proxy in two methods: Threaded & Async<br>
This is done as part of the CS4010 Computer Networks Laboratory<br>

## About Proxies
HTTP Proxies acts as content filters on the HTTP traffic. These are fit on top of browsers by clients who can choose to process the any information being communicated<br>
Here, we can create a Proxy server that acts like a gateway between users and the Internet<br>

## Our Proxy Rules
1. Each request being sent is set such that the Connection field is made Closed instead of Keep-Alive
2. Any Proxy connection is similarly converted into Closed instead of Keep-Alive
3. We lower the HTTP version to HTTP 1.0

## How to use it
There are two implementations: Threaded and Async<br>
We have made two executables which can be run on the command line<br>
They each accept two arguments: host and port details<br>
The log would be printed on the console<br>
