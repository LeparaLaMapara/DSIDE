from ubunye.core.interfaces import Task


class IngestFresh(Task):
    """Pass-through: the catalogue readers fetch; this step lands raw copies."""

    def transform(self, sources):
        return {name: frame.native for name, frame in sources.items()}
