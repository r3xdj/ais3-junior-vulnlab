#!/bin/sh
# Simple Bash CGI debug script
printf 'Content-Type: text/plain; charset=utf-8\r\n\r\n'
printf 'CGI Debug Script\n'
printf '=================================\n'
printf 'REQUEST_METHOD=%s\n' "${REQUEST_METHOD:-<unset>}"
printf 'QUERY_STRING=%s\n' "${QUERY_STRING:-}"
printf 'PATH_INFO=%s\n' "${PATH_INFO:-}"
printf 'PATH_TRANSLATED=%s\n' "${PATH_TRANSLATED:-}"
printf 'CONTENT_TYPE=%s\n' "${CONTENT_TYPE:-}"
printf 'CONTENT_LENGTH=%s\n' "${CONTENT_LENGTH:-}"
printf 'REMOTE_ADDR=%s\n' "${REMOTE_ADDR:-<unset>}"
printf 'HTTP_HOST=%s\n' "${HTTP_HOST:-}"
printf 'HTTP_USER_AGENT=%s\n' "${HTTP_USER_AGENT:-}"
printf 'HTTP_REFERER=%s\n' "${HTTP_REFERER:-}"
printf 'SERVER_NAME=%s\n' "${SERVER_NAME:-}"
printf 'SERVER_PORT=%s\n' "${SERVER_PORT:-}"
printf 'SCRIPT_NAME=%s\n' "${SCRIPT_NAME:-}"
printf 'GATEWAY_INTERFACE=%s\n' "${GATEWAY_INTERFACE:-}"
printf 'SERVER_SOFTWARE=%s\n' "${SERVER_SOFTWARE:-}"
printf 'PWD=%s\n' "$(pwd)"
printf '=================================\n'
printf 'GET/POST parameters:\n'
if [ -n "${QUERY_STRING}" ]; then
    printf '%s\n' "${QUERY_STRING}"
else
    printf '<none>\n'
fi
printf '=================================\n'
printf 'Raw body:\n'
if [ -n "${CONTENT_LENGTH}" ]; then
    body=$(dd bs=1 count="${CONTENT_LENGTH}" 2>/dev/null)
    if [ -n "${body}" ]; then
        printf '%s\n' "${body}"
    else
        printf '<empty>\n'
    fi
else
    body=$(cat)
    if [ -n "${body}" ]; then
        printf '%s\n' "${body}"
    else
        printf '<empty>\n'
    fi
fi
