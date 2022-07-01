from typing import Tuple, Dict, Set, Optional

from octopoes.xtdb import Datamodel, FieldSet, ForeignKey


class RelatedFieldNode:
    def __init__(
        self,
        data_model: Datamodel,
        object_types: Set[str],
        path: Optional[Tuple[ForeignKey, ...]] = (),
    ):
        self.data_model = data_model
        self.object_types = object_types

        # relations_out -> { (origin_class_name, prop_name): QueryNode }
        # e.g:          -> (DNSARecord, address): QueryNode[[IPAddressV4]]
        # and:          -> (IPService, service): QueryNode[[Service]]
        self.relations_out: Dict[Tuple[str, str], RelatedFieldNode] = {}

        # relations_in  -> { (foreign_class_name, foreign_prop_name): QueryNode }
        # e.g:          -> (DNSARecord, address, dns_a_records): QueryNode[[DNSARecord]]
        # and:          -> (DNSAAAARecord, address, dns_aaaa_records): QueryNode[[DNSAAAARecord]]
        self.relations_in: Dict[Tuple[str, str, str], RelatedFieldNode] = {}

        self.path = path

    def construct_outgoing_relations(self):
        types = self.object_types
        if "Network" in self.object_types and len(self.path) > 0:  # Don't traverse Network if not root node. TODO: Fix
            types = types - {"Network"}

        # Loop over types in node
        for object_type in types:
            # Merge the relations of all the types in one dict
            for foreign_key in self.data_model.entities[object_type]:
                # Don't traverse the same relation back
                if not self.path or foreign_key != self.path[-1]:
                    self.relations_out[(object_type, foreign_key.attr_name)] = RelatedFieldNode(
                        self.data_model,
                        foreign_key.related_entities,
                        self.path + (foreign_key,),
                    )

    def construct_incoming_relations(self):
        types = self.object_types
        if "Network" in self.object_types and len(self.path) > 0:  # Don't traverse Network if not root node. TODO: Fix
            types = types - {"Network"}

        # Loop all object types
        for (
            foreign_object_type,
            foreign_object_relations,
        ) in self.data_model.entities.items():
            # Loop all attributes
            for foreign_key in foreign_object_relations:
                # Other object points to one of the types in this QueryNode (i.e. sets are NOT disjoint)
                if not foreign_key.related_entities.isdisjoint(types):
                    # Don't traverse the same relation back
                    if not self.path or foreign_key != self.path[-1]:
                        self.relations_in[
                            (
                                foreign_key.source_entity,
                                foreign_key.attr_name,
                                foreign_key.reverse_name,
                            )
                        ] = RelatedFieldNode(
                            self.data_model,
                            {foreign_object_type},
                            self.path + (foreign_key,),
                        )

    def build_tree(self, depth: int):
        if depth > 0:
            self.construct_outgoing_relations()
            for child_node in self.relations_out.values():
                child_node.build_tree(depth - 1)

            self.construct_incoming_relations()
            for child_node in self.relations_in.values():
                child_node.build_tree(depth - 1)

    def generate_field(self, field_set: FieldSet, pk_prefix: str):
        queried_fields = pk_prefix if field_set is FieldSet.ONLY_ID else "*"
        """
        Output dicts in Crux Query Language
        """
        if not self.relations_out and not self.relations_in:
            return f"[{queried_fields}]"

        # Loop outgoing QueryNodes
        fields = [f"{queried_fields}"]
        for key, node in self.relations_out.items():
            cls, attr_name = key
            deeper_fields = node.generate_field(field_set, pk_prefix)
            field_query = "{(:%s/%s {:as %s}) %s}" % (
                cls,
                attr_name,
                attr_name,
                deeper_fields,
            )
            fields.append(field_query)

        # Loop incoming QueryNodes
        for key, node in self.relations_in.items():
            foreign_cls, attr_name, reverse_name = key
            deeper_fields = node.generate_field(field_set, pk_prefix)
            field_query = "{(:%s/_%s {:as %s}) %s}" % (
                foreign_cls,
                attr_name,
                reverse_name,
                deeper_fields,
            )
            fields.append(field_query)

        # Join fields
        return "[{}]".format(" ".join(sorted(fields)))

    def search_nodes(self, search_object_types=Set[str]):
        # Filter outgoing QueryNodes
        self.relations_out = {
            key: node for key, node in self.relations_out.items() if node.search_nodes(search_object_types)
        }

        # Filter incoming QueryNodes
        self.relations_in = {
            key: node for key, node in self.relations_in.items() if node.search_nodes(search_object_types)
        }

        # If any children are still there, remain in tree
        if self.relations_out or self.relations_in:
            return True

        # Match self
        return not self.object_types.isdisjoint(search_object_types)

    def __repr__(self):
        return f"QueryNode[{self}]"

    def __str__(self):
        return ",".join(self.object_types)

    def __eq__(self, other):
        if isinstance(other, RelatedFieldNode):
            return self.object_types == other.object_types
        else:
            return False

    def __hash__(self):
        return hash(self.__repr__())

    def to_dict(self):
        """
        Method to nest dicts for debugging reasons
        """
        d = {}
        if self.relations_out:
            for p, v in self.relations_out.items():
                d[f"{p[0]}/{p[1]}"] = v.to_dict()
        if self.relations_in:
            for p, v in self.relations_in.items():
                d[f"{p[0]}/_{p[1]} as {p[0]}/_{p[1]}"] = v.to_dict()
        return d
