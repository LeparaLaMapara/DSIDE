'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import type { MunicipalityWithStats, FeatureLoading } from '@/types';

interface PCABiplotProps {
  municipalities: MunicipalityWithStats[];
  featureLoadings: FeatureLoading[];
  onMunicipalityClick?: (munCode: string) => void;
}

const CLUSTER_COLORS: Record<number, string> = {
  1: '#007A4D', // High Performing - green
  2: '#FFB612', // Developing - gold
  3: '#ea8c3f', // Challenged - orange
  4: '#DE3831', // Critical - red
};

const CLUSTER_LABELS: Record<number, string> = {
  1: 'High Performing',
  2: 'Developing',
  3: 'Challenged',
  4: 'Critical',
};

const FEATURE_CATEGORY_COLORS: Record<string, string> = {
  employment: '#002395',
  finance: '#007A4D',
  service_delivery: '#FFB612',
  demographics: '#9333ea',
  default: '#64748b',
};

export default function PCABiplot({
  municipalities,
  featureLoadings,
  onMunicipalityClick,
}: PCABiplotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Responsive resize
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setDimensions({ width: Math.max(400, width), height: Math.max(400, Math.min(600, width * 0.75)) });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // D3 rendering
  const renderBiplot = useCallback(() => {
    if (!svgRef.current || municipalities.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;
    const margin = { top: 30, right: 30, bottom: 50, left: 60 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;

    // Scales
    const xExtent = d3.extent(municipalities, (d) => d.pc1) as [number, number];
    const yExtent = d3.extent(municipalities, (d) => d.pc2) as [number, number];
    const xPadding = (xExtent[1] - xExtent[0]) * 0.15 || 1;
    const yPadding = (yExtent[1] - yExtent[0]) * 0.15 || 1;

    const xScale = d3
      .scaleLinear()
      .domain([xExtent[0] - xPadding, xExtent[1] + xPadding])
      .range([0, plotWidth]);

    const yScale = d3
      .scaleLinear()
      .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
      .range([plotHeight, 0]);

    const popExtent = d3.extent(municipalities, (d) => d.population) as [number, number];
    const rScale = d3.scaleSqrt().domain(popExtent).range([3, 18]);

    // Create main group with zoom
    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 8])
      .on('zoom', (event) => {
        plotGroup.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Background for zoom reset on double-click
    g.append('rect')
      .attr('width', plotWidth)
      .attr('height', plotHeight)
      .attr('fill', 'transparent')
      .attr('cursor', 'move');

    const plotGroup = g.append('g');

    // Grid lines
    const xAxis = d3.axisBottom(xScale).ticks(8).tickSize(-plotHeight).tickFormat(() => '');
    const yAxis = d3.axisLeft(yScale).ticks(6).tickSize(-plotWidth).tickFormat(() => '');

    plotGroup
      .append('g')
      .attr('transform', `translate(0,${plotHeight})`)
      .call(xAxis)
      .selectAll('line')
      .attr('stroke', '#e2e8f0')
      .attr('stroke-dasharray', '2,2');

    plotGroup
      .append('g')
      .call(yAxis)
      .selectAll('line')
      .attr('stroke', '#e2e8f0')
      .attr('stroke-dasharray', '2,2');

    // Remove tick domain lines
    plotGroup.selectAll('.domain').attr('stroke', '#cbd5e1');

    // Zero lines
    plotGroup
      .append('line')
      .attr('x1', xScale(0))
      .attr('y1', 0)
      .attr('x2', xScale(0))
      .attr('y2', plotHeight)
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4');

    plotGroup
      .append('line')
      .attr('x1', 0)
      .attr('y1', yScale(0))
      .attr('x2', plotWidth)
      .attr('y2', yScale(0))
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4');

    // Feature loading arrows
    if (featureLoadings.length > 0) {
      const arrowScale = Math.min(plotWidth, plotHeight) * 0.35;
      const arrowGroup = plotGroup.append('g').attr('class', 'arrows');

      // Arrow head marker
      svg
        .append('defs')
        .selectAll('marker')
        .data(Object.entries(FEATURE_CATEGORY_COLORS))
        .enter()
        .append('marker')
        .attr('id', ([cat]) => `arrow-${cat}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 8)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', ([, color]) => color);

      featureLoadings.forEach((fl) => {
        const x = xScale(0) + fl.pc1 * arrowScale;
        const y = yScale(0) - fl.pc2 * arrowScale;
        const color = FEATURE_CATEGORY_COLORS[fl.category] || FEATURE_CATEGORY_COLORS.default;

        arrowGroup
          .append('line')
          .attr('x1', xScale(0))
          .attr('y1', yScale(0))
          .attr('x2', x)
          .attr('y2', y)
          .attr('stroke', color)
          .attr('stroke-width', 2)
          .attr('opacity', 0.7)
          .attr('marker-end', `url(#arrow-${fl.category || 'default'})`);

        // Label
        const labelX = x + (fl.pc1 > 0 ? 6 : -6);
        const labelY = y + (fl.pc2 > 0 ? -6 : 10);

        arrowGroup
          .append('text')
          .attr('x', labelX)
          .attr('y', labelY)
          .attr('text-anchor', fl.pc1 > 0 ? 'start' : 'end')
          .attr('font-size', '10px')
          .attr('font-weight', '600')
          .attr('fill', color)
          .attr('opacity', 0.85)
          .text(fl.feature.replace(/_/g, ' '));
      });
    }

    // Municipality dots
    const tooltip = d3.select(tooltipRef.current);

    plotGroup
      .selectAll('circle.municipality')
      .data(municipalities)
      .enter()
      .append('circle')
      .attr('class', 'municipality')
      .attr('cx', (d) => xScale(d.pc1))
      .attr('cy', (d) => yScale(d.pc2))
      .attr('r', (d) => rScale(d.population))
      .attr('fill', (d) => CLUSTER_COLORS[d.cluster] || '#64748b')
      .attr('fill-opacity', 0.7)
      .attr('stroke', (d) => CLUSTER_COLORS[d.cluster] || '#64748b')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.9)
      .attr('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('r', rScale(d.population) * 1.4)
          .attr('fill-opacity', 0.95)
          .attr('stroke-width', 2.5);

        tooltip
          .style('display', 'block')
          .style('left', `${event.offsetX + 12}px`)
          .style('top', `${event.offsetY - 12}px`)
          .html(
            `<div class="text-sm">
              <strong>${d.mun_name}</strong>
              <div class="text-xs text-slate-500">${d.province}</div>
              <div class="text-xs mt-1">
                <span style="color:${CLUSTER_COLORS[d.cluster]}">
                  ${CLUSTER_LABELS[d.cluster] || `Cluster ${d.cluster}`}
                </span>
              </div>
              <div class="text-xs text-slate-600 mt-1">
                Unemployment: ${d.youth_unemployment_rate.toFixed(1)}%<br/>
                Service Delivery: ${d.service_delivery_score.toFixed(0)}%<br/>
                Population: ${d.population.toLocaleString('en-ZA')}
              </div>
            </div>`
          );
      })
      .on('mouseout', function (_, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('r', rScale(d.population))
          .attr('fill-opacity', 0.7)
          .attr('stroke-width', 1.5);

        tooltip.style('display', 'none');
      })
      .on('click', (_, d) => {
        if (onMunicipalityClick) {
          onMunicipalityClick(d.mun_code);
        }
      });

    // Axis labels
    g.append('text')
      .attr('x', plotWidth / 2)
      .attr('y', plotHeight + margin.bottom - 10)
      .attr('text-anchor', 'middle')
      .attr('font-size', '13px')
      .attr('font-weight', '500')
      .attr('fill', '#64748b')
      .text('PC1');

    g.append('text')
      .attr('x', -plotHeight / 2)
      .attr('y', -margin.left + 16)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90)')
      .attr('font-size', '13px')
      .attr('font-weight', '500')
      .attr('fill', '#64748b')
      .text('PC2');
  }, [municipalities, featureLoadings, dimensions, onMunicipalityClick]);

  useEffect(() => {
    renderBiplot();
  }, [renderBiplot]);

  return (
    <div ref={containerRef} className="relative w-full" role="img" aria-label="PCA biplot showing municipality clusters">
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="w-full"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        preserveAspectRatio="xMidYMid meet"
      />
      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className="absolute pointer-events-none bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 shadow-lg z-20"
        style={{ display: 'none' }}
      />

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 mt-4">
        {Object.entries(CLUSTER_LABELS).map(([cluster, label]) => (
          <div key={cluster} className="flex items-center gap-1.5 text-xs">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CLUSTER_COLORS[Number(cluster)] }}
            />
            <span className={cn('text-slate-600 dark:text-slate-400')}>
              {label}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-slate-400 ml-4">
          <div className="w-2 h-2 rounded-full bg-slate-400" />
          <span>Small pop.</span>
          <div className="w-4 h-4 rounded-full bg-slate-400 ml-1" />
          <span>Large pop.</span>
        </div>
      </div>
    </div>
  );
}
