from ubunye.core.interfaces import Task

from dside_engine.frames import all_numpy_backed


class IngestFresh(Task):
    """Pass-through: the catalogue readers fetch; this step lands raw copies."""

    def transform(self, sources):
        return all_numpy_backed(sources)
