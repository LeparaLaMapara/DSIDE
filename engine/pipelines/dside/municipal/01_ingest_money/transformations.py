from ubunye.core.interfaces import Task

from dside_engine.frames import all_numpy_backed


class IngestMoney(Task):
    """Pass-through: the readers do the fetching; this step lands raw copies."""

    def transform(self, sources):
        return all_numpy_backed(sources)
