'use client';

import { useEffect, useState, useCallback } from 'react';

interface Person {
  id: string;
  name: string;
  dietaryRestrictions: string[];
  allergies: string[];
  preferences: string[];
  dislikes: string[];
  calorieTarget: number | null;
}

const DIETARY_OPTIONS = [
  'Vegetarian', 'Vegan', 'Pescatarian', 'Keto', 'Paleo',
  'Gluten-Free', 'Dairy-Free', 'Low-Carb', 'Low-Sodium', 'Halal', 'Kosher',
];

const COMMON_ALLERGIES = [
  'Peanuts', 'Tree Nuts', 'Milk', 'Eggs', 'Wheat', 'Soy',
  'Fish', 'Shellfish', 'Sesame',
];

export default function ProfilesPage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    dietaryRestrictions: [] as string[],
    allergies: [] as string[],
    preferences: '',
    dislikes: '',
    calorieTarget: '' as string | number,
  });

  const loadPersons = useCallback(async () => {
    const res = await fetch('/api/profiles');
    if (res.ok) setPersons(await res.json());
  }, []);

  useEffect(() => {
    loadPersons();
  }, [loadPersons]);

  const resetForm = () => {
    setForm({ name: '', dietaryRestrictions: [], allergies: [], preferences: '', dislikes: '', calorieTarget: '' });
    setEditingId(null);
    setShowForm(false);
  };

  const toggleArrayItem = (field: 'dietaryRestrictions' | 'allergies', value: string) => {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field].includes(value)
        ? prev[field].filter((v) => v !== value)
        : [...prev[field], value],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: form.name,
      dietaryRestrictions: form.dietaryRestrictions,
      allergies: form.allergies,
      preferences: form.preferences ? form.preferences.split(',').map((s) => s.trim()).filter(Boolean) : [],
      dislikes: form.dislikes ? form.dislikes.split(',').map((s) => s.trim()).filter(Boolean) : [],
      calorieTarget: form.calorieTarget ? parseInt(String(form.calorieTarget), 10) : null,
      ...(editingId ? { id: editingId } : {}),
    };

    const res = await fetch('/api/profiles', {
      method: editingId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      resetForm();
      loadPersons();
    }
  };

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/profiles?id=${id}`, { method: 'DELETE' });
    if (res.ok) loadPersons();
  };

  const startEdit = (person: Person) => {
    setForm({
      name: person.name,
      dietaryRestrictions: person.dietaryRestrictions,
      allergies: person.allergies,
      preferences: person.preferences.join(', '),
      dislikes: person.dislikes.join(', '),
      calorieTarget: person.calorieTarget || '',
    });
    setEditingId(person.id);
    setShowForm(true);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20 md:pb-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Family Profiles</h1>
          <p className="text-gray-500 mt-1">Dietary plans and food preferences for your household</p>
        </div>
        {persons.length < 4 && (
          <button onClick={() => { resetForm(); setShowForm(true); }} className="btn-primary">
            + Add Person
          </button>
        )}
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="card space-y-4">
          <h3 className="font-semibold">{editingId ? 'Edit Profile' : 'Add Family Member'}</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
              placeholder="e.g., John"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Dietary Restrictions</label>
            <div className="flex flex-wrap gap-2">
              {DIETARY_OPTIONS.map((diet) => (
                <button
                  key={diet}
                  type="button"
                  onClick={() => toggleArrayItem('dietaryRestrictions', diet)}
                  className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                    form.dietaryRestrictions.includes(diet)
                      ? 'bg-primary-100 border-primary-300 text-primary-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {diet}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Allergies</label>
            <div className="flex flex-wrap gap-2">
              {COMMON_ALLERGIES.map((allergy) => (
                <button
                  key={allergy}
                  type="button"
                  onClick={() => toggleArrayItem('allergies', allergy)}
                  className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                    form.allergies.includes(allergy)
                      ? 'bg-red-100 border-red-300 text-red-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {allergy}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Food Preferences <span className="text-gray-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={form.preferences}
              onChange={(e) => setForm({ ...form, preferences: e.target.value })}
              className="input"
              placeholder="e.g., Italian, Mexican, Grilled chicken"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Dislikes <span className="text-gray-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={form.dislikes}
              onChange={(e) => setForm({ ...form, dislikes: e.target.value })}
              className="input"
              placeholder="e.g., Liver, Brussels sprouts"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Daily Calorie Target <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="number"
              value={form.calorieTarget}
              onChange={(e) => setForm({ ...form, calorieTarget: e.target.value })}
              className="input w-40"
              placeholder="e.g., 2000"
            />
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary">
              {editingId ? 'Update Profile' : 'Add Person'}
            </button>
            <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button>
          </div>
        </form>
      )}

      {/* Person cards */}
      {persons.length === 0 ? (
        <div className="card text-center text-gray-400 py-12">
          <p>No profiles yet. Add family members to track dietary preferences.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {persons.map((person) => (
            <div key={person.id} className="card space-y-3">
              <div className="flex justify-between items-start">
                <h3 className="text-lg font-semibold text-gray-900">{person.name}</h3>
                <div className="flex gap-1">
                  <button onClick={() => startEdit(person)} className="p-1.5 text-gray-400 hover:text-gray-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button onClick={() => handleDelete(person.id)} className="p-1.5 text-gray-400 hover:text-red-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              {person.calorieTarget && (
                <div className="text-sm text-gray-500">
                  Target: {person.calorieTarget} cal/day
                </div>
              )}

              {person.dietaryRestrictions.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Dietary</div>
                  <div className="flex flex-wrap gap-1">
                    {person.dietaryRestrictions.map((d) => (
                      <span key={d} className="badge bg-primary-100 text-primary-700">{d}</span>
                    ))}
                  </div>
                </div>
              )}

              {person.allergies.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Allergies</div>
                  <div className="flex flex-wrap gap-1">
                    {person.allergies.map((a) => (
                      <span key={a} className="badge bg-red-100 text-red-700">{a}</span>
                    ))}
                  </div>
                </div>
              )}

              {person.preferences.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Likes</div>
                  <div className="flex flex-wrap gap-1">
                    {person.preferences.map((p) => (
                      <span key={p} className="badge bg-green-100 text-green-700">{p}</span>
                    ))}
                  </div>
                </div>
              )}

              {person.dislikes.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Dislikes</div>
                  <div className="flex flex-wrap gap-1">
                    {person.dislikes.map((d) => (
                      <span key={d} className="badge bg-gray-100 text-gray-600">{d}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
