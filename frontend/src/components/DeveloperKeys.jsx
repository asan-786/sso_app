import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { Key, Copy, Trash2, Plus, Eye, EyeOff } from "lucide-react";

const API_URL = "http://127.0.0.1:8000/api";

const DeveloperKeys = () => {
  const { token } = useAuth();
  const [keys, setKeys] = useState([]);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [visibleKeys, setVisibleKeys] = useState({});

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      const res = await fetch(`${API_URL}/keys`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setKeys(data);
      }
    } catch (err) {
      console.error("Error loading keys:", err);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      alert("Please enter a name for the API key");
      return;
    }

    try {
      const res = await fetch(`${API_URL}/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ name: newKeyName })
      });

      if (res.ok) {
        const data = await res.json();
        setNewKeyValue(data.key_value);
        await loadKeys();
        setNewKeyName("");
      }
    } catch (err) {
      console.error("Error creating key:", err);
      alert("Failed to create API key");
    }
  };

  const handleDeleteKey = async (keyId) => {
    if (!window.confirm("Are you sure you want to revoke this API key?")) return;

    try {
      const res = await fetch(`${API_URL}/keys/${keyId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        await loadKeys();
        alert("API key revoked");
      }
    } catch (err) {
      console.error("Error deleting key:", err);
      alert("Failed to revoke API key");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const toggleKeyVisibility = (keyId) => {
    setVisibleKeys((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Key className="text-purple-600" size={24} />
          <h2 className="text-xl font-bold text-gray-800">Developer API Keys</h2>
        </div>
        <button
          onClick={() => setShowNewKeyModal(true)}
          className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
        >
          <Plus size={18} />
          Create Key
        </button>
      </div>

      {keys.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No API keys created yet</p>
          <p className="text-sm mt-2">Create one to integrate SSO with your applications</p>
        </div>
      ) : (
        <div className="space-y-3">
          {keys.map((key) => (
            <div key={key.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-800">{key.name}</h3>
                <button
                  onClick={() => handleDeleteKey(key.id)}
                  className="text-red-600 hover:bg-red-50 p-2 rounded"
                >
                  <Trash2 size={18} />
                </button>
              </div>
              
              <div className="flex items-center gap-2 bg-gray-50 p-3 rounded">
                <code className="flex-1 text-sm font-mono text-gray-700">
                  {visibleKeys[key.id] ? key.key_value : "••••••••••••••••••••••••••••••••"}
                </code>
                <button
                  onClick={() => toggleKeyVisibility(key.id)}
                  className="text-gray-600 hover:text-gray-800"
                >
                  {visibleKeys[key.id] ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
                <button
                  onClick={() => copyToClipboard(key.key_value)}
                  className="text-purple-600 hover:text-purple-800"
                >
                  <Copy size={18} />
                </button>
              </div>

              <div className="flex gap-4 mt-2 text-xs text-gray-500">
                <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                {key.last_used && <span>Last used: {new Date(key.last_used).toLocaleDateString()}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showNewKeyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-800 mb-4">Create API Key</h3>
            
            {newKeyValue ? (
              <div>
                <p className="text-sm text-gray-600 mb-3">
                  Save this key now! You won't be able to see it again.
                </p>
                <div className="bg-green-50 border border-green-200 p-4 rounded-lg mb-4">
                  <code className="text-sm break-all">{newKeyValue}</code>
                </div>
                <button
                  onClick={() => {
                    copyToClipboard(newKeyValue);
                    setShowNewKeyModal(false);
                    setNewKeyValue("");
                  }}
                  className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
                >
                  Copy & Close
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="text"
                  placeholder="Key name (e.g., 'Production App')"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg mb-4"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleCreateKey}
                    className="flex-1 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
                  >
                    Create
                  </button>
                  <button
                    onClick={() => setShowNewKeyModal(false)}
                    className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DeveloperKeys;