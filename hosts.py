"""Pin tadbirwrapper to its internal address in /etc/hosts.

The crawler container runs as root, so the write works there; anywhere else (tests, a laptop) it is skipped.
"""
import logging

HOSTS_LINE = "172.20.20.120 tadbirwrapper.tavana.net"


def pin_tadbir_host(path="/etc/hosts"):
    """Append the host entry once. Never fails the job: without it the system DNS is used."""
    try:
        with open(path, "a+", encoding="utf-8") as hosts_file:
            hosts_file.seek(0)
            text = hosts_file.read()
            if HOSTS_LINE not in text:
                separator = "" if not text or text.endswith("\n") else "\n"
                hosts_file.write(separator + HOSTS_LINE + "\n")
    except OSError as err:
        logging.getLogger("crawlers").warning("hosts pin skipped (%s); using system DNS", err)
