from octopoes.bad import wrong  # noqa


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:  # noqa
    network = Network(name=raw.decode())  # noqa

    yield network  # noqa
