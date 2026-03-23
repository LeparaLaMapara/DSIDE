'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import type { Layer, PathOptions } from 'leaflet';
import type { Feature, Geometry } from 'geojson';
import { getUnemploymentColor, getScoreColor, formatNumber } from '@/lib/utils';
import type { MunicipalityWithStats } from '@/types';

// GeoJSON source for SA municipal boundaries
const GEOJSON_URL =
  'https://raw.githubusercontent.com/nicholasgasior/gisdata/master/south-africa/municipalities.geojson';

type ColorMetric = 'unemployment' | 'service_delivery' | 'neet';

interface MunicipalMapProps {
  municipalities: MunicipalityWithStats[];
  colorMetric: ColorMetric;
  selectedProvince?: string | null;
  onMunicipalityClick?: (munCode: string) => void;
}

interface GeoJSONProperties {
  name?: string;
  NAME_2?: string;
  CAT_B?: string;
  [key: string]: unknown;
}

/** Fit map bounds to the displayed GeoJSON */
function FitBounds({ geoJson }: { geoJson: GeoJSON.FeatureCollection | null }) {
  const map = useMap();
  useEffect(() => {
    if (!geoJson || geoJson.features.length === 0) return;
    // Default SA bounds
    map.fitBounds([[-35, 16], [-22, 33]]);
  }, [map, geoJson]);
  return null;
}

