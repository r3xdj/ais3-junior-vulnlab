#!/bin/sh
# Simple CGI test script
printf 'Content-Type: text/plain; charset=utf-8\n\n'
printf 'Test CGI\n'
printf '--------------------\n'
printf 'PWD=%s\n' "$(pwd)"
printf 'USER=%s\n' "$(whoami)"