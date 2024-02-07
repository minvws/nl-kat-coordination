class XTDBException(Exception):
    """Base exception for XTDB errors."""


class NodeNotFound(XTDBException):
    """The XTDB node was not found"""
