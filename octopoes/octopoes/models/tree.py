from __future__ import annotations

from typing import Dict, List, Set, Callable

from pydantic.main import BaseModel

from octopoes.models import Reference
from octopoes.models.types import OOIType


class ReferenceNode(BaseModel):
    reference: Reference
    children: Dict[str, List[ReferenceNode]]

    def filter_children(self, filter_fn: Callable[[ReferenceNode], bool]):
        """
        Mutable filter function to evict any children from the tree that do not adhere to the provided callback
        """
        self.children = {
            attr_name: [child for child in children if child.filter_children(filter_fn)]
            for attr_name, children in self.children.items()
        }
        self.children = {key: value for key, value in self.children.items() if value}
        if self.children:
            return True
        return filter_fn(self)

    def collect_references(self) -> Set[Reference]:
        child_references = set()
        for child_name, children in self.children.items():
            child_references_ = [child.collect_references() for child in children]
            # merge list of sets
            child_references_ = set().union(*child_references_)
            child_references = child_references.union(child_references_)

        return {self.reference}.union(child_references)


ReferenceNode.update_forward_refs()


class ReferenceTree(BaseModel):
    root: ReferenceNode
    store: Dict[str, OOIType]
