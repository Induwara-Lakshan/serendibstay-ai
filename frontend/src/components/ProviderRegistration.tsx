import { useState } from "react";

const districts = [
  "Ampara",
  "Anuradhapura",
  "Badulla",
  "Batticaloa",
  "Colombo",
  "Galle",
  "Gampaha",
  "Hambantota",
  "Jaffna",
  "Kalutara",
  "Kandy",
  "Kegalle",
  "Kilinochchi",
  "Kurunegala",
  "Mannar",
  "Matale",
  "Matara",
  "Monaragala",
  "Mullaitivu",
  "Nuwara Eliya",
  "Polonnaruwa",
  "Puttalam",
  "Ratnapura",
  "Trincomalee",
  "Vavuniya",
];

function ProviderRegistration() {
  const [providerName, setProviderName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [passengerCapacity, setPassengerCapacity] = useState("");
  const [baseDistrict, setBaseDistrict] = useState("");
  const [serviceDistricts, setServiceDistricts] = useState<string[]>([]);

  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleDistrictChange = (district: string) => {
    setServiceDistricts((current) =>
      current.includes(district)
        ? current.filter((item) => item !== district)
        : [...current, district]
    );
  };
  const selectAllDistricts = () => {
    setServiceDistricts([...districts]);
  };

  const clearAllDistricts = () => {
    setServiceDistricts([]);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (serviceDistricts.length === 0) {
      setMessage("Please select at least one service district.");
      return;
    }

    setLoading(true);
    setMessage("");

    const providerData = {
      provider_name: providerName,
      phone: phone,
      email: email,
      password: password,
      vehicle_type: vehicleType,
      vehicle_number: vehicleNumber,
      passenger_capacity: Number(passengerCapacity),
      base_district: baseDistrict,
      service_districts: serviceDistricts,
    };

    try {
      const response = await fetch(
        "http://127.0.0.1:8001/transport/providers",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(providerData),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Provider registration failed.");
      }

      setMessage(
        `Registration successful. Provider ID: ${data.provider_id}. Waiting for admin approval.`
      );

      setProviderName("");
      setPhone("");
      setEmail("");
      setPassword("");
      setVehicleType("");
      setVehicleNumber("");
      setPassengerCapacity("");
      setBaseDistrict("");
      setServiceDistricts([]);
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message);
      } else {
        setMessage("Provider registration failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="provider-registration">
      <div className="provider-registration-card">
        <h2>Transport Provider Registration</h2>

        <div className="registration-heading">
  <div className="registration-icon">TP</div>

  <div>
    <h2>Transport Provider Registration</h2>
    <p>
      Join SerendibStay AI and provide trusted transport services
      across Sri Lanka.
    </p>
  </div>

  <span className="approval-badge">Admin Approval Required</span>
</div>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Provider Name"
            value={providerName}
            onChange={(e) => setProviderName(e.target.value)}
            required
          />

          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

    <input
  type="password"
  placeholder="Password"
  value={password}
  onChange={(e) => setPassword(e.target.value)}
  required
/>

          <input
            type="tel"
            placeholder="Phone Number"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />

         <select
  value={vehicleType}
  onChange={(e) => setVehicleType(e.target.value)}
  required
>
  <option value="">Select Vehicle Type</option>
  <option value="Car">Car</option>
  <option value="Van">Van</option>
  <option value="Mini Bus">Mini Bus</option>
  <option value="Bus">Bus</option>
  <option value="Three Wheeler">Three Wheeler</option>
</select>

          <input
            type="text"
            placeholder="Vehicle Number"
            value={vehicleNumber}
            onChange={(e) => setVehicleNumber(e.target.value)}
            required
          />

          <input
            type="number"
            min="1"
            placeholder="Passenger Capacity"
            value={passengerCapacity}
            onChange={(e) => setPassengerCapacity(e.target.value)}
            required
          />

          <label>Base District</label>

          <select
            className="base-district-select"
            value={baseDistrict}
            onChange={(e) => setBaseDistrict(e.target.value)}
            required
          >
            <option value="">Select Base District</option>

            {districts.map((district) => (
              <option key={district} value={district}>
                {district}
              </option>
            ))}
          </select>

          <div className="service-district-section">

  <div className="district-section-header">
    <div>
      <label>Service Districts</label>
      <p>Select all districts where you provide transport services.</p>
    </div>

    <div className="district-controls">
      <span className="district-count">
        {serviceDistricts.length} of {districts.length} selected
      </span>

      <button
        type="button"
        className="district-control-button"
        onClick={selectAllDistricts}
      >
        Select All
      </button>

      <button
        type="button"
        className="district-control-button clear"
        onClick={clearAllDistricts}
      >
        Clear All
      </button>
    </div>
  </div>

  <div className="district-grid">
              {districts.map((district) => (
                <label key={district} className="district-option">
                  <input
                    type="checkbox"
                    checked={serviceDistricts.includes(district)}
                    onChange={() => handleDistrictChange(district)}
                  />
                
                 <span>{district}</span>
                </label>
              ))}
            </div>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Registering..." : "Register Provider"}
          </button>

          {message && <p className="registration-message">{message}</p>}
        </form>
      </div>
    </div>
  );
}

export default ProviderRegistration;