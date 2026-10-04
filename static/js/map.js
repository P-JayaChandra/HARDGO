/* HardGo maps: Leaflet/OpenStreetMap first, no API key required. */

let trackingMap = null;
let trackingLayers = [];
const deliveryMaps = {};
let checkoutMap = null;
let checkoutMarker = null;

function validCoord(v) { return typeof v === 'number' && Number.isFinite(v); }

function makeIcon(type) {
    if (!window.L) return null;
    const cfg = type === 'shop'
        ? {bg:'#0284c7', icon:'fa-store', size:34}
        : type === 'bike'
        ? {bg:'#00f0ff', icon:'fa-motorcycle', size:38}
        : {bg:'#10b981', icon:'fa-location-dot', size:34};
    return L.divIcon({className:'hardgo-map-icon', html:`<div style="background:${cfg.bg};color:${type==='bike'?'#000':'#fff'};width:${cfg.size}px;height:${cfg.size}px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 2px 8px #0008"><i class="fas ${cfg.icon}"></i></div>`, iconSize:[cfg.size,cfg.size], iconAnchor:[cfg.size/2,cfg.size/2]});
}

function baseLeafletMap(elementId, lat, lng, zoom=15) {
    const el = document.getElementById(elementId);
    if (!el || !window.L || !validCoord(lat) || !validCoord(lng)) return null;
    const map = L.map(el, {center:[lat,lng], zoomControl:true, scrollWheelZoom:true});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom:19,
        attribution:'&copy; OpenStreetMap contributors'
    }).addTo(map);
    return map;
}

async function drawRoadRoute(map, fromLat, fromLng, toLat, toLng) {
    try {
        const url = `https://router.project-osrm.org/route/v1/driving/${fromLng},${fromLat};${toLng},${toLat}?overview=full&geometries=geojson`;
        const r = await fetch(url);
        const d = await r.json();
        if (d.code === 'Ok' && d.routes && d.routes[0]) {
            const coords = d.routes[0].geometry.coordinates.map(p => [p[1],p[0]]);
            return L.polyline(coords,{color:'#0284c7',weight:6,opacity:.9}).addTo(map);
        }
    } catch(e) {}
    return L.polyline([[fromLat,fromLng],[toLat,toLng]],{color:'#0284c7',weight:5,dashArray:'9,8'}).addTo(map);
}

function initTrackingMap(elementId, shopLat, shopLng, customerLat, customerLng, partnerLat = null, partnerLng = null) {
    if (!validCoord(shopLat) || !validCoord(shopLng) || !validCoord(customerLat) || !validCoord(customerLng)) return;
    if (trackingMap && trackingMap.remove) trackingMap.remove();
    trackingMap = baseLeafletMap(elementId, customerLat, customerLng, 14);
    if (!trackingMap) return;

    const shop = L.marker([shopLat,shopLng],{icon:makeIcon('shop')}).addTo(trackingMap).bindPopup('<b>Pickup Shop</b>');
    const customer = L.marker([customerLat,customerLng],{icon:makeIcon('customer')}).addTo(trackingMap).bindPopup('<b>Customer Delivery Location</b>');
    const pLat = validCoord(partnerLat) ? partnerLat : shopLat;
    const pLng = validCoord(partnerLng) ? partnerLng : shopLng;
    const partner = L.marker([pLat,pLng],{icon:makeIcon('bike')}).addTo(trackingMap).bindPopup('<b>Delivery Partner</b>');
    drawRoadRoute(trackingMap, shopLat, shopLng, customerLat, customerLng);
    trackingMap.fitBounds(L.latLngBounds([[shopLat,shopLng],[customerLat,customerLng]]),{padding:[35,35]});
    trackingMap.invalidateSize();
}

function updatePartnerLocationOnMap(currentLat, currentLng) {
    // Tracking animation is intentionally lightweight; the real navigation is opened in Google Maps.
}

function initDeliveryOrderMap(elementId, shopLat, shopLng, customerLat, customerLng) {
    if (!validCoord(shopLat) || !validCoord(shopLng) || !validCoord(customerLat) || !validCoord(customerLng)) return;
    if (deliveryMaps[elementId]) deliveryMaps[elementId].remove();
    const map = baseLeafletMap(elementId, customerLat, customerLng, 14);
    if (!map) return;
    L.marker([shopLat,shopLng],{icon:makeIcon('shop')}).addTo(map).bindPopup('<b>Pickup Shop</b>').openPopup();
    L.marker([customerLat,customerLng],{icon:makeIcon('customer')}).addTo(map).bindPopup('<b>Customer Drop Location</b>');
    drawRoadRoute(map, shopLat, shopLng, customerLat, customerLng);
    map.fitBounds(L.latLngBounds([[shopLat,shopLng],[customerLat,customerLng]]),{padding:[30,30]});
    map.invalidateSize();
    deliveryMaps[elementId] = map;
}

function initCheckoutMap(elementId, lat, lng, onChange) {
    if (checkoutMap && checkoutMap.remove) checkoutMap.remove();
    checkoutMap = baseLeafletMap(elementId, lat, lng, 15);
    if (!checkoutMap) return;
    checkoutMarker = L.marker([lat,lng],{icon:makeIcon('customer'),draggable:true}).addTo(checkoutMap).bindPopup('<b>Delivery location</b><br>Drag the marker to your exact location.').openPopup();
    checkoutMarker.on('dragend', async () => {
        const pos = checkoutMarker.getLatLng();
        let name = `Selected location (${pos.lat.toFixed(5)}, ${pos.lng.toFixed(5)})`;
        try {
            const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${pos.lat}&lon=${pos.lng}`, {headers:{'Accept':'application/json'}});
            if (r.ok) { const d=await r.json(); if (d.display_name) name=d.display_name; }
        } catch(e) {}
        if (onChange) onChange(pos.lat,pos.lng,name);
    });
    checkoutMap.on('click', e => checkoutMarker.setLatLng(e.latlng).fire('dragend'));
    checkoutMap.invalidateSize();
}

async function searchCheckoutLocation(query, onChange) {
    if (!query || !window.fetch) return;
    try {
        const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=in&q=${encodeURIComponent(query)}`, {headers:{'Accept':'application/json'}});
        const data = await r.json();
        if (!data.length || !checkoutMap || !checkoutMarker) return false;
        const lat = Number(data[0].lat), lng = Number(data[0].lon), name = data[0].display_name;
        checkoutMap.setView([lat,lng],16); checkoutMarker.setLatLng([lat,lng]);
        if (onChange) onChange(lat,lng,name);
        return true;
    } catch(e) { return false; }
}

function openGoogleDirections(lat, lng) {
    if (!validCoord(lat) || !validCoord(lng)) return;
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`, '_blank', 'noopener');
}

function startSimulatedLiveMovement() {}