export default function MunicipalMap({
  municipalities,
  colorMetric,
  selectedProvince,
  onMunicipalityClick,
}: MunicipalMapProps) {
  const [geoJson, setGeoJson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Build a lookup map by municipality name
  const munLookup = useMemo(() => {
    const map = new Map<string, MunicipalityWithStats>();
    municipalities.forEach((m) => {
      map.set(m.mun_name.toLowerCase(), m);
      map.set(m.mun_code.toLowerCase(), m);
    });
    return map;
  }, [municipalities]);

  // Fetch GeoJSON
  useEffect(() => {
    let cancelled = false;
    async function fetchGeoJSON() {
      try {
        setLoading(true);
        const res = await fetch(GEOJSON_URL);
        if (!res.ok) throw new Error('Failed to fetch GeoJSON');
        const data = await res.json();
        if (!cancelled) {
          setGeoJson(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError('Could not load map boundaries. Using marker fallback.');
          console.error('GeoJSON fetch error:', err);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchGeoJSON();
    return () => { cancelled = true; };
  }, []);

  // Match GeoJSON feature to municipality data
  const findMunicipality = useCallback(
    (feature: Feature<Geometry, GeoJSONProperties>): MunicipalityWithStats | undefined => {
      const props = feature.properties;
      if (!props) return undefined;
      const name = (props.name || props.NAME_2 || props.CAT_B || '').toLowerCase();
      return munLookup.get(name);
    },
    [munLookup]
  );

  // Get the metric value for coloring
  const getMetricValue = useCallback(
    (mun: MunicipalityWithStats): number => {
      switch (colorMetric) {
        case 'unemployment':
          return mun.youth_unemployment_rate;
        case 'service_delivery':
          return mun.service_delivery_score;
        case 'neet':
          return mun.neet_rate;
        default:
          return mun.youth_unemployment_rate;
      }
    },
    [colorMetric]
  );

  // Style each GeoJSON feature
  const style = useCallback(
    (feature?: Feature<Geometry, GeoJSONProperties>): PathOptions => {
      if (!feature) return { fillColor: '#e2e8f0', weight: 1, opacity: 0.7, color: '#94a3b8', fillOpacity: 0.6 };

      const mun = findMunicipality(feature);
      if (!mun) {
        return { fillColor: '#e2e8f0', weight: 1, opacity: 0.7, color: '#94a3b8', fillOpacity: 0.3 };
      }

      // If province filter active, dim non-matching municipalities
      if (selectedProvince && mun.province !== selectedProvince) {
        return { fillColor: '#e2e8f0', weight: 0.5, opacity: 0.3, color: '#cbd5e1', fillOpacity: 0.15 };
      }

      const value = getMetricValue(mun);
      let fillColor: string;

      if (colorMetric === 'service_delivery') {
        fillColor = getScoreColor(value);
      } else {
        fillColor = getUnemploymentColor(value);
      }

      return {
        fillColor,
        weight: 1.5,
        opacity: 0.8,
        color: '#475569',
        fillOpacity: 0.7,
      };
    },
    [findMunicipality, getMetricValue, colorMetric, selectedProvince]
  );

  // Handle feature interactions
  const onEachFeature = useCallback(
    (feature: Feature<Geometry, GeoJSONProperties>, layer: Layer) => {
      const mun = findMunicipality(feature);

      if (mun) {
        const metricLabel =
          colorMetric === 'unemployment'
            ? 'Youth Unemployment'
            : colorMetric === 'service_delivery'
              ? 'Service Delivery'
              : 'NEET Rate';
        const metricValue = getMetricValue(mun);
        const profileLabels: Record<number, string> = {
          1: 'High Performing',
          2: 'Developing',
          3: 'Challenged',
          4: 'Critical',
        };

        layer.bindTooltip(
          `<div class="text-sm">
            <strong>${mun.mun_name}</strong><br/>
            <span class="text-xs text-slate-500">${mun.province} | ${mun.district}</span><br/>
            <span>${metricLabel}: <strong>${metricValue.toFixed(1)}%</strong></span><br/>
            <span>Profile: ${profileLabels[mun.profile] || 'Unknown'}</span><br/>
            <span>Pop: ${formatNumber(mun.population)}</span>
          </div>`,
          { sticky: true, className: 'leaflet-tooltip-custom' }
        );

        layer.on({
          mouseover: (e) => {
            const target = e.target;
            target.setStyle({ weight: 3, color: '#002395', fillOpacity: 0.85 });
            target.bringToFront();
          },
          mouseout: (e) => {
            const target = e.target;
            target.setStyle(style(feature));
          },
          click: () => {
            if (onMunicipalityClick) {
              onMunicipalityClick(mun.mun_code);
            }
          },
        });
      }
    },
    [findMunicipality, getMetricValue, colorMetric, style, onMunicipalityClick]
  );

  // Unique key for GeoJSON re-render
  const geoJsonKey = `${colorMetric}-${selectedProvince || 'all'}-${municipalities.length}`;

  if (loading) {
    return (
      <div className="map-container flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-500 mt-3">Loading map boundaries...</p>
        </div>
      </div>
    );
  }

  if (error && !geoJson) {
    return (
      <div className="map-container flex items-center justify-center">
        <p className="text-sm text-slate-500">{error}</p>
      </div>
    );
  }

  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const tileUrl = mapboxToken
    ? `https://api.mapbox.com/styles/v1/mapbox/light-v11/tiles/{z}/{x}/{y}?access_token=${mapboxToken}`
    : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  const tileAttribution = mapboxToken
    ? '&copy; <a href="https://www.mapbox.com/">Mapbox</a>'
    : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  return (
    <div className="map-container" role="img" aria-label="South Africa municipality map colored by selected metric">
      <MapContainer
        center={[-29, 25]}
        zoom={5}
        scrollWheelZoom
        style={{ height: '100%', width: '100%' }}
        className="rounded-lg"
      >
        <TileLayer url={tileUrl} attribution={tileAttribution} />
        {geoJson && (
          <GeoJSON
            key={geoJsonKey}
            data={geoJson}
            style={style}
            onEachFeature={onEachFeature}
          />
        )}
        <FitBounds geoJson={geoJson} />
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 shadow-md border border-slate-200 dark:border-slate-700">
        <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
          {colorMetric === 'unemployment'
            ? 'Youth Unemployment Rate'
            : colorMetric === 'service_delivery'
              ? 'Service Delivery Score'
              : 'NEET Rate'}
        </p>
        {colorMetric === 'service_delivery' ? (
          <div className="flex items-center gap-1 text-[10px] text-slate-500">
            <div className="w-6 h-3 rounded-sm" style={{ backgroundColor: '#DE3831' }} />
            <span>Low</span>
            <div className="w-6 h-3 rounded-sm ml-1" style={{ backgroundColor: '#FFB612' }} />
            <span>Med</span>
            <div className="w-6 h-3 rounded-sm ml-1" style={{ backgroundColor: '#007A4D' }} />
            <span>High</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-[10px] text-slate-500">
            <div className="w-6 h-3 rounded-sm" style={{ backgroundColor: '#007A4D' }} />
            <span>Low</span>
            <div className="w-6 h-3 rounded-sm ml-1" style={{ backgroundColor: '#FFB612' }} />
            <span>Med</span>
            <div className="w-6 h-3 rounded-sm ml-1" style={{ backgroundColor: '#DE3831' }} />
            <span>High</span>
          </div>
        )}
      </div>
    </div>
  );
}
