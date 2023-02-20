from graphql import GraphQLList


def test_complete_schema(schema_loader):

    assert (
        schema_loader.complete_schema.origin_type.fields["results"].type.of_type.of_type
        == schema_loader.complete_schema.ooi_union_type
    )

    ooi_types_names = {type_.name for type_ in schema_loader.complete_schema.ooi_union_type.types}
    assert "Animal" in ooi_types_names
    assert "ZooKeeper" in ooi_types_names


def test_api_schema(schema_loader):
    assert (
        schema_loader.api_schema.query_type.fields["Animal"].type.of_type
        == schema_loader.api_schema.schema.type_map["Animal"]
    )


def test_backlink_in_api_schema(schema_loader):
    backlink = schema_loader.api_schema.get_object_type("Animal").fields["zookeepers"].type
    assert isinstance(backlink, GraphQLList)
    assert backlink.of_type == schema_loader.api_schema.schema.type_map["ZooKeeper"]
