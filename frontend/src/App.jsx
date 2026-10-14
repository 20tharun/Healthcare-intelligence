
import { useState } from 'react';
import {
  HeartPulse,
  MapPin,
  LocateFixed,
  Search,
  ShieldAlert,
  Phone,
  Navigation,
  Building2,
  Activity,
} from 'lucide-react';

import './App.css';

const API =
  (import.meta.env.VITE_API_URL ||
    'https://healthcare-intelligence-uvrm.onrender.com').replace(/\/$/, '');

const cities = [
  'Coimbatore, Tamil Nadu',
  'Chennai, Tamil Nadu',
  'Madurai, Tamil Nadu',
  'Salem, Tamil Nadu',
  'Tiruchirappalli, Tamil Nadu',
  'Erode, Tamil Nadu',
  'Tiruppur, Tamil Nadu',
  'Bengaluru, Karnataka',
  'Other / enter city',
];

const services = [
  'Emergency department',
  'ICU beds',
  'Oxygen support',
  'Ventilator support',
  'Cardiologist',
  'Neurologist',
  'Orthopedic specialist',
  'Blood bank',
  'CT scan / MRI',
  'Emergency surgery',
  'NICU',
  'Dialysis',
];

export default function App() {
  const [city, setCity] = useState(cities[0]);
  const [customCity, setCustomCity] = useState('');
  const [lat, setLat] = useState('11.0168');
  const [lon, setLon] = useState('76.9558');
  const [useCoords, setUseCoords] = useState(false);
  const [radius, setRadius] = useState('15');
  const [servicesChosen, setServicesChosen] = useState([
    'Emergency department',
  ]);
  const [hospitals, setHospitals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [notice, setNotice] = useState('');
  const [dataNotice, setDataNotice] = useState('');

  function toggleService(service) {
    setServicesChosen((old) =>
      old.includes(service)
        ? old.filter((item) => item !== service)
        : [...old, service]
    );
  }

  function locate() {
    if (!navigator.geolocation) {
      setNotice('GPS is not supported. Please select a city.');
      return;
    }

    setNotice('Getting your location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude.toFixed(6));
        setLon(position.coords.longitude.toFixed(6));
        setUseCoords(true);
        setNotice('GPS location added. Click Find nearby hospitals.');
      },
      () => {
        setNotice(
          'Location access failed. Allow location in your browser or select a city.'
        );
      },
      { timeout: 15000, enableHighAccuracy: false }
    );
  }

  async function search(event) {
    event.preventDefault();

    if (loading) return;

    const chosen =
      city === 'Other / enter city' ? customCity.trim() : city;

    if (!useCoords && !chosen) {
      setNotice('Please enter a city name.');
      return;
    }

    if (
      useCoords &&
      (!Number.isFinite(Number(lat)) ||
        !Number.isFinite(Number(lon)) ||
        lat === '' ||
        lon === '')
    ) {
      setNotice('Please enter valid latitude and longitude.');
      return;
    }

    setLoading(true);
    setSearched(true);
    setHospitals([]);
    setNotice('');
    setDataNotice('');

    const body = {
      radius_km: Number(radius),
      emergency_type: 'General emergency',
      required_services: servicesChosen,
    };

    if (useCoords) {
      body.latitude = Number(lat);
      body.longitude = Number(lon);
    } else {
      body.city = chosen;
    }

    try {
      const response = await fetch(`${API}/api/hospitals/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const raw = await response.text();
      let data;

      try {
        data = JSON.parse(raw);
      } catch {
        throw new Error(
          `The backend returned an unexpected response (HTTP ${response.status}).`
        );
      }

      if (!response.ok) {
        throw new Error(
          data.detail || `Hospital search failed (HTTP ${response.status}).`
        );
      }

      const results = Array.isArray(data.hospitals) ? data.hospitals : [];

      setHospitals(results);
      setDataNotice(data.data_notice || '');

      if (results.length === 0) {
        setNotice(
          `No facilities were returned for ${data.resolved_location || chosen}. Try a larger radius or retry later. This does not mean no hospitals exist.`
        );
      }
    } catch (error) {
      console.error('Healthcare hospital search failed:', error);

      if (error instanceof TypeError) {
        setNotice(
          'Cannot connect to the hospital API. Check the API URL, CORS settings, internet connection, and Render deployment.'
        );
      } else {
        setNotice(
          error.message || 'Hospital search failed. Please try again.'
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Healthcare Intelligence home">
          <span className="logo">
            <HeartPulse size={27} />
          </span>
          <span>
            <b>Healthcare</b>
            <strong>Intelligence</strong>
          </span>
        </a>
        <span className="topnote">Emergency discovery prototype</span>
      </header>

      <main>
        <section className="hero">
          <div>
            <div className="eyebrow">
              <Activity size={16} />
              SMARTER EMERGENCY HOSPITAL DISCOVERY
            </div>

            <h1>
              Find nearby care.
              <br />
              <em>Verify before transfer.</em>
            </h1>

            <p>
              Search hospitals by city or GPS and review public map details.
              Live hospital capacity is unknown unless a verified integration
              provides it.
            </p>

            <div className="pills">
              <span>Nearby discovery</span>
              <span>Facility information</span>
              <span>Transparent status</span>
            </div>
          </div>

          <div className="heroart" aria-hidden="true">
            <div className="halo" />
            <div className="cross">
              <HeartPulse size={70} />
            </div>
            <div className="float f1">
              <MapPin />
              <span>
                <b>City or GPS</b>
                <small>Public map data</small>
              </span>
            </div>
            <div className="float f2">
              <ShieldAlert />
              <span>
                <b>Clear status</b>
                <small>No fake availability</small>
              </span>
            </div>
          </div>
        </section>

        <div className="warning">
          <ShieldAlert size={25} />
          <div>
            <b>Not an emergency dispatch system</b>
            <p>
              Public map data cannot confirm ICU beds, oxygen, ventilators,
              specialists, or patient acceptance. Call the hospital or
              ambulance service to verify. Never delay emergency care to use
              this app.
            </p>
          </div>
        </div>

        <section className="workspace">
          <aside className="panel formpanel">
            <div className="paneltitle">
              <span className="iconbox">
                <Activity />
              </span>
              <div>
                <h2>Emergency search</h2>
                <p>Choose a city or use your GPS</p>
              </div>
            </div>

            <form onSubmit={search}>
              <label htmlFor="city">Search city / location</label>
              <select
                id="city"
                value={city}
                onChange={(event) => {
                  setCity(event.target.value);
                  setUseCoords(false);
                }}
              >
                {cities.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>

              {city === 'Other / enter city' && (
                <input
                  aria-label="Enter city"
                  placeholder="e.g. Hosur, Tamil Nadu"
                  value={customCity}
                  onChange={(event) => setCustomCity(event.target.value)}
                  required
                />
              )}

              <div className="labelrow">
                <label>Coordinates (optional)</label>
                <button
                  type="button"
                  className="linkbtn"
                  onClick={locate}
                >
                  <LocateFixed size={15} />
                  Use my location
                </button>
              </div>

              <div className="coords">
                <div>
                  <small>Latitude</small>
                  <input
                    aria-label="Latitude"
                    type="number"
                    step="any"
                    min="-90"
                    max="90"
                    value={lat}
                    onChange={(event) => {
                      setLat(event.target.value);
                      setUseCoords(true);
                    }}
                  />
                </div>
                <div>
                  <small>Longitude</small>
                  <input
                    aria-label="Longitude"
                    type="number"
                    step="any"
                    min="-180"
                    max="180"
                    value={lon}
                    onChange={(event) => {
                      setLon(event.target.value);
                      setUseCoords(true);
                    }}
                  />
                </div>
              </div>

              <label htmlFor="radius">Search radius</label>
              <select
                id="radius"
                value={radius}
                onChange={(event) => setRadius(event.target.value)}
              >
                {[5, 10, 15, 20, 30, 50, 100].map((value) => (
                  <option key={value} value={value}>
                    Within {value} km
                  </option>
                ))}
              </select>

              <div className="labelrow">
                <label>Required services</label>
                <small>Not live-verified</small>
              </div>

              <div className="services">
                {services.map((service) => (
                  <label
                    className={
                      servicesChosen.includes(service) ? 'chosen' : ''
                    }
                    key={service}
                  >
                    <input
                      type="checkbox"
                      checked={servicesChosen.includes(service)}
                      onChange={() => toggleService(service)}
                    />
                    <span>
                      {servicesChosen.includes(service) ? '✓' : ''}
                    </span>
                    {service}
                  </label>
                ))}
              </div>

              <button className="primary" type="submit" disabled={loading}>
                <Search size={18} />
                {loading ? 'Searching map data...' : 'Find nearby hospitals'}
              </button>

              {notice && (
                <p className="notice" role="status">
                  {notice}
                </p>
              )}
            </form>

            <p className="footnote">
              Source: OpenStreetMap / Overpass. Internet required. Map
              coverage varies.
            </p>
          </aside>

          <section className="panel results">
            <div className="resultshead">
              <div>
                <div className="eyebrow small">RECOMMENDATION RESULTS</div>
                <h2>
                  {searched
                    ? `${hospitals.length} hospitals / facilities found`
                    : 'Hospitals near your selected city'}
                </h2>
                <p>Sorted by straight-line distance; score is a prototype.</p>
              </div>
            </div>

            {loading && (
              <div className="empty">
                <div className="loader" />
                <h3>Searching public map data</h3>
                <p>Waiting for hospital and healthcare facility information.</p>
              </div>
            )}

            {!loading && hospitals.length === 0 && (
              <div className="empty">
                <div className="emptyicon">
                  <Building2 />
                  <MapPin />
                </div>
                <h3>
                  {searched ? 'No results returned' : 'Choose a location to begin'}
                </h3>
                <p>
                  {searched
                    ? 'Read the error message on the left. Public map coverage or service availability may be the cause.'
                    : 'Select a city and search to discover mapped facilities.'}
                </p>
              </div>
            )}

            {!loading &&
              hospitals.map((hospital, index) => (
                <article className="hospital" key={hospital.id}>
                  <div className="hospitalhead">
                    <span className="number">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <div className="hospitalname">
                      <h3>{hospital.name}</h3>
                      <p>
                        <MapPin size={14} />
                        {hospital.address || 'Address not listed'}
                      </p>
                    </div>
                    <div className="score">
                      <b>{hospital.distance_km} km</b>
                      <small>straight-line</small>
                    </div>
                  </div>

                  <div className="meta">
                    <span>
                      <b>Score {hospital.score}/100</b>
                    </span>
                    <span className="unknown">Availability unknown</span>
                  </div>

                  <div className="facility">
                    <div>
                      <b>Facility verification</b>
                      <small>Not live-connected</small>
                    </div>
                    <p>
                      {hospital.live_capacity_status ||
                        'Live hospital capacity is not available.'}
                    </p>
                    <div className="tags">
                      {(hospital.mapped_services || []).map((service) => (
                        <span key={service}>{service}</span>
                      ))}
                      {servicesChosen.map((service) => (
                        <span className="unverified" key={service}>
                          {service}: unverified
                        </span>
                      ))}
                    </div>
                  </div>

                  <details>
                    <summary>Why this result?</summary>
                    <ul>
                      {(hospital.score_explanation || []).map(
                        (explanation, index) => (
                          <li key={index}>{explanation}</li>
                        )
                      )}
                    </ul>
                  </details>

                  <div className="actions">
                    {hospital.phone ? (
                      <a href={`tel:${hospital.phone}`}>
                        <Phone size={15} />
                        Call hospital
                      </a>
                    ) : (
                      <span className="muted">
                        <Phone size={15} />
                        Phone not listed
                      </span>
                    )}

                    <a
                      target="_blank"
                      rel="noreferrer"
                      href={`https://www.google.com/maps/dir/?api=1&destination=${hospital.latitude},${hospital.longitude}`}
                    >
                      <Navigation size={15} />
                      Directions
                    </a>

                    {hospital.osm_url && (
                      <a
                        className="source"
                        target="_blank"
                        rel="noreferrer"
                        href={hospital.osm_url}
                      >
                        OSM source ↗
                      </a>
                    )}
                  </div>
                </article>
              ))}

            {dataNotice && <div className="datanote">{dataNotice}</div>}
          </section>
        </section>
      </main>

      <footer>
        <a className="brand" href="/">
          <span className="logo">
            <HeartPulse size={24} />
          </span>
          <span>
            <b>Healthcare</b>
            <strong>Intelligence</strong>
          </span>
        </a>
        <p>
          Final-year project prototype · Live clinical availability is not
          provided
        </p>
      </footer>
    </div>
  );
}
