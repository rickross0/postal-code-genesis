import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Marker, Polygon, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  listZones, updateZone, autoCreateAllZones, createZoneManual, listDistricts,
  deleteZone, listRegions, createRegion, updateRegion, deleteRegion, autoCreateRegions, deleteAllRegions,
  createDistrict, updateDistrict, deleteDistrict, autoCreateDistricts, updateCountryBoundary,
  saveSnapshot, listSnapshots, restoreSnapshot, splitZone,
} from '../services/api';

const ZONE_COLORS = [
  '#e6194b','#3cb44b','#ffe119','#4363d8','#f58231',
  '#911eb4','#42d4f4','#f032e6','#bfef45','#fabed4',
  '#469990','#dcbeff','#9A6324','#fffac8','#800000',
  '#aaffc3','#808000','#ffd8b1','#000075','#a9a9a9',
];

const getZoneColor = (zone) => zone?.color || ZONE_COLORS[(zone?.id || 0) % ZONE_COLORS.length];
const isHidden = (map, type, id) => !!map[`${type}-${id}`];

const REGION_COLORS = ['#6c63ff','#ff6b6b','#51cf66','#ffd43b','#339af0','#f06595'];

const styles = {
  container: { flex: 1, display: 'flex', flexDirection: 'column', height: '100vh' },
  toolbar: { padding: '10px 16px', background: '#fff', borderBottom: '1px solid #e8e8f0', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' },
  mapWrap: { flex: 1, position: 'relative', background: '#f0f0f5', overflow: 'hidden' },
  btn: { padding: '6px 14px', background: '#6c63ff', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnS: { padding: '6px 14px', background: '#f0f0f5', color: '#333', border: '1px solid #ddd', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnD: { padding: '6px 14px', background: '#ff6b6b', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnG: { padding: '6px 14px', background: '#51cf66', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  btnO: { padding: '6px 14px', background: '#ff922b', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  bar: { position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 2000, background: '#fff', padding: '10px 18px', borderRadius: 10, boxShadow: '0 2px 16px rgba(0,0,0,.18)', display: 'flex', gap: 10, alignItems: 'center' },
  info: { position: 'absolute', bottom: 20, right: 20, background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 4px 20px rgba(0,0,0,.15)', maxWidth: 320, zIndex: 1000, fontSize: '13px' },
  legend: { position: 'absolute', top: 20, left: 20, background: '#fff', borderRadius: 10, padding: 12, boxShadow: '0 2px 12px rgba(0,0,0,.12)', maxWidth: 240, zIndex: 1000, fontSize: '12px', maxHeight: '50vh', overflowY: 'auto' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 16, textAlign: 'center', padding: 40 },
};

function FitBounds({ zones, cid }) {
  const map = useMap();
  const last = useRef(null);
  useEffect(() => {
    if (!zones.length) return;
    if (last.current === cid) return;
    last.current = cid;
    const v = zones.filter(z => z.center_lat && z.center_lng);
    if (!v.length) return;
    const b = L.latLngBounds(v.map(z => [z.center_lat, z.center_lng]));
    if (b.isValid()) map.fitBounds(b, { padding: [60, 60] });
  }, [zones, map, cid]);
  return null;
}

function ClickH({ onClick }) { useMapEvents({ click: onClick }); return null; }

function MapRef({ onReady }) {
  const map = useMap();
  useEffect(() => { onReady(map); }, [map, onReady]);
  return null;
}

function useMapScreenshot() {
  const capture = async (element) => {
    if (!element) return null;
    const canvas = await html2canvas(element, {
      useCORS: true,
      allowTaint: true,
      scale: 2,
      logging: false,
      backgroundColor: '#f0f0f5',
    });
    return canvas.toDataURL('image/png');
  };
  return { capture };
}

export default function ZoneMap({ selectedCountry, onCountryUpdated }) {
  const [zones, setZones] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [regions, setRegions] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [selDistrict, setSelDistrict] = useState(null);
  const [selRegion, setSelRegion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [drawPoints, setDrawPoints] = useState([]);
  const [drawTarget, setDrawTarget] = useState(null); // 'zone','region','district','country'
  const [editItem, setEditItem] = useState(null);
  const [saving, setSaving] = useState(false);
  const [movingZone, setMovingZone] = useState(null);
  const [editingName, setEditingName] = useState(null); // { type, id, value }
  const [hiddenMap, setHiddenMap] = useState({}); // { "z-1": true, "d-2": true, "r-3": true }
  const [countryHidden, setCountryHidden] = useState(false);
  const [undoableRegions, setUndoableRegions] = useState(false);
  const [undoableDistricts, setUndoableDistricts] = useState({}); // { regionId: snapshotId }
  const [nameModalOpen, setNameModalOpen] = useState(false);
  const [nameModalType, setNameModalType] = useState(null); // 'region', 'district'
  const [nameModalTarget, setNameModalTarget] = useState(null); // regionId for district, or callback context
  const [customName, setCustomName] = useState('');
  const [selectedPresetName, setSelectedPresetName] = useState('');

  const PREDEFINED_REGION_NAMES = useMemo(() => [
    'Northern Bahr el Ghazal', 'Western Bahr el Ghazal', 'Lakes', 'Warrap',
    'Western Equatoria', 'Central Equatoria', 'Eastern Equatoria',
    'Jonglei', 'Unity', 'Upper Nile',
    'Abyei Area', 'Greater Pibor Area', 'Ruweng Area',
  ], []);

  const PREDEFINED_DISTRICT_NAMES = useMemo(() => [
    'Aweil', 'Wau', 'Rumbek', 'Kuajok', 'Yambio', 'Juba', 'Torit',
    'Bor', 'Bentiu', 'Malakal', 'Abyei', 'Pibor', 'Pariang',
    'Yirol', 'Cueibet', 'Wanjok', 'Mundri', 'Maridi', 'Yei', 'Terekeka',
    'Renk', 'Melut', 'Maban', 'Nasir', 'Maiwut', 'Kodok', 'Panriang',
    'Waat', 'Ayod', 'Akobo', 'Leer', 'Mayom',
  ], []);
  const [snapshots, setSnapshots] = useState([]);
  const [showSnapshots, setShowSnapshots] = useState(false);
  const [snapshotsVisible, setSnapshotsVisible] = useState(true);
  const [snapshotsPos, setSnapshotsPos] = useState('tl'); // 'tl','tr','bl','br'
  const [reportMode, setReportMode] = useState(false);
  const [selectedReportItems, setSelectedReportItems] = useState(new Set());
  const [generatingReport, setGeneratingReport] = useState(false);
  const mapWrapRef = useRef(null);
  const [mapInstance, setMapInstance] = useState(null);

  const { capture: captureMap } = useMapScreenshot();

  const zoomToFeature = useCallback((type, id) => {
    if (!mapInstance) return;
    let bounds = null;
    if (type === 'zone') {
      const z = zones.find(x => x.id === id);
      if (z) {
        if (z.boundary_geojson) {
          bounds = L.geoJSON(z.boundary_geojson).getBounds();
        } else if (z.center_lat != null && z.center_lng != null) {
          bounds = L.latLngBounds([[z.center_lat - 0.01, z.center_lng - 0.01], [z.center_lat + 0.01, z.center_lng + 0.01]]);
        }
      }
    } else if (type === 'district') {
      const d = districts.find(x => x.id === id);
      if (d && d.boundary_geojson) {
        bounds = L.geoJSON(d.boundary_geojson).getBounds();
      }
    } else if (type === 'region') {
      const r = regions.find(x => x.id === id);
      if (r && r.boundary_geojson) {
        bounds = L.geoJSON(r.boundary_geojson).getBounds();
      }
    }
    if (bounds && bounds.isValid()) {
      mapInstance.fitBounds(bounds, { padding: [60, 60], maxZoom: 16 });
    }
  }, [mapInstance, zones, districts, regions]);

  const zoomToReportItems = useCallback(() => {
    if (!mapInstance) return;
    const points = [];
    selectedReportItems.forEach(key => {
      const [type, idStr] = key.split('-');
      const id = parseInt(idStr, 10);
      if (type === 'zone') {
        const z = zones.find(x => x.id === id);
        if (z) {
          if (z.boundary_geojson) {
            const b = L.geoJSON(z.boundary_geojson).getBounds();
            if (b.isValid()) { points.push(b.getSouthWest(), b.getNorthEast()); }
          } else if (z.center_lat != null && z.center_lng != null) {
            points.push([z.center_lat, z.center_lng]);
          }
        }
      } else if (type === 'district') {
        const d = districts.find(x => x.id === id);
        if (d && d.boundary_geojson) {
          const b = L.geoJSON(d.boundary_geojson).getBounds();
          if (b.isValid()) { points.push(b.getSouthWest(), b.getNorthEast()); }
        }
      } else if (type === 'region') {
        const r = regions.find(x => x.id === id);
        if (r && r.boundary_geojson) {
          const b = L.geoJSON(r.boundary_geojson).getBounds();
          if (b.isValid()) { points.push(b.getSouthWest(), b.getNorthEast()); }
        }
      }
    });
    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      if (bounds.isValid()) mapInstance.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
  }, [mapInstance, selectedReportItems, zones, districts, regions]);

  const toggleReportItem = useCallback((type, id) => {
    setSelectedReportItems(prev => {
      const key = `${type}-${id}`;
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const isReportSelected = (type, id) => selectedReportItems.has(`${type}-${id}`);

  const clearReportSelection = useCallback(() => setSelectedReportItems(new Set()), []);

  const handleScreenshot = useCallback(async () => {
    if (!mapWrapRef.current) return;
    try {
      setGeneratingReport(true);
      // Center map on selected/report features before capture; don't zoom out if nothing selected
      if (mapInstance) {
        if (reportMode && selectedReportItems.size > 0) {
          zoomToReportItems();
          await new Promise(r => setTimeout(r, 900)); // let tiles load after pan/zoom
        } else if (selectedZone) {
          zoomToFeature('zone', selectedZone.id);
          await new Promise(r => setTimeout(r, 700));
        } else if (selDistrict) {
          zoomToFeature('district', selDistrict);
          await new Promise(r => setTimeout(r, 700));
        } else if (selRegion) {
          zoomToFeature('region', selRegion);
          await new Promise(r => setTimeout(r, 700));
        }
        // If nothing is selected, capture the current view without zooming out
      }
      const dataUrl = await captureMap(mapWrapRef.current);
      // Add branding header/footer
      const brandedUrl = await new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          const padTop = 42;
          const padBottom = 38;
          const canvas = document.createElement('canvas');
          canvas.width = img.width;
          canvas.height = img.height + padTop + padBottom;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#f8f9fa';
          ctx.fillRect(0, 0, canvas.width, padTop);
          ctx.fillRect(0, img.height + padTop, canvas.width, padBottom);
          ctx.drawImage(img, 0, padTop);
          ctx.fillStyle = '#1a1a2e';
          ctx.font = 'bold 16px system-ui, -apple-system, Segoe UI, sans-serif';
          ctx.textBaseline = 'middle';
          ctx.textAlign = 'left';
          ctx.fillText(`📍 ${selectedCountry?.name || 'Map'} — PostalCode Genesis`, 16, padTop / 2);
          ctx.fillStyle = '#888';
          ctx.font = '12px system-ui, -apple-system, Segoe UI, sans-serif';
          ctx.textAlign = 'right';
          ctx.fillText(new Date().toLocaleString(), canvas.width - 16, padTop / 2);
          ctx.fillStyle = '#6c63ff';
          ctx.font = 'bold 13px system-ui, -apple-system, Segoe UI, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('Generated by PostalCode Genesis', canvas.width / 2, img.height + padTop + padBottom / 2);
          resolve(canvas.toDataURL('image/png'));
        };
        img.src = dataUrl;
      });
      const link = document.createElement('a');
      link.href = brandedUrl;
      link.download = `${selectedCountry?.name || 'map'}-screenshot-${new Date().toISOString().slice(0,10)}.png`;
      link.click();
    } catch (e) { console.error('Screenshot failed:', e); alert('Screenshot failed'); }
    finally { setGeneratingReport(false); }
  }, [captureMap, selectedCountry, mapInstance, zones, regions, districts, hiddenMap]);

  const estimateCost = useCallback((area_sq_km, population) => {
    // Rough implementation cost estimate
    // Infrastructure: $3,400 per km²
    // Population services: $3.5 per person
    const area = parseFloat(area_sq_km) || 0;
    const pop = parseInt(population) || 0;
    const infrastructure = area * 3400;
    const services = pop * 3.5;
    const total = infrastructure + services;
    return {
      infrastructure,
      services,
      total,
      formatted: total > 0 ? `$${total.toLocaleString(undefined, {maximumFractionDigits: 0})}` : 'N/A',
      breakdown: `Infrastructure: $${infrastructure.toLocaleString(undefined, {maximumFractionDigits: 0})} | Services: $${services.toLocaleString(undefined, {maximumFractionDigits: 0})}`
    };
  }, []);

  const buildReportData = useCallback(() => {
    const items = [];
    selectedReportItems.forEach(key => {
      const [type, idStr] = key.split('-');
      const id = parseInt(idStr, 10);
      if (type === 'region') {
        const r = regions.find(x => x.id === id);
        if (r) {
          const ds = districts.filter(d => d.region_id === id);
          const zs = zones.filter(z => ds.some(d => d.id === z.district_id));
          items.push({ type: 'region', data: r, districts: ds, zones: zs });
        }
      } else if (type === 'district') {
        const d = districts.find(x => x.id === id);
        if (d) {
          const zs = zones.filter(z => z.district_id === id);
          items.push({ type: 'district', data: d, zones: zs });
        }
      } else if (type === 'zone') {
        const z = zones.find(x => x.id === id);
        if (z) items.push({ type: 'zone', data: z });
      }
    });
    return items;
  }, [selectedReportItems, regions, districts, zones]);

  const handleGenerateProposalPDF = useCallback(async () => {
    if (!selectedCountry) return;
    try {
      setGeneratingReport(true);
      const doc = new jsPDF({ unit: 'mm', format: 'a4' });
      const pageW = doc.internal.pageSize.getWidth();
      const pageH = doc.internal.pageSize.getHeight();
      const margin = 14;

      // Cover
      doc.setFontSize(26);
      doc.setTextColor(108, 99, 255);
      doc.text('Postal Code Genesis', pageW / 2, 45, { align: 'center' });
      doc.setFontSize(18);
      doc.setTextColor(26, 26, 46);
      doc.text('Product Proposal', pageW / 2, 58, { align: 'center' });
      doc.setFontSize(12);
      doc.setTextColor(100, 100, 100);
      doc.text(`Prepared for: ${selectedCountry.name || 'National Government'}`, pageW / 2, 72, { align: 'center' });
      doc.text(`Date: ${new Date().toLocaleDateString()}`, pageW / 2, 80, { align: 'center' });

      // Value proposition
      const vpY = 95;
      doc.setFillColor(248, 249, 255);
      doc.roundedRect(margin, vpY, pageW - margin * 2, 48, 4, 4, 'F');
      doc.setFontSize(12);
      doc.setTextColor(26, 26, 46);
      doc.text('Why Postal Code Genesis?', margin + 6, vpY + 10);
      doc.setFontSize(9);
      doc.setTextColor(80, 80, 80);
      const vpLines = [
        '• Purpose-built for nations without existing postal infrastructure — no legacy system dependencies.',
        '• Combines GIS mapping, boundary drawing, postal code assignment, and policy generation in one platform.',
        '• 25% more affordable than international alternatives (Esri, Smarty, UPU consultancy) at national scale.',
        '• Supports multi-level administration: regions → districts → zones, with automatic code generation.',
        '• Full snapshot/rollback capability — experiment safely, revert mistakes instantly.',
        '• Export-ready for UN, UPU, and international postal compliance standards.',
      ];
      vpLines.forEach((line, i) => doc.text(line, margin + 6, vpY + 18 + i * 5));

      // Pricing
      doc.addPage();
      doc.setFontSize(18);
      doc.setTextColor(26, 26, 46);
      doc.text('Software License Pricing', margin, 24);
      doc.setFontSize(10);
      doc.setTextColor(120, 120, 120);
      doc.text('25% cheaper than international addressing systems at national scale', margin, 32);

      const plans = [
        { name: '1-Year Plan', price: 18900, benchmark: 25200 },
        { name: '2-Year Plan', price: 33900, benchmark: 45300 },
        { name: '20-Year Membership', price: 338000, benchmark: 451000 },
      ];
      const licBody = plans.map(p => {
        const save = p.benchmark - p.price;
        const pct = Math.round((save / p.benchmark) * 100);
        return [p.name, `$${p.price.toLocaleString()}`, `$${p.benchmark.toLocaleString()}`, `$${save.toLocaleString()} (${pct}%)`];
      });

      autoTable(doc, {
        startY: 38,
        head: [['Plan', 'Our Price', 'Int\'l Benchmark', 'You Save']],
        body: licBody,
        theme: 'striped',
        headStyles: { fillColor: [108, 99, 255], textColor: 255 },
        styles: { fontSize: 10, cellPadding: 2 },
        margin: { left: margin, right: margin },
      });

      // One-Time Professional Services
      const svcY = doc.lastAutoTable.finalY + 16;
      doc.setFontSize(16);
      doc.setTextColor(26, 26, 46);
      doc.text('One-Time Professional Services', margin, svcY);
      doc.setFontSize(9);
      doc.setTextColor(120, 120, 120);
      doc.text('Tailored to launch your national postal system fast — no in-house expertise required.', margin, svcY + 6);

      const oneTimeBody = [
        ['Setup & Onboarding', '$2,500 – $10,000', 'Configuration, user training, data import, go-live support'],
        ['Data Migration', '$1,500 – $5,000', 'Import shapefiles, census data, legacy postal databases'],
        ['White-Label / Custom Branding', '$5,000 – $15,000', 'Remove our logo, apply your national identity & colours'],
        ['System Integration', '$3,000 – $15,000', 'Connect to tax, land registry, voter rolls, or ID systems'],
      ];

      autoTable(doc, {
        startY: svcY + 10,
        head: [['Service', 'Price Range', 'What You Get']],
        body: oneTimeBody,
        theme: 'striped',
        headStyles: { fillColor: [108, 99, 255], textColor: 255 },
        styles: { fontSize: 10, cellPadding: 2, overflow: 'linebreak' },
        columnStyles: { 0: { cellWidth: 55 }, 1: { cellWidth: 40 }, 2: { cellWidth: 'auto' } },
        margin: { left: margin, right: margin },
      });

      // Marketing pitch
      const pitchY = doc.lastAutoTable.finalY + 12;
      doc.setFillColor(248, 249, 255);
      doc.roundedRect(margin, pitchY, pageW - margin * 2, 42, 4, 4, 'F');
      doc.setFontSize(12);
      doc.setTextColor(26, 26, 46);
      doc.text('Why invest in professional services?', margin + 6, pitchY + 10);
      doc.setFontSize(9);
      doc.setTextColor(80, 80, 80);
      const pitchLines = [
        '• Governments that skip setup support take 3x longer to launch — every delayed month costs public trust and revenue.',
        '• Data migration from legacy systems prevents costly duplication errors and ensures continuity.',
        '• White-label branding builds citizen confidence — your postal system looks like a home-grown institution, not imported software.',
        '• System integration unlocks cross-department revenue: connected addressing powers tax collection, voter registration,',
        '  emergency response, and e-commerce — paying for itself within the first year.',
      ];
      pitchLines.forEach((line, i) => doc.text(line, margin + 6, pitchY + 18 + i * 4.5));

      // Contact / CTA
      const ctaY = pitchY + 52;
      doc.setFontSize(14);
      doc.setTextColor(108, 99, 255);
      doc.text('Ready to modernise your national addressing system?', pageW / 2, ctaY, { align: 'center' });
      doc.setFontSize(10);
      doc.setTextColor(80, 80, 80);
      doc.text('Contact us to schedule a demonstration or request a pilot project.', pageW / 2, ctaY + 8, { align: 'center' });

      doc.save(`${selectedCountry.name || 'proposal'}-postal-genesis-proposal-${new Date().toISOString().slice(0,10)}.pdf`);
    } catch (e) { console.error('Proposal PDF failed:', e); alert('Proposal PDF failed: ' + e.message); }
    finally { setGeneratingReport(false); }
  }, [selectedCountry]);

  const handleGeneratePDF = useCallback(async () => {
    if (!mapWrapRef.current || !selectedCountry) return;
    const reportItems = buildReportData();
    if (!reportItems.length) { alert('Select at least one area in Report Mode first.'); return; }
    try {
      setGeneratingReport(true);
      const doc = new jsPDF({ unit: 'mm', format: 'a4' });
      const pageW = doc.internal.pageSize.getWidth();
      const pageH = doc.internal.pageSize.getHeight();
      const margin = 14;

      // Cover
      doc.setFontSize(22);
      doc.setTextColor(26, 26, 46);
      doc.text('Postal Code Genesis Report', pageW / 2, 40, { align: 'center' });
      doc.setFontSize(14);
      doc.setTextColor(100, 100, 100);
      doc.text(selectedCountry.name || 'Country', pageW / 2, 55, { align: 'center' });
      doc.setFontSize(11);
      doc.text(`Generated: ${new Date().toLocaleString()}`, pageW / 2, 65, { align: 'center' });
      doc.text(`Selected areas: ${selectedReportItems.size}`, pageW / 2, 72, { align: 'center' });

      // License Pricing Section
      doc.setFontSize(14);
      doc.setTextColor(108, 99, 255);
      doc.text('Software License Pricing', pageW / 2, 82, { align: 'center' });
      doc.setFontSize(9);
      doc.setTextColor(120, 120, 120);
      doc.text('25% cheaper than international addressing systems (Esri, Smarty, UPU consultancy)', pageW / 2, 88, { align: 'center' });
      doc.setFontSize(10);
      doc.setTextColor(80, 80, 80);

      // International benchmark pricing (mid-to-enterprise tier, national-level)
      // Excludes entry-level tiers. Based on Esri ArcGIS Enterprise, Smarty Business,
      // Loqate Enterprise, and UPU national addressing consultancy rates.
      const benchmark1yr = 25200;
      const benchmark2yr = 45300;
      const benchmark20yr = 451000;

      const plans = [
        { name: '1-Year Plan', price: 18900, period: 1, benchmark: benchmark1yr },
        { name: '2-Year Plan', price: 33900, period: 2, benchmark: benchmark2yr },
        { name: '20-Year Membership', price: 338000, period: 20, benchmark: benchmark20yr },
      ];

      // Calculate effective annual cost for each
      plans.forEach(p => { p.annual = p.price / p.period; p.benchAnnual = p.benchmark / p.period; });

      // Build license table with benchmark comparison
      const licBody = plans.map(p => {
        const saveVsBench = p.benchmark - p.price;
        const pctSave = Math.round((saveVsBench / p.benchmark) * 100);
        return [
          p.name,
          `$${p.price.toLocaleString()}`,
          `$${Math.round(p.annual).toLocaleString()}/yr`,
          `$${p.benchmark.toLocaleString()}`,
          `$${saveVsBench.toLocaleString()} (${pctSave}%)`,
        ];
      });

      autoTable(doc, {
        startY: 93,
        head: [['Plan', 'Our Price', 'Effective Annual', 'Int\'l Benchmark', 'You Save']],
        body: licBody,
        theme: 'striped',
        headStyles: { fillColor: [108, 99, 255], textColor: 255 },
        styles: { fontSize: 10, cellPadding: 2 },
        margin: { left: margin, right: margin },
      });

      doc.setFontSize(9);
      doc.setTextColor(100, 100, 100);
      doc.text('* International benchmark based on Esri ArcGIS Enterprise, Smarty Address Verification,', margin, doc.lastAutoTable.finalY + 6);
      doc.text('  and UPU national addressing consultancy rates for comparable national-level deployments.', margin, doc.lastAutoTable.finalY + 10);

      // Zoom map to selected report items before capture
      if (mapInstance && selectedReportItems.size > 0) {
        zoomToReportItems();
        await new Promise(r => setTimeout(r, 900)); // let tiles load after pan/zoom
      }

      // Map screenshot
      const imgData = await captureMap(mapWrapRef.current);
      const imgW = pageW - margin * 2;
      const imgH = imgW * 0.6;
      doc.addImage(imgData, 'PNG', margin, 85, imgW, imgH);

      // Summary table
      doc.addPage();
      doc.setFontSize(16);
      doc.setTextColor(26, 26, 46);
      doc.text('Selected Areas Summary', margin, 20);

      const tableBody = [];
      reportItems.forEach(item => {
        if (item.type === 'region') {
          tableBody.push([
            'Region',
            item.data.name,
            item.data.code || '-',
            item.districts.length,
            item.zones.length,
          ]);
        } else if (item.type === 'district') {
          tableBody.push([
            'District',
            item.data.name,
            item.data.code || '-',
            '-',
            item.zones.length,
          ]);
        } else {
          tableBody.push([
            'Zone',
            item.data.name,
            item.data.postal_code || '-',
            '-',
            '-',
          ]);
        }
      });

      autoTable(doc, {
        startY: 28,
        head: [['Type', 'Name', 'Code / Postal', 'Districts', 'Zones']],
        body: tableBody,
        theme: 'striped',
        headStyles: { fillColor: [108, 99, 255], textColor: 255 },
        styles: { fontSize: 10, cellPadding: 2 },
        margin: { left: margin, right: margin },
      });

      doc.setFontSize(9);
      doc.setTextColor(120, 120, 120);
      doc.text('* Postal Code Format: first 2 letters of Region + first 2 letters of District + 3-digit sequential number.', margin, doc.lastAutoTable.finalY + 6);
      doc.text('  Example: Region "Central" + District "Juba" = CEJU001, CEJU002...', margin, doc.lastAutoTable.finalY + 10);

      // Detail pages
      reportItems.forEach(item => {
        doc.addPage();
        doc.setFontSize(16);
        doc.setTextColor(26, 26, 46);
        if (item.type === 'region') {
          doc.text(`Region: ${item.data.name}`, margin, 20);
          doc.setFontSize(11);
          doc.setTextColor(80, 80, 80);
          doc.text(`Code: ${item.data.code || '-'} | Locked: ${item.data.locked ? 'Yes' : 'No'}`, margin, 28);
          // Region stats
          const regionPop = item.zones.reduce((sum, z) => sum + (z.population || 0), 0);
          const regionArea = item.zones.reduce((sum, z) => sum + (z.area_sq_km || 0), 0);
          const regionCost = estimateCost(regionArea, regionPop);
          doc.text(`Population: ${regionPop > 0 ? regionPop.toLocaleString() : '-'}`, margin, 34);
          doc.text(`Area: ${regionArea > 0 ? regionArea.toLocaleString() + ' km²' : '-'}`, margin, 40);
          doc.text(`Districts: ${item.districts.length} | Zones: ${item.zones.length}`, margin, 46);
          doc.setFontSize(12);
          doc.setTextColor(108, 99, 255);
          doc.text(`Est. Implementation Cost: ${regionCost.formatted}`, margin, 54);
          doc.setFontSize(9);
          doc.setTextColor(120, 120, 120);
          doc.text(regionCost.breakdown, margin, 60);
          if (item.districts.length) {
            const startY = 66;
            doc.setFontSize(13);
            doc.setTextColor(26, 26, 46);
            doc.text('Districts', margin, startY);
            autoTable(doc, {
              startY: startY + 4,
              head: [['District', 'Code', 'Zones']],
              body: item.districts.map(d => [d.name, d.code || '-', item.zones.filter(z => z.district_id === d.id).length]),
              theme: 'striped',
              headStyles: { fillColor: [108, 99, 255], textColor: 255 },
              styles: { fontSize: 10, cellPadding: 2 },
              margin: { left: margin, right: margin },
            });
          }
          if (item.zones.length) {
            const startY = doc.lastAutoTable ? doc.lastAutoTable.finalY + 8 : 74;
            doc.setFontSize(13);
            doc.setTextColor(26, 26, 46);
            doc.text('Postal Zones', margin, startY);
            autoTable(doc, {
              startY: startY + 4,
              head: [['Postal Code', 'Name', 'Population', 'Area (km²)', 'Status']],
              body: item.zones.map(z => [
                z.postal_code || '-',
                z.name,
                z.population != null ? z.population.toLocaleString() : '-',
                z.area_sq_km != null ? z.area_sq_km.toLocaleString() : '-',
                z.status || '-',
              ]),
              theme: 'striped',
              headStyles: { fillColor: [108, 99, 255], textColor: 255 },
              styles: { fontSize: 10, cellPadding: 2 },
              margin: { left: margin, right: margin },
            });
          }
        } else if (item.type === 'district') {
          doc.text(`District: ${item.data.name}`, margin, 20);
          doc.setFontSize(11);
          doc.setTextColor(80, 80, 80);
          doc.text(`Code: ${item.data.code || '-'} | Locked: ${item.data.locked ? 'Yes' : 'No'}`, margin, 28);
          const distPop = item.zones.reduce((sum, z) => sum + (z.population || 0), 0);
          const distArea = item.zones.reduce((sum, z) => sum + (z.area_sq_km || 0), 0);
          const distCost = estimateCost(distArea, distPop);
          doc.text(`Population: ${distPop > 0 ? distPop.toLocaleString() : '-'}`, margin, 34);
          doc.text(`Area: ${distArea > 0 ? distArea.toLocaleString() + ' km²' : '-'}`, margin, 40);
          doc.text(`Zones: ${item.zones.length}`, margin, 46);
          doc.setFontSize(12);
          doc.setTextColor(108, 99, 255);
          doc.text(`Est. Implementation Cost: ${distCost.formatted}`, margin, 54);
          doc.setFontSize(9);
          doc.setTextColor(120, 120, 120);
          doc.text(distCost.breakdown, margin, 60);
          if (item.zones.length) {
            const startY = 66;
            doc.setFontSize(13);
            doc.setTextColor(26, 26, 46);
            doc.text('Postal Zones', margin, startY);
            autoTable(doc, {
              startY: startY + 4,
              head: [['Postal Code', 'Name', 'Population', 'Area (km²)', 'Status']],
              body: item.zones.map(z => [
                z.postal_code || '-',
                z.name,
                z.population != null ? z.population.toLocaleString() : '-',
                z.area_sq_km != null ? z.area_sq_km.toLocaleString() : '-',
                z.status || '-',
              ]),
              theme: 'striped',
              headStyles: { fillColor: [108, 99, 255], textColor: 255 },
              styles: { fontSize: 10, cellPadding: 2 },
              margin: { left: margin, right: margin },
            });
          }
        } else {
          doc.text(`Zone: ${item.data.name}`, margin, 20);
          doc.setFontSize(11);
          doc.setTextColor(80, 80, 80);
          doc.text(`Postal Code: ${item.data.postal_code || '-'}`, margin, 28);
          doc.text(`Population: ${item.data.population != null ? item.data.population.toLocaleString() : '-'}`, margin, 34);
          doc.text(`Area: ${item.data.area_sq_km != null ? item.data.area_sq_km.toLocaleString() : '-'} km²`, margin, 40);
          doc.text(`Status: ${item.data.status || '-'}`, margin, 46);
          doc.text(`Locked: ${item.data.locked ? 'Yes' : 'No'}`, margin, 52);
          const zoneCost = estimateCost(item.data.area_sq_km, item.data.population);
          doc.setFontSize(12);
          doc.setTextColor(108, 99, 255);
          doc.text(`Est. Implementation Cost: ${zoneCost.formatted}`, margin, 62);
          doc.setFontSize(9);
          doc.setTextColor(120, 120, 120);
          doc.text(zoneCost.breakdown, margin, 68);
        }
      });

      doc.save(`${selectedCountry.name || 'report'}-postal-genesis-${new Date().toISOString().slice(0,10)}.pdf`);
    } catch (e) { console.error('PDF generation failed:', e); alert('PDF generation failed: ' + e.message); }
    finally { setGeneratingReport(false); }
  }, [captureMap, selectedCountry, selectedReportItems, buildReportData, estimateCost]);

  const loadSnapshots = useCallback(async () =>{
    if (!selectedCountry) return;
    try {
      const res = await listSnapshots(selectedCountry.id);
      setSnapshots(res.data);
    } catch (e) { console.error('loadSnapshots failed:', e); }
  }, [selectedCountry]);

  useEffect(() => {
    loadSnapshots();
  }, [loadSnapshots, regions.length, districts.length, zones.length]);

  const loadData = useCallback(async () => {
    if (!selectedCountry) return;
    setLoading(true);
    try {
      const [zRes, dRes] = await Promise.all([listZones(selectedCountry.id), listDistricts(selectedCountry.id)]);
      setZones(zRes.data);
      setDistricts(dRes.data);
    } catch (e) { console.error('loadZones/Districts failed:', e); }
    try {
      const rRes = await listRegions(selectedCountry.id);
      setRegions(rRes.data);
    } catch (e) { console.error('loadRegions failed:', e); }
    setLoading(false);
  }, [selectedCountry]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    setUndoableRegions(false);
  }, [selectedCountry?.id]);

  const startDraw = useCallback((target, item) => {
    setDrawing(true); setDrawPoints([]); setEditItem(item || null); setDrawTarget(target);
    setSelectedZone(null);
  }, []);

  const cancelDraw = useCallback(() => { setDrawing(false); setDrawPoints([]); setEditItem(null); setDrawTarget(null); }, []);

  const saveDraw = useCallback(async () => {
    if (drawTarget === 'split') {
      if (drawPoints.length < 2) { alert('Need at least 2 points for a split line.'); return; }
    } else if (drawPoints.length < 3) { alert('Need at least 3 points.'); return; }
    setSaving(true);
    try {
      if (drawTarget === 'split') {
        const coordinates = drawPoints.map(p => [p[1], p[0]]);
        const lineGeojson = { type: 'LineString', coordinates };
        await splitZone(editItem.id, lineGeojson);
        setDrawing(false); setDrawPoints([]); setEditItem(null); setDrawTarget(null);
        await loadData();
        setSaving(false);
        return;
      }

      const closed = [...drawPoints, drawPoints[0]];
      const coordinates = [closed.map(p => [p[1], p[0]])];
      const geojson = { type: 'Polygon', coordinates };

      if (drawTarget === 'zone') {
        if (editItem) {
          await updateZone(editItem.id, { boundary_geojson: geojson });
        } else {
          const districtId = selDistrict || (districts.length > 0 ? districts[0].id : undefined);
          await createZoneManual(selectedCountry.id, { country_id: selectedCountry.id, boundary_geojson: geojson, district_id: districtId });
        }
      } else if (drawTarget === 'district') {
        if (editItem) {
          await updateDistrict(editItem.id, { boundary_geojson: geojson });
        } else {
          const regionId = selRegion || (districts.length > 0 ? districts[0].region_id : undefined);
          if (!regionId) { alert('Select a region first.'); setSaving(false); return; }
          const dRes = await createDistrict(regionId, 'New District', `${String(districts.length + 1).padStart(2, '0')}`);
          const newDId = dRes.data?.id;
          if (newDId) await updateDistrict(newDId, { boundary_geojson: geojson });
          await loadData();
          setDrawing(false); setDrawPoints([]); setEditItem(null); setDrawTarget(null);
          setNameModalType('district');
          setNameModalTarget(regionId);
          setNameModalOpen(true);
          setSaving(false);
          return;
        }
      } else if (drawTarget === 'region') {
        if (editItem) {
          await updateRegion(editItem.id, { boundary_geojson: geojson });
        } else {
          // After drawing, prompt for name then create
          setDrawing(false); setDrawPoints([]); setEditItem(null); setDrawTarget(null);
          await loadData();
          const latest = await listRegions(selectedCountry.id);
          // Find the region we just drew by looking for one without boundary
          // Actually simpler: create with temp name, then rename via modal
          const rRes = await createRegion(selectedCountry.id, 'New Region', `${String(Math.floor(Math.random() * 90 + 10))}`);
          if (rRes.data?.id) {
            await updateRegion(rRes.data.id, { boundary_geojson: geojson });
            await loadData();
            setNameModalType('region');
            setNameModalTarget(rRes.data.id);
            setNameModalOpen(true);
          }
          setSaving(false);
          return;
        }
      } else if (drawTarget === 'country') {
        await updateCountryBoundary(selectedCountry.id, { boundary_geojson: geojson });
        if (onCountryUpdated) onCountryUpdated();
      }

      setDrawing(false); setDrawPoints([]); setEditItem(null); setDrawTarget(null);
      await loadData();
    } catch (err) {
      alert('Save failed: ' + (err.response?.data?.detail || err.message));
    }
    setSaving(false);
  }, [drawPoints, drawTarget, editItem, selDistrict, selRegion, selectedCountry, districts, loadData]);

  const toggleLock = useCallback(async (type, id, locked) => {
    try {
      if (type === 'zone') await updateZone(id, { locked: !locked });
      else if (type === 'district') await updateDistrict(id, { locked: !locked });
      else if (type === 'region') await updateRegion(id, { locked: !locked });
      else if (type === 'country') await updateCountryBoundary(selectedCountry.id, { locked: !locked });
      await loadData();
      if (selectedZone?.id === id && type === 'zone') setSelectedZone(prev => prev ? { ...prev, locked: !locked } : null);
    } catch (err) { alert('Lock failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData]);

  const handleDelete = useCallback(async (type, id) => {
    if (!window.confirm(`Delete this ${type}? This cannot be undone.`)) return;
    try {
      if (type === 'zone') await deleteZone(id);
      else if (type === 'district') await deleteDistrict(id);
      else if (type === 'region') await deleteRegion(id);
      setSelectedZone(null);
      await loadData();
    } catch (err) { alert('Delete failed: ' + (err.response?.data?.detail || err.message)); }
  }, [loadData]);

  const handleColorChange = useCallback(async (zoneId, color) => {
    try {
      await updateZone(zoneId, { color });
      await loadData();
      setSelectedZone(prev => prev ? { ...prev, color } : null);
    } catch (err) { alert('Color update failed: ' + (err.response?.data?.detail || err.message)); }
  }, [loadData]);

  const closeNameModal = useCallback(() => {
    setNameModalOpen(false);
    setNameModalType(null);
    setNameModalTarget(null);
    setCustomName('');
    setSelectedPresetName('');
  }, []);

  const submitNameModal = useCallback(async () => {
    const name = customName.trim() || selectedPresetName;
    if (!name) { alert('Please select or enter a name.'); return; }
    if (nameModalType === 'region') {
      try {
        await createRegion(selectedCountry.id, name, `${String(Math.floor(Math.random() * 90 + 10))}`);
        await loadData();
      } catch (err) { alert('Region creation failed: ' + (err.response?.data?.detail || err.message)); }
    } else if (nameModalType === 'district') {
      try {
        await createDistrict(nameModalTarget, name, `${String(Math.floor(Math.random() * 90 + 10))}`);
        await loadData();
      } catch (err) { alert('District creation failed: ' + (err.response?.data?.detail || err.message)); }
    }
    closeNameModal();
  }, [customName, selectedPresetName, nameModalType, nameModalTarget, selectedCountry, loadData, closeNameModal]);

  const clearSelections = useCallback(() => {
    // Hide whatever is currently selected instead of just deselecting
    setHiddenMap(prev => {
      const next = { ...prev };
      if (selectedZone) next[`z-${selectedZone.id}`] = true;
      if (selDistrict) next[`d-${selDistrict}`] = true;
      if (selRegion) next[`r-${selRegion}`] = true;
      return next;
    });
    setSelectedZone(null);
    setSelDistrict(null);
    setSelRegion(null);
  }, [selectedZone, selDistrict, selRegion]);

  const handleNameSave = useCallback(async (type, id, name) => {
    if (!name.trim()) return;
    try {
      if (type === 'region') await updateRegion(id, { name: name.trim() });
      else if (type === 'district') await updateDistrict(id, { name: name.trim() });
      await loadData();
      setEditingName(null);
    } catch (err) { alert('Rename failed: ' + (err.response?.data?.detail || err.message)); }
  }, [loadData]);

  const handleMoveZone = useCallback(async (zoneId, lat, lng) => {
    try {
      await updateZone(zoneId, { lat, lng });
      await loadData();
      setSelectedZone(prev => prev ? { ...prev, center_lat: lat, center_lng: lng } : null);
      setMovingZone(null);
    } catch (err) {
      alert('Move failed: ' + (err.response?.data?.detail || err.message));
      setMovingZone(null);
    }
  }, [loadData]);

  const handleAutoGen = useCallback(async () => {
    if (!window.confirm('Auto-generate zones for ALL districts? This replaces existing zones.')) return;
    try { await autoCreateAllZones(selectedCountry.id, 5000); await loadData(); }
    catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData]);

  const handleAutoRegions = useCallback(async () => {
    if (!window.confirm('Auto-generate regions for open areas? Existing regions will be preserved.')) return;
    try {
      await autoCreateRegions(selectedCountry.id);
      await loadData();
    }
    catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData]);

  const handleUndoRegions = useCallback(async () => {
    if (!window.confirm('Undo auto-regions? This deletes ALL regions, districts, and zones for this country.')) return;
    try { await deleteAllRegions(selectedCountry.id); setUndoableRegions(false); await loadData(); }
    catch (err) { alert('Undo failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData]);

  const handleUndoDistricts = useCallback(async (regionId) => {
    const snapshotId = undoableDistricts[regionId];
    if (!snapshotId) return;
    if (!window.confirm('Undo auto-districts for this region? This restores the previous district layout.')) return;
    try {
      await restoreSnapshot(selectedCountry.id, snapshotId);
      setUndoableDistricts(prev => {
        const next = { ...prev };
        delete next[regionId];
        return next;
      });
      await loadData();
      await loadSnapshots();
    }
    catch (err) { alert('Undo failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData, loadSnapshots, undoableDistricts]);

  const handleSaveSnapshot = useCallback(async () => {
    try { await saveSnapshot(selectedCountry.id); await loadSnapshots(); alert('Snapshot saved!'); }
    catch (err) { alert('Save failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadSnapshots]);

  const handleRestoreSnapshot = useCallback(async (snapshotId) => {
    if (!window.confirm('Restore this snapshot? This replaces all current regions, districts, and zones.')) return;
    try { await restoreSnapshot(selectedCountry.id, snapshotId); await loadData(); await loadSnapshots(); }
    catch (err) { alert('Restore failed: ' + (err.response?.data?.detail || err.message)); }
  }, [selectedCountry, loadData, loadSnapshots]);

  const handleAutoDistricts = useCallback(async (regionId) => {
    if (!window.confirm('Auto-generate districts for open areas in this region? Existing districts will be preserved.')) return;
    const input = window.prompt('How many districts do you want to create? (Leave empty for automatic)', '');
    const numDistricts = input ? parseInt(input.trim(), 10) : null;
    if (input && (isNaN(numDistricts) || numDistricts < 1)) {
      alert('Please enter a valid number (1 or more).');
      return;
    }
    try {
      const res = await autoCreateDistricts(regionId, numDistricts);
      await loadData();
      await loadSnapshots();
      if (res.data?.snapshot_id) {
        setUndoableDistricts(prev => ({ ...prev, [regionId]: res.data.snapshot_id }));
      }
      alert(res.data?.detail || 'Districts generated');
    }
    catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); }
  }, [loadData, loadSnapshots]);

  const onMapClick = useCallback((e) => {
    if (movingZone) {
      handleMoveZone(movingZone, e.latlng.lat, e.latlng.lng);
      return;
    }
    if (!drawing) {
      clearSelections();
      return;
    }
    setDrawPoints(prev => [...prev, [e.latlng.lat, e.latlng.lng]]);
  }, [drawing, movingZone, clearSelections]);

  if (!selectedCountry) return <div style={styles.empty}>Select a country to view zones</div>;

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e' }}>{selectedCountry.name}</span>
        <span style={{ fontSize: 12, color: '#666' }}>({zones.length} zones, {districts.length} districts)</span>
        <div style={{ flex: 1 }} />
        {selectedCountry?.boundary_geojson && !countryHidden && (
          <>
            <button style={{ ...styles.btnS, border: '1px solid #6c63ff', color: '#6c63ff' }} onClick={() => startDraw('country', null)}>✏️ Edit Border</button>
            <button style={{ ...styles.btnS, border: '1px solid #999', color: '#666' }} onClick={() => setCountryHidden(true)}>👁️‍🗨️ Hide Border</button>
          </>
        )}
        {countryHidden && (
          <button style={{ ...styles.btnS, border: '1px solid #51cf66', color: '#51cf66' }} onClick={() => setCountryHidden(false)}>👁️ Show Border</button>
        )}
        {!selectedCountry?.boundary_geojson && (
          <button style={styles.btnO} onClick={() => startDraw('country', null)}>🌍 Draw Border</button>
        )}
        <button style={styles.btn} onClick={() => startDraw('region', null)}>🗺 Region</button>
        <button style={styles.btnS} onClick={() => startDraw('district', null)}>📍 District</button>
        <button style={styles.btnG} onClick={() => startDraw('zone', null)}>✏️ Zone</button>
        <button style={styles.btnG} onClick={handleAutoGen}>⚡ Auto-Fill</button>
        <button style={styles.btnO} onClick={handleAutoRegions}>🗺 Auto Regions</button>
        {undoableRegions && (
          <button style={{ ...styles.btnD, background: '#c62828' }} onClick={handleUndoRegions}>↩️ Undo Regions</button>
        )}
        {(selectedZone || selDistrict || selRegion) && (
          <button style={{ ...styles.btnS, border: '1px solid #999', color: '#666' }} onClick={clearSelections}>👁️‍🗨️ Hide Selection</button>
        )}
        {Object.keys(hiddenMap).length > 0 && (
          <button style={{ ...styles.btnS, border: '1px solid #51cf66', color: '#51cf66' }} onClick={() => setHiddenMap({})}>👁️ Show All ({Object.keys(hiddenMap).length} hidden)</button>
        )}
        <button style={{ ...styles.btnS, border: '1px solid #4363d8', color: '#4363d8' }} onClick={handleSaveSnapshot}>💾 Save Snapshot</button>
        <button style={{ ...styles.btnS, border: snapshotsVisible ? '1px solid #999' : '1px solid #4363d8', color: snapshotsVisible ? '#666' : '#4363d8' }} onClick={() => setSnapshotsVisible(v => !v)}>
          {snapshotsVisible ? '👁️‍🗨️ Hide Snapshots' : '📸 Show Snapshots'}
        </button>
        <button style={{ ...styles.btnS, border: '1px solid #6c63ff', color: '#6c63ff' }} onClick={handleScreenshot} disabled={generatingReport}>📸 Screenshot</button>
        <button style={{ ...styles.btnS, border: '1px solid #1a1a2e', color: '#1a1a2e', fontWeight: 700 }} onClick={handleGenerateProposalPDF} disabled={generatingReport}>📋 Product Proposal</button>
        <button style={{ ...styles.btnS, border: reportMode ? '1px solid #ff922b' : '1px solid #999', color: reportMode ? '#ff922b' : '#666' }} onClick={() => { setReportMode(v => !v); if (reportMode) clearReportSelection(); }}>
          {reportMode ? '📄 Exit Report' : '📄 Report Mode'}
        </button>
        {reportMode && selectedReportItems.size > 0 && (
          <button style={{ ...styles.btn, background: '#4363d8' }} onClick={handleGeneratePDF} disabled={generatingReport}>📥 Generate PDF ({selectedReportItems.size})</button>
        )}
      </div>

      <div style={styles.mapWrap} ref={mapWrapRef}>
        <MapContainer center={[4.85, 31.6]} zoom={6} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" crossOrigin="anonymous" updateWhenIdle={true} updateWhenZooming={false} />
          <FitBounds zones={zones} cid={selectedCountry.id} />
          <MapRef onReady={setMapInstance} />
          <ClickH onClick={onMapClick} />

          {selectedCountry?.boundary_geojson && !countryHidden && (
            <GeoJSON key={`country-${selectedCountry.id}-${(selectedCountry.boundary_geojson?.type||"")}`} data={selectedCountry.boundary_geojson} style={{ color: '#6c63ff', weight: 3, fillColor: '#6c63ff', fillOpacity: 0.12 }} />
          )}

          {regions.filter(r => r.boundary_geojson && !isHidden(hiddenMap, 'r', r.id)).map((r) => {
            const color = REGION_COLORS[r.id % REGION_COLORS.length];
            const rSel = isReportSelected('region', r.id);
            return (
              <GeoJSON key={`rg-${r.id}-${r.boundary_geojson?.type||""}`} data={r.boundary_geojson} style={() => ({ color: rSel ? '#ffd43b' : color, weight: rSel ? 6 : 3, fillColor: rSel ? '#ffd43b' : color, fillOpacity: rSel ? 0.55 : 0.2, dashArray: rSel ? undefined : '8,4' })} eventHandlers={{ click: () => { if (!drawing) { if (reportMode) { toggleReportItem('region', r.id); } else { setSelRegion(r.id); setSelDistrict(null); zoomToFeature('region', r.id); } } } }} />
            );
          })}

          {districts.filter(d => !isHidden(hiddenMap, 'd', d.id)).map((d, i) => {
            const isSel = selDistrict === d.id;
            const rSel = isReportSelected('district', d.id);
            const col = rSel ? '#ffd43b' : (isSel ? '#6c63ff' : (i % 2 === 0 ? '#888' : '#aaa'));
            return d.boundary_geojson ? (
              <GeoJSON key={`d-${d.id}-${d.boundary_geojson?.type||""}`} data={d.boundary_geojson} style={() => ({
                color: col, weight: rSel ? 6 : (isSel ? 3 : 2), fillColor: rSel ? '#ffd43b' : (isSel ? '#6c63ff' : '#ccc'),
                fillOpacity: rSel ? 0.55 : (isSel ? 0.25 : 0.12), dashArray: (d.locked && !rSel) ? '8,4' : undefined,
              })} eventHandlers={{
                click: () => { if (!drawing) { if (reportMode) { toggleReportItem('district', d.id); } else { setSelDistrict(isSel ? null : d.id); setSelRegion(d.region_id); if (!isSel) zoomToFeature('district', d.id); } } },
              }} />
            ) : null;
          })}

          {zones.filter(z => !isHidden(hiddenMap, 'z', z.id)).map((zone) => {
            const color = getZoneColor(zone);
            const isSel = selectedZone?.id === zone.id;
            const isEdit = editItem?.id === zone.id && drawTarget === 'zone';
            const zRep = isReportSelected('zone', zone.id);
            if (isEdit) return null;
            if (zone.boundary_geojson) {
              return (
                <GeoJSON key={`z-${zone.id}-${zone.boundary_geojson?.type||""}`} data={zone.boundary_geojson} style={() => ({
                  color: zRep ? '#ffd43b' : (isSel ? '#fff' : color), weight: zRep ? 5 : (isSel ? 3 : 1.5),
                  fillColor: zRep ? '#ffd43b' : color, fillOpacity: zRep ? 0.55 : (isSel ? 0.5 : 0.3),
                  dashArray: zone.locked ? '4,4' : undefined,
                })} eventHandlers={{ click: () => { if (!drawing && !movingZone) { if (reportMode) { toggleReportItem('zone', zone.id); } else { setSelectedZone(zone); zoomToFeature('zone', zone.id); } } } }} />
              );
            }
            return (
              <CircleMarker key={zone.id} center={[zone.center_lat || 0, zone.center_lng || 0]} radius={zRep ? 16 : (movingZone === zone.id ? 14 : 10)}
                pathOptions={{ color: zRep ? '#ffd43b' : (movingZone === zone.id ? '#ff922b' : (isSel ? '#ff6b6b' : color)), fillColor: zRep ? '#ffd43b' : color, fillOpacity: zRep ? 0.7 : (movingZone === zone.id ? 0.5 : 0.3), weight: zRep ? 6 : (movingZone === zone.id ? 4 : (isSel ? 3 : 2)) }}
                eventHandlers={{ click: () => { if (!drawing && !movingZone) { if (reportMode) { toggleReportItem('zone', zone.id); } else { setSelectedZone(zone); zoomToFeature('zone', zone.id); } } } }} />
            );
          })}

          {zones.filter(z => !isHidden(hiddenMap, 'z', z.id)).map((zone) => {
            const color = getZoneColor(zone);
            const zRep = isReportSelected('zone', zone.id);
            const labelColor = zRep ? '#1a1a2e' : color;
            const labelBg = zRep ? '#ffd43b' : 'rgba(255,255,255,.95)';
            const labelBorder = zRep ? '2px solid #1a1a2e' : `1px solid ${color}`;
            return (
              <Marker key={`l-${zone.id}`} position={[zone.center_lat || 0, zone.center_lng || 0]}
                icon={L.divIcon({ className: '', html: `<div style="background:${labelBg};padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;color:${labelColor};border:${labelBorder};white-space:nowrap;pointer-events:none;">${zone.locked ? '🔒' : ''}${zone.postal_code}</div>`, iconSize: [80, 20], iconAnchor: [40, 10] })}
                interactive={false} />
            );
          })}

          {drawing && drawPoints.length > 0 && (
            <>
              {drawTarget === 'split' ? (
                <>
                  <Polygon positions={drawPoints} pathOptions={{ color: '#ff6b6b', dashArray: '5,8', weight: 3 }} />
                  {drawPoints.map((p, i) => <CircleMarker key={`p-${i}`} center={p} radius={5} pathOptions={{ color: '#ff6b6b', fillColor: '#ff6b6b', fillOpacity: 1, weight: 1 }} />)}
                </>
              ) : (
                <>
                  <Polygon positions={drawPoints} pathOptions={{ color: '#ff6b6b', dashArray: '5,8', fillColor: '#ff6b6b', fillOpacity: 0.15, weight: 2 }} />
                  {drawPoints.map((p, i) => <CircleMarker key={`p-${i}`} center={p} radius={5} pathOptions={{ color: '#ff6b6b', fillColor: '#ff6b6b', fillOpacity: 1, weight: 1 }} />)}
                </>
              )}
            </>
          )}
        </MapContainer>

        {drawing && (
          <div style={styles.bar}>
            <span style={{ fontWeight: 700, fontSize: 13, color: '#6c63ff' }}>
              {drawTarget === 'split'
                ? (editItem ? `Split ${editItem.postal_code}: draw a line across the zone` : 'Draw split line')
                : (editItem ? `Edit ${drawTarget}: ${editItem.postal_code || editItem.name}` : `Draw new ${drawTarget}`)}
            </span>
            <span style={{ fontSize: 12, color: '#666' }}>{drawPoints.length} pts</span>
            {(drawTarget === 'split' ? drawPoints.length >= 2 : drawPoints.length >= 3) && <button style={styles.btnG} onClick={saveDraw} disabled={saving}>{saving ? 'Saving...' : '✓ Save'}</button>}
            {drawPoints.length > 0 && <button style={styles.btnS} onClick={() => setDrawPoints(p => p.slice(0, -1))}>Undo</button>}
            <button style={styles.btnD} onClick={cancelDraw}>Cancel</button>
          </div>
        )}

        {movingZone && (
          <div style={{ ...styles.bar, border: '2px solid #ff922b' }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: '#ff922b' }}>
              📍 Moving {zones.find(z => z.id === movingZone)?.postal_code}
            </span>
            <span style={{ fontSize: 12, color: '#666' }}>Click anywhere on the map to place</span>
            <button style={styles.btnD} onClick={() => setMovingZone(null)}>Cancel</button>
          </div>
        )}

        {zones.length > 0 && !drawing && (
          <div style={styles.legend}>
            <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13, color: '#1a1a2e' }}>Zones</div>
            <div style={{ maxHeight: '40vh', overflowY: 'auto' }}>
              {zones.filter(z => !isHidden(hiddenMap, 'z', z.id)).slice(0, 50).map((z) => {
                const color = getZoneColor(z);
                return (
                  <div key={z.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2, cursor: 'pointer' }} onClick={() => { setSelectedZone(z); zoomToFeature('zone', z.id); }}>
                    <div style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '1px solid rgba(0,0,0,.1)' }} />
                    <span style={{ color: '#333', fontSize: 11 }}>{z.locked ? '🔒' : ''} {z.postal_code}</span>
                    <span style={{ color: '#888', fontSize: 10 }}>- {z.name}</span>
                  </div>
                );
              })}
              {zones.some(z => isHidden(hiddenMap, 'z', z.id)) && (
                <div style={{ fontSize: 10, color: '#999', marginTop: 4, paddingTop: 4, borderTop: '1px solid #eee' }}>
                  {zones.filter(z => isHidden(hiddenMap, 'z', z.id)).length} hidden
                </div>
              )}
            </div>
          </div>
        )}

        {selectedZone && !drawing && (
          <div style={styles.info}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, color: getZoneColor(selectedZone) }}>
                  {selectedZone.locked ? '🔒 ' : ''}{selectedZone.postal_code}
                </div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{selectedZone.name}</div>
              </div>
              <button style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#999' }} onClick={() => setSelectedZone(null)}>✕</button>
            </div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 6 }}>
              {selectedZone.region_name && <div>Region: <strong>{selectedZone.region_name}</strong></div>}
              {selectedZone.district_name && <div>District: <strong>{selectedZone.district_name}</strong></div>}
              {selectedZone.population && <div>Population: <strong>{selectedZone.population.toLocaleString()}</strong></div>}
              {selectedZone.area_sq_km && <div>Area: <strong>{selectedZone.area_sq_km.toFixed(1)} km²</strong></div>}
            </div>
            <div style={{ marginTop: 10, display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: '#666', marginRight: 4 }}>Color:</span>
              {ZONE_COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => handleColorChange(selectedZone.id, c)}
                  style={{
                    width: 18, height: 18, borderRadius: 4, background: c,
                    border: getZoneColor(selectedZone) === c ? '2px solid #1a1a2e' : '1px solid #ddd',
                    cursor: 'pointer', padding: 0,
                  }}
                  title={c}
                />
              ))}
              <button
                onClick={() => handleColorChange(selectedZone.id, null)}
                style={{
                  fontSize: 10, padding: '2px 6px', borderRadius: 4,
                  border: '1px solid #ddd', background: '#f5f5fa', cursor: 'pointer',
                  color: '#666',
                }}
              >
                Reset
              </button>
            </div>
            <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button style={styles.btn} onClick={() => startDraw('zone', selectedZone)}>✏️ Edit</button>
              <button style={{ ...styles.btnS, background: '#fff3e0', color: '#e65100', border: '1px solid #ff9800' }} onClick={() => startDraw('split', selectedZone)}>✂️ Split</button>
              <button style={{ ...styles.btnS, background: movingZone === selectedZone.id ? '#ffe8cc' : '#f0f0f5', color: '#ff922b', border: '1px solid #ff922b' }} onClick={() => setMovingZone(movingZone === selectedZone.id ? null : selectedZone.id)}>
                {movingZone === selectedZone.id ? '❌ Cancel Move' : '📍 Move'}
              </button>
              <button style={{ ...styles.btnS, border: '1px solid #999', color: '#666' }} onClick={() => { setHiddenMap(prev => ({ ...prev, [`z-${selectedZone.id}`]: true })); setSelectedZone(null); }}>👁️‍🗨️ Hide</button>
              <button style={styles.btnS} onClick={() => toggleLock('zone', selectedZone.id, selectedZone.locked)}>
                {selectedZone.locked ? '🔓 Unlock' : '🔒 Lock'}
              </button>
              <button style={styles.btnD} onClick={() => handleDelete('zone', selectedZone.id)}>🗑 Delete</button>
            </div>
          </div>
        )}

        {selDistrict && !drawing && districts.find(d => d.id === selDistrict) && (
          <div style={{ position: 'absolute', bottom: 20, left: 20, background: '#fff', borderRadius: 12, padding: 14, boxShadow: '0 4px 20px rgba(0,0,0,.15)', maxWidth: 260, zIndex: 1000, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              {editingName?.type === 'district' && editingName?.id === selDistrict ? (
                <input
                  autoFocus
                  value={editingName.value}
                  onChange={(e) => setEditingName(prev => ({ ...prev, value: e.target.value }))}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleNameSave('district', selDistrict, editingName.value); if (e.key === 'Escape') setEditingName(null); }}
                  onBlur={() => setEditingName(null)}
                  style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 6, border: '1px solid #6c63ff', borderRadius: 4, padding: '2px 6px', width: '100%' }}
                />
              ) : (
                <div
                  style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 6, cursor: 'pointer' }}
                  onClick={() => {
                    const d = districts.find(x => x.id === selDistrict);
                    if (!d?.locked) setEditingName({ type: 'district', id: selDistrict, value: d?.name || '' });
                  }}
                  title={districts.find(d => d.id === selDistrict)?.locked ? 'Locked' : 'Click to rename'}
                >
                  📍 {districts.find(d => d.id === selDistrict)?.name}
                  {districts.find(d => d.id === selDistrict)?.locked ? ' 🔒' : ''}
                  {!districts.find(d => d.id === selDistrict)?.locked && <span style={{ fontSize: 10, color: '#999', marginLeft: 4 }}>✏️</span>}
                </div>
              )}
              <button style={{ background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#999', lineHeight: 1 }} onClick={() => setSelDistrict(null)}>✕</button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button style={styles.btnS} onClick={() => startDraw('district', districts.find(d => d.id === selDistrict))}>✏️ Edit Boundary</button>
              <button style={{ ...styles.btnS, border: '1px solid #999', color: '#666' }} onClick={() => { setHiddenMap(prev => ({ ...prev, [`d-${selDistrict}`]: true })); setSelDistrict(null); }}>👁️‍🗨️ Hide</button>
              <button style={styles.btnS} onClick={() => toggleLock('district', selDistrict, districts.find(d => d.id === selDistrict)?.locked)}>
                {districts.find(d => d.id === selDistrict)?.locked ? '🔓 Unlock' : '🔒 Lock'}
              </button>
              <button style={styles.btnD} onClick={() => handleDelete('district', selDistrict)}>🗑</button>
            </div>
          </div>
        )}

        {selRegion && !drawing && regions.find(r => r.id === selRegion) && (
          <div style={{ position: 'absolute', bottom: 80, left: 20, background: '#fff', borderRadius: 12, padding: 14, boxShadow: '0 4px 20px rgba(0,0,0,.15)', maxWidth: 260, zIndex: 1000, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              {editingName?.type === 'region' && editingName?.id === selRegion ? (
                <input
                  autoFocus
                  value={editingName.value}
                  onChange={(e) => setEditingName(prev => ({ ...prev, value: e.target.value }))}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleNameSave('region', selRegion, editingName.value); if (e.key === 'Escape') setEditingName(null); }}
                  onBlur={() => setEditingName(null)}
                  style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 6, border: '1px solid #6c63ff', borderRadius: 4, padding: '2px 6px', width: '100%' }}
                />
              ) : (
                <div
                  style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 6, cursor: 'pointer' }}
                  onClick={() => {
                    const r = regions.find(x => x.id === selRegion);
                    if (!r?.locked) setEditingName({ type: 'region', id: selRegion, value: r?.name || '' });
                  }}
                  title={regions.find(r => r.id === selRegion)?.locked ? 'Locked' : 'Click to rename'}
                >
                  🗺️ {regions.find(r => r.id === selRegion)?.name}
                  {regions.find(r => r.id === selRegion)?.locked ? ' 🔒' : ''}
                  {!regions.find(r => r.id === selRegion)?.locked && <span style={{ fontSize: 10, color: '#999', marginLeft: 4 }}>✏️</span>}
                </div>
              )}
              <button style={{ background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#999', lineHeight: 1 }} onClick={() => setSelRegion(null)}>✕</button>
            </div>
            <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>
              Boundary: {regions.find(r => r.id === selRegion)?.boundary_geojson ? '✅ Yes' : '❌ None — draw one'}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button style={styles.btnS} onClick={() => startDraw('region', regions.find(r => r.id === selRegion))}>✏️ Edit Boundary</button>
              <button style={{ ...styles.btnS, border: '1px solid #999', color: '#666' }} onClick={() => { setHiddenMap(prev => ({ ...prev, [`r-${selRegion}`]: true })); setSelRegion(null); }}>👁️‍🗨️ Hide</button>
              <button style={styles.btnO} onClick={() => handleAutoDistricts(selRegion)}>📍 Auto Districts</button>
              {undoableDistricts[selRegion] && (
                <button style={{ ...styles.btnD, background: '#c62828' }} onClick={() => handleUndoDistricts(selRegion)}>↩️ Undo Districts</button>
              )}
              <button style={styles.btnS} onClick={() => toggleLock('region', selRegion, regions.find(r => r.id === selRegion)?.locked)}>
                {regions.find(r => r.id === selRegion)?.locked ? '🔓 Unlock' : '🔒 Lock'}
              </button>
              <button style={styles.btnD} onClick={() => handleDelete('region', selRegion)}>🗑</button>
            </div>
          </div>
        )}

        {regions.length > 0 && !drawing && (
          <div style={{ position: 'absolute', top: 80, left: 20, background: '#fff', borderRadius: 10, padding: 12, boxShadow: '0 2px 12px rgba(0,0,0,.12)', maxWidth: 240, zIndex: 1000, fontSize: '12px', maxHeight: '40vh', overflowY: 'auto' }}>
            <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13, color: '#1a1a2e' }}>Regions</div>
            {regions.map((r) => {
              const color = REGION_COLORS[r.id % REGION_COLORS.length];
              const isSel = selRegion === r.id;
              const hidden = isHidden(hiddenMap, 'r', r.id);
              const rRep = isReportSelected('region', r.id);
              return (
                <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2, cursor: 'pointer', background: rRep ? '#fffce8' : (isSel ? '#f0f0f5' : 'transparent'), borderRadius: 4, padding: '2px 4px', opacity: hidden ? 0.4 : 1, border: rRep ? '1px solid #ffd43b' : '1px solid transparent' }} onClick={() => { if (reportMode) { toggleReportItem('region', r.id); } else { setSelRegion(isSel ? null : r.id); setSelDistrict(null); if (!isSel) zoomToFeature('region', r.id); } }}>
                  <div style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '1px solid rgba(0,0,0,.1)' }} />
                  <span style={{ color: '#333', fontSize: 11, textDecoration: hidden ? 'line-through' : 'none', fontWeight: rRep ? 700 : 400 }}>{r.locked ? '🔒' : ''} {r.name} {hidden ? '👁️‍🗨️' : ''} {rRep ? '✅' : ''}</span>
                  <span style={{ color: r.boundary_geojson ? '#51cf66' : '#ff6b6b', fontSize: 9 }}>{r.boundary_geojson ? '●' : '○'}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Snapshots Panel */}
        {snapshots.length > 0 && !drawing && snapshotsVisible && (
          <div style={{ position: 'absolute', ...(({ tl: { top: 80, left: 270 }, tr: { top: 80, right: 20 }, bl: { bottom: 20, left: 20 }, br: { bottom: 20, right: 20 } })[snapshotsPos]), background: '#fff', borderRadius: 10, padding: 12, boxShadow: '0 2px 12px rgba(0,0,0,.12)', maxWidth: 220, zIndex: 1000, fontSize: '12px', maxHeight: '40vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: '#1a1a2e' }}>📸 Snapshots</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <button title="Top left" style={{ background: 'none', border: 'none', fontSize: 10, cursor: 'pointer', color: snapshotsPos === 'tl' ? '#6c63ff' : '#ccc', padding: 0 }} onClick={() => setSnapshotsPos('tl')}>↖</button>
                <button title="Top right" style={{ background: 'none', border: 'none', fontSize: 10, cursor: 'pointer', color: snapshotsPos === 'tr' ? '#6c63ff' : '#ccc', padding: 0 }} onClick={() => setSnapshotsPos('tr')}>↗</button>
                <button title="Bottom left" style={{ background: 'none', border: 'none', fontSize: 10, cursor: 'pointer', color: snapshotsPos === 'bl' ? '#6c63ff' : '#ccc', padding: 0 }} onClick={() => setSnapshotsPos('bl')}>↙</button>
                <button title="Bottom right" style={{ background: 'none', border: 'none', fontSize: 10, cursor: 'pointer', color: snapshotsPos === 'br' ? '#6c63ff' : '#ccc', padding: 0 }} onClick={() => setSnapshotsPos('br')}>↘</button>
                <button title="Close panel" style={{ background: 'none', border: 'none', fontSize: 14, cursor: 'pointer', color: '#999', padding: '0 0 0 4px', lineHeight: 1 }} onClick={() => setSnapshotsVisible(false)}>×</button>
              </div>
            </div>
            <button style={{ background: 'none', border: 'none', fontSize: 12, cursor: 'pointer', color: '#999', padding: 0, marginBottom: 6, display: 'block' }} onClick={() => setShowSnapshots(!showSnapshots)}>{showSnapshots ? '▲ Collapse' : '▼ Expand (' + snapshots.length + ')'}</button>
            {showSnapshots && snapshots.map((s, i) => (
              <div key={s.id} style={{ marginBottom: 6, padding: '6px 8px', background: '#f8f9ff', borderRadius: 6, border: '1px solid #e8e8f0' }}>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>#{snapshots.length - i} — {new Date(s.created_at).toLocaleString()}</div>
                <button style={{ ...styles.btnS, fontSize: 10, padding: '4px 8px', width: '100%' }} onClick={() => handleRestoreSnapshot(s.id)}>↩️ Revert to this</button>
              </div>
            ))}
          </div>
        )}

        {/* Report Selection Panel */}
        {reportMode && !drawing && (
          <div style={{ position: 'absolute', bottom: 20, right: 20, background: '#fff', borderRadius: 10, padding: 12, boxShadow: '0 2px 12px rgba(0,0,0,.12)', maxWidth: 260, zIndex: 1000, fontSize: '12px', maxHeight: '35vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: '#1a1a2e' }}>📄 Report Selection ({selectedReportItems.size})</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button style={{ background: 'none', border: 'none', fontSize: 12, cursor: 'pointer', color: '#999' }} onClick={clearReportSelection}>Clear</button>
                <button style={{ background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#999', lineHeight: 1, padding: 0 }} onClick={() => { setReportMode(false); clearReportSelection(); }} title="Close report panel">✕</button>
              </div>
            </div>
            {selectedReportItems.size === 0 && <div style={{ fontSize: 11, color: '#999' }}>Click regions, districts, or zones on the map to add them.</div>}
            {Array.from(selectedReportItems).map(key => {
              const [type, idStr] = key.split('-');
              const id = parseInt(idStr, 10);
              let label = '-';
              if (type === 'region') { const r = regions.find(x => x.id === id); label = r ? `🗺️ ${r.name}` : '-'; }
              else if (type === 'district') { const d = districts.find(x => x.id === id); label = d ? `📍 ${d.name}` : '-'; }
              else { const z = zones.find(x => x.id === id); label = z ? `📮 ${z.postal_code} — ${z.name}` : '-'; }
              return (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4, padding: '4px 6px', background: '#f8f9ff', borderRadius: 6, border: '1px solid #e8e8f0' }}>
                  <span style={{ fontSize: 11, color: '#333' }}>{label}</span>
                  <button style={{ background: 'none', border: 'none', fontSize: 14, cursor: 'pointer', color: '#ff6b6b', padding: 0, lineHeight: 1 }} onClick={() => toggleReportItem(type, id)}>×</button>
                </div>
              );
            })}
            {selectedReportItems.size > 0 && (
              <button style={{ ...styles.btn, width: '100%', marginTop: 8, fontSize: 11, padding: '6px' }} onClick={handleGeneratePDF} disabled={generatingReport}>
                {generatingReport ? 'Generating...' : '📥 Download PDF'}
              </button>
            )}
          </div>
        )}

        {/* Naming Modal */}
        {nameModalOpen && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 5000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, maxWidth: 420, width: '90%', boxShadow: '0 8px 40px rgba(0,0,0,0.2)' }}>
              <div style={{ fontWeight: 700, fontSize: 16, color: '#1a1a2e', marginBottom: 16 }}>
                {nameModalType === 'region' ? '🗺️ Name this Region' : '📍 Name this District'}
              </div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Choose from list or type a custom name:</div>
                <select
                  value={selectedPresetName}
                  onChange={(e) => { setSelectedPresetName(e.target.value); setCustomName(''); }}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13, marginBottom: 10 }}
                >
                  <option value="">-- Select from list --</option>
                  {(nameModalType === 'region' ? PREDEFINED_REGION_NAMES : PREDEFINED_DISTRICT_NAMES).map(n => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
                <div style={{ fontSize: 11, color: '#999', textAlign: 'center', marginBottom: 8 }}>— or —</div>
                <input
                  autoFocus
                  type="text"
                  placeholder={`Custom ${nameModalType} name...`}
                  value={customName}
                  onChange={(e) => { setCustomName(e.target.value); setSelectedPresetName(''); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') submitNameModal(); }}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }}
                />
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button style={{ ...styles.btnS, fontSize: 13, padding: '8px 16px' }} onClick={closeNameModal}>Cancel</button>
                <button style={{ ...styles.btn, fontSize: 13, padding: '8px 16px' }} onClick={submitNameModal}>Save Name</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
