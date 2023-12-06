import hashlib
import logging
from typing import Any

from pydantic import AwareDatetime

from bytes.models import (
    HashingAlgorithm,
    RawData,
    SecureHash,
)

logger = logging.getLogger(__name__)


def hash_data(
    data: RawData, datetime: AwareDatetime, hash_algo: HashingAlgorithm = HashingAlgorithm.SHA512
) -> SecureHash:
    """Hash the raw data"""
    timestamp_bytes = str(datetime.timestamp()).encode("utf-8")

    hasher = _get_hasher(hash_algo)
    hasher.update(data.value)
    hasher.update(timestamp_bytes)

    return SecureHash(f"{hash_algo.value}:{hasher.hexdigest()}")


def _get_hasher(hash_algo: HashingAlgorithm) -> Any:
    if hash_algo == HashingAlgorithm.SHA512:
        return hashlib.sha512()

    if hash_algo == HashingAlgorithm.SHA224:
        return hashlib.sha224()

    raise ValueError(f"Hashing algorithm {hash_algo} not implemented")
