from ubunye.core.interfaces import Task

from dside_engine.frames import all_numpy_backed


class Publish(Task):
    def transform(self, sources):
        frames = all_numpy_backed(sources)
        geos = frames["geographies"]
        return {
            "municipalities": frames["municipalities"],
            "projects": frames["projects"],
            "boundaries": geos[["code", "name", "level", "parent", "geometry"]],
            "stations": frames["stations"],
            "schools": frames["schools"],
            "wards": frames["wards"],
            "meta": frames["meta"],
        }
