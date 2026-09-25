from ubunye.core.interfaces import Task

from dside_engine.frames import all_numpy_backed

from dside_engine import live
from dside_engine.sources import places_live as pl


class CollectLive(Task):
    def transform(self, sources):
        frames = all_numpy_backed(sources)
        schools = frames["schools"]
        wards, munis = pl.load_wards(), pl.load_munis()
        open_faults, per_ward = live.faults(wards)
        slim = open_faults[["lat", "lng", "suburb", "street", "code", "ward_id", "first_seen", "open_hours"]]
        items = live.news(wards, munis, schools)
        items["published"] = items["published"].astype(str)
        return {"faults": slim, "fault_wards": per_ward, "news": items, "status": live.status()}
