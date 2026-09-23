import json

import pandas as pd
from ubunye.core.interfaces import Task

from dside_engine.build import analyse


class Analyse(Task):
    def transform(self, sources):
        raw = {name: frame.native for name, frame in sources.items()}
        out = analyse(raw)
        # Parquet cannot hold ragged nested lists; carry them as JSON text.
        munis = out["municipalities"].copy()
        for col in munis.columns:
            if munis[col].map(lambda v: isinstance(v, (list, dict))).any():
                munis[col] = munis[col].map(json.dumps)
        out["municipalities"] = munis
        for name in ("stations", "wards"):
            frame = out[name].copy()
            for col in frame.columns:
                if frame[col].map(lambda v: isinstance(v, (list, dict))).any():
                    frame[col] = frame[col].map(json.dumps)
            out[name] = frame
        return out
