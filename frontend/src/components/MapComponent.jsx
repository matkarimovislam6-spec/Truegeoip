import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

const ChangeView = ({ center, zoom }) => {
    const map = useMap();
    useEffect(() => {
        if (center && center[0] !== null && center[1] !== null) {
            map.setView(center, zoom);
        }
    }, [center, zoom, map]);
    return null;
};

const MapComponent = ({ lat, lng, popupContent, zoom = 10 }) => {
    const position = [lat || 20, lng || 0];

    return (
        <MapContainer center={position} zoom={zoom} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }} className="leaflet-map-compact">
            <ChangeView center={[lat, lng]} zoom={zoom} />
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {lat !== null && lng !== null && (
                <Marker position={position}>
                    <Popup>
                        <div dangerouslySetInnerHTML={{ __html: popupContent }} />
                    </Popup>
                </Marker>
            )}
        </MapContainer>
    );
};

export default MapComponent;
