import hashlib
import hmac


SIGNATURE_PREFIX = "sha256="


def compute_signature(secret: str, raw_body: bytes) -> str:
    """Compute HMAC-SHA256 hex digest for the raw request body."""
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    secret: str | None,
    raw_body: bytes,
    signature_header: str | None,
) -> bool:
    """
    Verify X-PseudoGram-Signature against the exact raw request bytes.

    Returns False when the secret is missing, the header is malformed,
    or the digest does not match.
    """
    if not secret or not signature_header:
        return False

    if not signature_header.startswith(SIGNATURE_PREFIX):
        return False

    provided = signature_header[len(SIGNATURE_PREFIX) :]
    if len(provided) != 64:
        return False

    try:
        int(provided, 16)
    except ValueError:
        return False

    expected = compute_signature(secret, raw_body)
    return hmac.compare_digest(provided, expected)
