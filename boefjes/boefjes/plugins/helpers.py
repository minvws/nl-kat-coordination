import io
import logging
import os
import tarfile
from typing import ByteString, Generator, Union

import docker


class TarStream(io.RawIOBase):
    """Wrapper around generator to feed tarfile.

    Based on:
    - https://stackoverflow.com/questions/39155958/how-do-i-read-a-tarfile-from-a-generator
    - https://stackoverflow.com/questions/6657820/how-to-convert-an-iterable-to-a-stream/6658949
    """

    def __init__(self, stream: Generator):
        """Store the generator in the TarStream class."""
        self.bytes_left = None
        self.stream = stream
        self.able_to_read = bool(stream)
        super().__init__()

    def reader(self) -> io.BufferedReader:
        """Return the bufferedreader for this TarStream."""
        return io.BufferedReader(self)

    def readable(self) -> bool:
        """Returns whether the generator stream is (still) readable."""
        return self.able_to_read

    def readinto(self, memory_view: ByteString) -> int:
        """Read the generator. Returns 0 when done. Output is stored in memory_view."""
        try:
            chunk = self.bytes_left or next(self.stream)
        except StopIteration:
            self.able_to_read = False
            return 0
        view_len = len(memory_view)
        output, self.bytes_left = chunk[:view_len], chunk[view_len:]
        outlen = len(output)
        memory_view[:outlen] = output
        return outlen


def get_file_from_container(container: docker.models.containers.Container, path: str) -> Union[bytes, None]:
    """Returns a file from a docker container."""
    try:
        stream, _ = container.get_archive(path)
    except docker.errors.NotFound:
        logging.warning(
            "%s not found in container %s %s",
            path,
            container.short_id,
            container.image.tags,
        )
        return None

    f = tarfile.open(mode="r|", fileobj=TarStream(stream).reader())
    tarobject = f.next()
    if tarobject.name == os.path.basename(path):
        return f.extractfile(tarobject).read()
