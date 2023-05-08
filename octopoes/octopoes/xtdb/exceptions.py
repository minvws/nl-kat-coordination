class XTDBException(Exception):
    """Base exception for XTDB errors."""


class NoMultinode(XTDBException):
    """Kat is not set up with XTDB multinode"""


class NodeNotFound(XTDBException):
    """The XTDB node was not found"""
