from ubunye.core.interfaces import Task


class IngestPeople(Task):
    """Pass-through: the readers do the fetching; this step lands raw copies."""

    def transform(self, sources):
        return {name: frame.native for name, frame in sources.items()}
