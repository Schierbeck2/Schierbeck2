'use client';

import { useEffect, useState, useCallback } from 'react';

interface Person {
  id: string;
  name: string;
}

interface Recipe {
  id: string;
  title: string;
}

interface MealPlan {
  id: string;
  date: string;
  mealType: string;
  customMeal: string | null;
  notes: string | null;
  recipe: Recipe | null;
  persons: Person[];
}

const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snack'] as const;

function getWeekDates(offset: number): Date[] {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - today.getDay() + offset * 7);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

function formatDate(d: Date): string {
  return d.toISOString().split('T')[0];
}

function formatDay(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

export default function MealsPage() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [meals, setMeals] = useState<MealPlan[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    date: formatDate(new Date()),
    mealType: 'dinner' as string,
    recipeId: '',
    customMeal: '',
    notes: '',
    personIds: [] as string[],
  });

  const weekDates = getWeekDates(weekOffset);

  const loadData = useCallback(async () => {
    const start = formatDate(weekDates[0]);
    const end = formatDate(weekDates[6]);
    const [mealsRes, personsRes, recipesRes] = await Promise.all([
      fetch(`/api/meals?start=${start}&end=${end}`),
      fetch('/api/profiles'),
      fetch('/api/recipes'),
    ]);
    if (mealsRes.ok) setMeals(await mealsRes.json());
    if (personsRes.ok) setPersons(await personsRes.json());
    if (recipesRes.ok) setRecipes(await recipesRes.json());
  }, [weekOffset]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadData();
  }, [loadData]);

  const resetForm = () => {
    setForm({ date: formatDate(new Date()), mealType: 'dinner', recipeId: '', customMeal: '', notes: '', personIds: [] });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      date: form.date,
      mealType: form.mealType,
      recipeId: form.recipeId || null,
      customMeal: form.customMeal || null,
      notes: form.notes || null,
      personIds: form.personIds,
      ...(editingId ? { id: editingId } : {}),
    };

    const res = await fetch('/api/meals', {
      method: editingId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      resetForm();
      loadData();
    }
  };

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/meals?id=${id}`, { method: 'DELETE' });
    if (res.ok) loadData();
  };

  const openFormForDate = (date: Date, mealType: string) => {
    resetForm();
    setForm((prev) => ({ ...prev, date: formatDate(date), mealType }));
    setShowForm(true);
  };

  const togglePerson = (personId: string) => {
    setForm((prev) => ({
      ...prev,
      personIds: prev.personIds.includes(personId)
        ? prev.personIds.filter((id) => id !== personId)
        : [...prev.personIds, personId],
    }));
  };

  const getMealsForDay = (date: Date, type: string) => {
    const dateStr = formatDate(date);
    return meals.filter(
      (m) => m.date.startsWith(dateStr) && m.mealType === type
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20 md:pb-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meal Plans</h1>
          <p className="text-gray-500 mt-1">Plan meals for the week</p>
        </div>
        <button onClick={() => { resetForm(); setShowForm(true); }} className="btn-primary">
          + Plan Meal
        </button>
      </div>

      {/* Week navigation */}
      <div className="flex items-center justify-between">
        <button onClick={() => setWeekOffset((w) => w - 1)} className="btn-secondary">
          Previous
        </button>
        <span className="font-medium text-gray-700">
          {formatDay(weekDates[0])} - {formatDay(weekDates[6])}
        </span>
        <button onClick={() => setWeekOffset((w) => w + 1)} className="btn-secondary">
          Next
        </button>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="card space-y-4">
          <h3 className="font-semibold">{editingId ? 'Edit Meal' : 'Plan a Meal'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="input"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Meal Type</label>
              <select
                value={form.mealType}
                onChange={(e) => setForm({ ...form, mealType: e.target.value })}
                className="input"
              >
                {MEAL_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Recipe</label>
              <select
                value={form.recipeId}
                onChange={(e) => setForm({ ...form, recipeId: e.target.value })}
                className="input"
              >
                <option value="">No recipe (custom meal)</option>
                {recipes.map((r) => (
                  <option key={r.id} value={r.id}>{r.title}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Custom Meal <span className="text-gray-400 font-normal">(if no recipe)</span>
              </label>
              <input
                type="text"
                value={form.customMeal}
                onChange={(e) => setForm({ ...form, customMeal: e.target.value })}
                className="input"
                placeholder="e.g., Takeout pizza"
              />
            </div>
          </div>

          {persons.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Who&apos;s eating?</label>
              <div className="flex flex-wrap gap-2">
                {persons.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => togglePerson(person.id)}
                    className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                      form.personIds.includes(person.id)
                        ? 'bg-primary-100 border-primary-300 text-primary-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {person.name}
                  </button>
                ))}
              </div>
            </div>
          )}

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
              {editingId ? 'Update' : 'Add Meal'}
            </button>
            <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button>
          </div>
        </form>
      )}

      {/* Weekly calendar */}
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Header row */}
          <div className="grid grid-cols-8 gap-1 mb-1">
            <div className="p-2 text-sm font-medium text-gray-500" />
            {weekDates.map((d) => {
              const isToday = formatDate(d) === formatDate(new Date());
              return (
                <div
                  key={formatDate(d)}
                  className={`p-2 text-center text-sm font-medium rounded-t-lg ${
                    isToday ? 'bg-primary-100 text-primary-700' : 'text-gray-700 bg-gray-50'
                  }`}
                >
                  {d.toLocaleDateString('en-US', { weekday: 'short' })}
                  <div className="text-xs">{d.getMonth() + 1}/{d.getDate()}</div>
                </div>
              );
            })}
          </div>

          {/* Meal rows */}
          {MEAL_TYPES.map((type) => (
            <div key={type} className="grid grid-cols-8 gap-1 mb-1">
              <div className="p-2 text-sm font-medium text-gray-500 capitalize flex items-start">
                {type}
              </div>
              {weekDates.map((d) => {
                const dayMeals = getMealsForDay(d, type);
                return (
                  <div
                    key={`${formatDate(d)}-${type}`}
                    className="bg-white border border-gray-100 rounded-lg p-1.5 min-h-[60px] cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => dayMeals.length === 0 && openFormForDate(d, type)}
                  >
                    {dayMeals.map((meal) => (
                      <div
                        key={meal.id}
                        className="text-xs p-1 rounded bg-primary-50 text-primary-700 mb-1 group relative"
                      >
                        <div className="font-medium truncate">
                          {meal.recipe?.title || meal.customMeal || 'Planned'}
                        </div>
                        {meal.persons.length > 0 && (
                          <div className="text-primary-500 truncate">
                            {meal.persons.map((p) => p.name).join(', ')}
                          </div>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(meal.id); }}
                          className="absolute top-0 right-0 p-0.5 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
