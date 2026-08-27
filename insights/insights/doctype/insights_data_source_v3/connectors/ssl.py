# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import tempfile
from contextlib import contextmanager


@contextmanager
def ca_certificate_file(data_source):
    """Yield the path of the source's CA certificate, or None when it has none.

    A CA is what turns an encrypted connection into a verified one, so
    supplying one is how a data source asks to be verified. The drivers read a
    path, not a string, and they read it while connecting — writing the file
    for the length of the connect keeps it off disk the rest of the time.
    """
    certificate = (data_source.get("ssl_ca") or "").strip()
    if not certificate:
        yield None
        return

    with tempfile.NamedTemporaryFile("w", suffix=".pem") as file:
        file.write(certificate + "\n")
        file.flush()
        yield file.name
