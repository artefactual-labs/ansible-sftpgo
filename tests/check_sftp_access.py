from io import BytesIO
import os

import paramiko


transport = paramiko.Transport(("127.0.0.1", int(os.environ.get("SFTPGO_CI_SFTP_PORT", "33322"))))
transport.connect(username="customer", password="sftpgo_ci_customer_password")
sftp = paramiko.SFTPClient.from_transport(transport)

try:
    sftp.chdir("/protected")
    downloaded = BytesIO()
    sftp.getfo("seed.txt", downloaded)
    assert downloaded.getvalue() == b"read-only test fixture\n"

    def assert_denied(operation, description):
        try:
            operation()
        except OSError:
            return
        raise AssertionError(f"protected virtual folder unexpectedly allowed {description}")

    assert_denied(
        lambda: sftp.putfo(BytesIO(b"protected upload must fail\n"), "forbidden.txt"),
        "upload",
    )
    assert_denied(
        lambda: sftp.putfo(BytesIO(b"overwrite must fail\n"), "seed.txt"),
        "overwrite",
    )
    assert_denied(lambda: sftp.remove("seed.txt"), "deletion")
    assert_denied(lambda: sftp.rename("seed.txt", "renamed.txt"), "rename")
    assert_denied(lambda: sftp.mkdir("forbidden-dir"), "directory creation")
    assert_denied(lambda: sftp.chmod("seed.txt", 0o600), "permission change")
    assert_denied(lambda: sftp.utime("seed.txt", None), "timestamp change")

    sftp.chdir("/read-write")
    sftp.putfo(BytesIO(b"read-write upload works\n"), "read-write.txt")
    sftp.remove("read-write.txt")
finally:
    sftp.close()
    transport.close()

print("Protected read-only rules and read-write upload/delete passed")
