import { useCallback, useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faLayerGroup,
  faPlus,
  faRotate,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";

import {
  getAdminBatches,
  createAdminBatch,
} from "../../services/adminService";

import "./BatchManagement.css";

function BatchManagement() {
  const [batchName, setBatchName] = useState("");
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadBatches = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await getAdminBatches();

      if (!response?.success || !Array.isArray(response.data)) {
        throw new Error(response?.message || "Unable to load batches.");
      }

      setBatches(response.data);
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.message ||
          "Failed to load batches."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timerId = setTimeout(() => {
      loadBatches();
    }, 0);

    return () => clearTimeout(timerId);
  }, [loadBatches]);

  async function handleCreateBatch(event) {
    event.preventDefault();

    const trimmedName = batchName.trim();

    if (!trimmedName) {
      setError("Please enter a batch name.");
      return;
    }

    if (trimmedName.length > 20) {
      setError("Batch name cannot exceed 20 characters.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const response = await createAdminBatch({
        batch_name: trimmedName,
      });

      if (!response?.success) {
        throw new Error(response?.message || "Unable to create batch.");
      }

      setBatchName("");
      setSuccess(response.message || "Batch created successfully.");

      await loadBatches();
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.message ||
          "Failed to create batch."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="batch-management-page">
      <header className="batch-page-header">
        <div>
          <span className="batch-eyebrow">ADMIN PORTAL</span>
          <h1>Batch Management</h1>
          <p>Create and manage the batches used in your academic structure.</p>
        </div>

        <button
          type="button"
          className="batch-refresh-button"
          onClick={loadBatches}
          disabled={loading}
        >
          <FontAwesomeIcon
            icon={loading ? faSpinner : faRotate}
            spin={loading}
          />
          Refresh
        </button>
      </header>

      <div className="batch-summary-card">
        <div className="batch-summary-icon">
          <FontAwesomeIcon icon={faLayerGroup} />
        </div>
        <div>
          <span>Total Batches</span>
          <strong>{batches.length}</strong>
        </div>
      </div>

      <div className="batch-content-grid">
        <section className="batch-panel">
          <h2>Create Batch</h2>
          <p>Add a degree cohort batch (e.g. 2024-2028) to make it available in academic forms.</p>

          <form onSubmit={handleCreateBatch}>
            <label htmlFor="batch-name">Batch Year / Cohort</label>

            <input
              id="batch-name"
              type="text"
              value={batchName}
              onChange={(event) => {
                setBatchName(event.target.value);
                setError("");
                setSuccess("");
              }}
              placeholder="e.g. 2024-2028"
              maxLength={20}
              required
              disabled={saving}
            />

            <small>Degree cohort duration (e.g. 2024-2028 or cohort year 2024).</small>

            <button
              type="submit"
              className="batch-create-button"
              disabled={saving || !batchName.trim()}
            >
              <FontAwesomeIcon icon={saving ? faSpinner : faPlus} spin={saving} />
              {saving ? "Creating..." : "Create Batch"}
            </button>
          </form>

          {error && (
            <p className="batch-message batch-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="batch-message batch-success" role="status">
              {success}
            </p>
          )}
        </section>

        <section className="batch-panel batch-list-panel">
          <div className="batch-list-header">
            <div>
              <h2>Existing Batches</h2>
              <p>Saved batches from the database.</p>
            </div>
            <span className="batch-count">{batches.length}</span>
          </div>

          {loading ? (
            <div className="batch-empty-state">
              <FontAwesomeIcon icon={faSpinner} spin />
              <p>Loading batches...</p>
            </div>
          ) : batches.length === 0 ? (
            <div className="batch-empty-state">
              <FontAwesomeIcon icon={faLayerGroup} />
              <p>No batches found. Create your first batch.</p>
            </div>
          ) : (
            <div className="batch-table-wrapper">
              <table className="batch-table">
                <thead>
                  <tr>
                    <th>Batch ID</th>
                    <th>Batch Name</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((batch) => (
                    <tr key={batch.batch_id}>
                      <td>{batch.batch_id}</td>
                      <td>{batch.batch_name}</td>
                      <td>
                        <span
                          className={`batch-status ${
                            batch.is_active ? "active" : "inactive"
                          }`}
                        >
                          {batch.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

export default BatchManagement;
