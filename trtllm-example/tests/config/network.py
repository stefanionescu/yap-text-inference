"""Network and hostname heuristics used by test utilities."""

TLS_PORT = 443
HTTP_PORT = 80
LOCAL_HOSTNAMES = {"localhost", "ip6-localhost"}
INTERNAL_SUFFIXES = (
    ".local",
    ".internal",
    ".lan",
    ".cluster.local",
    ".localdomain",
)
WS_BUSY_CLOSE_CODE = 1013
