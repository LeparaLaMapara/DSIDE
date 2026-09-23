from ubunye.core.interfaces import Task


class Publish(Task):
    def transform(self, sources):
        geos = sources["geographies"].native
        return {
            "municipalities": sources["municipalities"].native,
            "projects": sources["projects"].native,
            "boundaries": geos[["code", "name", "level", "parent", "geometry"]],
            "stations": sources["stations"].native,
            "wards": sources["wards"].native,
            "meta": sources["meta"].native,
        }
