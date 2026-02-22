'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';

interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  isLeftover: boolean;
  expiryDate: string | null;
  notes: string | null;
  addedAt: string;
}

const CATEGORIES = ['fridge', 'freezer', 'pantry'] as const;
const UNITS = ['item', 'lb', 'oz', 'kg', 'g', 'cup', 'gallon', 'liter', 'serving', 'package', 'bunch', 'dozen'];

export default function InventoryPage() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [filter, setFilter] = useState(searchParams.get('category') || 'all');
  const [showLeftovers, setShowLeftovers] = useState(searchParams.get('leftovers') === 'true');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    category: 'fridge' as string,
    quantity: 1,
    unit: 'item',
    isLeftover: false,
    expiryDate: '',
    notes: '',
  });

  const loadItems = useCallback(async () => {
    const params = new URLSearchParams();
    if (filter !== 'all') params.set('category', filter);
    if (showLeftovers) params.set('leftovers', 'true');
    const res = await fetch(`/api/inventory?${params}`);
    if (res.ok) setItems(await res.json());
  }, [filter, showLeftovers]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const resetForm = () => {
    setForm({ name: '', category: 'fridge', quantity: 1, unit: 'item', isLeftover: false, expiryDate: '', notes: '' });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      expiryDate: form.expiryDate || null,
      notes: form.notes || null,
      ...(editingId ? { id: editingId } : {}),
    };

    const res = await fetch('/api/inventory', {
      method: editingId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      resetForm();
      loadItems();
    }
  };

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/inventory?id=${id}`, { method: 'DELETE' });
    if (res.ok) loadItems();
  };

  const startEdit = (item: InventoryItem) => {
    setForm({
      name: item.name,
      category: item.category,
      quantity: item.quantity,
      unit: item.unit,
      isLeftover: item.isLeftover,
      expiryDate: item.expiryDate ? item.expiryDate.split('T')[0] : '',
      notes: item.notes || '',
    });
    setEditingId(item.id);
    setShowForm(true);
  };

  const categoryBadge = (cat: string) => {
    switch (cat) {
      case 'fridge': return 'badge-fridge';
      case 'freezer': return 'badge-freezer';
      case 'pantry': return 'badge-pantry';
      default: return 'badge bg-gray-100 text-gray-600';
    }
  };

  const isExpiringSoon = (date: string | null) => {
    if (!date) return false;
    const days = (new Date(date).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
    return days >= 0 && days <= 3;
  };

  const isExpired = (date: string | null) => {
    if (!date) return false;
    return new Date(date).getTime() < Date.now();
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20 md:pb-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-gray-500 mt-1">Track what&apos;s in your fridge, freezer, and pantry</p>
        </div>
        <button onClick={() => { resetForm(); setShowForm(true); }} className="btn-primary">
          + Add Item
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {['all', ...CATEGORIES].map((cat) => (
          <button
            key={cat}
            onClick={() => { setFilter(cat); setShowLeftovers(false); }}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === cat && !showLeftovers
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat === 'all' ? 'All' : cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
        <button
          onClick={() => { setShowLeftovers(!showLeftovers); setFilter('all'); }}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            showLeftovers
              ? 'bg-orange-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Leftovers
        </button>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="card space-y-4">
          <h3 className="font-semibold">{editingId ? 'Edit Item' : 'Add New Item'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input"
                placeholder="e.g., Chicken breast"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="input"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                <input
                  type="number"
                  step="0.25"
                  min="0"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })}
                  className="input"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                <select
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                  className="input"
                >
                  {UNITS.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Expiry Date</label>
              <input
                type="date"
                value={form.expiryDate}
                onChange={(e) => setForm({ ...form, expiryDate: e.target.value })}
                className="input"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.isLeftover}
                onChange={(e) => setForm({ ...form, isLeftover: e.target.checked })}
                className="rounded border-gray-300"
              />
              This is a leftover
            </label>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="input"
              placeholder="Optional notes"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary">
              {editingId ? 'Update' : 'Add Item'}
            </button>
            <button type="button" onClick={resetForm} className="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Items list */}
      {items.length === 0 ? (
        <div className="card text-center text-gray-400 py-12">
          <p>No items found. Add your first item to get started.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className={`card flex items-center justify-between ${
                isExpired(item.expiryDate) ? 'border-red-200 bg-red-50' :
                isExpiringSoon(item.expiryDate) ? 'border-amber-200 bg-amber-50' : ''
              }`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900">{item.name}</span>
                    <span className={categoryBadge(item.category)}>{item.category}</span>
                    {item.isLeftover && <span className="badge-leftover">leftover</span>}
                    {isExpired(item.expiryDate) && (
                      <span className="badge bg-red-100 text-red-700">expired</span>
                    )}
                    {isExpiringSoon(item.expiryDate) && !isExpired(item.expiryDate) && (
                      <span className="badge bg-amber-100 text-amber-700">expiring soon</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-0.5">
                    {item.quantity} {item.unit}
                    {item.expiryDate && (
                      <span className="ml-2">
                        Exp: {new Date(item.expiryDate).toLocaleDateString()}
                      </span>
                    )}
                    {item.notes && <span className="ml-2 text-gray-400">- {item.notes}</span>}
                  </div>
                </div>
              </div>
              <div className="flex gap-1 ml-2">
                <button
                  onClick={() => startEdit(item)}
                  className="p-2 text-gray-400 hover:text-gray-600"
                  title="Edit"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="p-2 text-gray-400 hover:text-red-500"
                  title="Delete"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
